#!/usr/bin/env python3
"""
Docker Environment Manager
"""

import os
import subprocess
import time
import secrets
import string
import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from data.dataset_manager import dataset_manager
from utils.port_manager import port_manager

PROJECT_ROOT = Path(__file__).parent.parent

def _get_env_path(category, env_name):
    if category == "defense":
        return PROJECT_ROOT / "docker" / "defense" / env_name
    elif category == "cve":
        return PROJECT_ROOT / "docker" / "cve" / env_name
    elif category == "multiple_host":
        return PROJECT_ROOT / "docker" / "MultiHost" / env_name
    elif category == "full_chain":
        return PROJECT_ROOT / "docker" / "FullChain" / env_name
    else:
        return None

def _find_compose_file(env_path: Path) -> Optional[Path]:
    """Recursively find docker-compose.yml or docker-compose.yaml"""
    for ext in ["docker-compose.yml", "docker-compose.yaml"]:
        candidate = env_path / ext
        if candidate.exists():
            return candidate
    # Recursively search subdirectories
    for sub in env_path.iterdir():
        if sub.is_dir():
            for ext in ["docker-compose.yml", "docker-compose.yaml"]:
                candidate = sub / ext
                if candidate.exists():
                    return candidate
    return None

class DockerManager:
    def __init__(self):
        self.docker_dir = PROJECT_ROOT / "docker"
        self.environments = self._build_environments()
        self.task_to_env = self._build_task_to_env_mapping()
        self.category_to_envs = self._build_category_to_envs()
        self.flags_dir = PROJECT_ROOT / "flags"
        self.flags_dir.mkdir(exist_ok=True)

    def _build_environments(self) -> Dict[str, Dict]:
        envs = {}
        for category in dataset_manager.list_categories():
            tasks = dataset_manager.get_datasets(category)
            for task_name, task_info in tasks.items():
                env_name = task_info.get('environment')
                if env_name:
                    envs[env_name] = {
                        "path": _get_env_path(category, env_name),
                        "name": task_info.get('name', env_name),
                        "description": task_info.get('description', '')
                    }
        return envs

    def _build_task_to_env_mapping(self) -> Dict[str, str]:
        mapping = {}
        for category in dataset_manager.list_categories():
            tasks = dataset_manager.get_datasets(category)
            for task_name, task_info in tasks.items():
                env_name = task_info.get('environment')
                if env_name:
                    mapping[task_info['id']] = env_name
                    mapping[task_name] = env_name
        return mapping

    def _build_category_to_envs(self) -> Dict[str, List[str]]:
        cat_envs = {}
        for category in dataset_manager.list_categories():
            envs = []
            tasks = dataset_manager.get_datasets(category)
            for task_name, task_info in tasks.items():
                env_name = task_info.get('environment')
                if env_name:
                    envs.append(env_name)
            cat_envs[category] = envs
        return cat_envs

    def list_environments(self) -> List[str]:
        return list(self.environments.keys())

    def get_environment_info(self, env_name: str) -> Optional[Dict]:
        return self.environments.get(env_name)

    def check_docker_installed(self) -> bool:
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            # Prefer Compose V2 (docker compose). Fallback to V1 if necessary.
            try:
                subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
            except Exception:
                subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _compose_cmd(self) -> List[str]:
        """Return the compose base command. Prefer docker compose (V2)."""
        try:
            subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
            return ["docker", "compose"]
        except Exception:
            return ["docker-compose"]

    def update_docker_compose_ports(self, env_path: Path, ports: Dict[str, int]):
        compose_file = _find_compose_file(env_path)
        if not compose_file:
            print(f"⚠️ docker-compose.yaml not found: {env_path}")
            return False
        try:
            with open(compose_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace only placeholder default values (e.g., ${APACHE_PORT:-8080} -> ${APACHE_PORT:-5999}), keep placeholders
            import re
            for port_key, new_port in ports.items():
                if not (isinstance(port_key, str) and port_key.startswith('${') and port_key.endswith('}')):
                    # Only support the ${VAR:-DEFAULT} form
                    continue
                var_name = port_key[2:-1].split(':')[0]

                # Unescaped placeholder: ${VAR:-DEFAULT}
                pattern_plain = rf'(\$\{{{var_name}:-)([^}}]+)(\}})'
                # Escaped placeholder: \${VAR:-DEFAULT}
                pattern_escaped = rf'(\\\$\{{{var_name}:-)([^}}]+)(\}})'

                def _repl_plain(m):
                    return f"{m.group(1)}{new_port}{m.group(3)}"

                def _repl_escaped(m):
                    return f"{m.group(1)}{new_port}{m.group(3)}"

                cnt1 = 0
                cnt2 = 0
                content, cnt1 = re.subn(pattern_plain, _repl_plain, content)
                content, cnt2 = re.subn(pattern_escaped, _repl_escaped, content)
                if (cnt1 + cnt2) > 0:
                    print(f"🔧 Replaced default port: {var_name} -> {new_port} (matched {cnt1+cnt2})")
                else:
                    print(f"⚠️ Placeholder not found: {var_name}")

            with open(compose_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"❌ Failed to update port mappings: {e}")
            return False

    def _show_access_info(self, env_name: str, ports: Optional[Dict[str, int]] = None):
        # print(f"\n🌐 Access URLs: (refer to datasets.json ports and compose)")
        if ports:
            for k, v in ports.items():
                print(f"   {k}: http://localhost:{v}/")

    def start_environment(self, env_name: str, ports: Optional[Dict[str, int]] = None) -> bool:
        if not self.check_docker_installed():
            print("❌ Docker or docker-compose is not installed")
            return False
        env_info = self.environments.get(env_name)
        if not env_info:
            print(f"❌ Environment not found: {env_name}")
            return False
        env_path = env_info["path"]
        if not env_path or not env_path.exists():
            print(f"❌ Environment path does not exist: {env_path}")
            return False
        # Pre-start cleanup (remove volumes if needed)
        try:
            remove_volumes = self.env_requires_fresh_volumes(env_name)
            if remove_volumes:
                print("🧹 Pre-start cleanup (including volumes) to avoid stale flags...")
            else:
                print("🧹 Pre-start cleanup (excluding volumes)...")
            self.prestart_cleanup(env_name, remove_volumes=remove_volumes)
        except Exception:
            pass
        print(f"🚀 Starting {env_info['name']}...")
        print(f"📁 Env path: {env_path}")
        compose_env = None
        if ports:
            print(f"🔗 Using ports: {ports}")
            # FullChain env: pass ports via env vars only, do not modify compose
            is_full_chain = any(part.lower() == 'fullchain' for part in env_path.parts)
            if is_full_chain:
                compose_env = self._build_compose_env_vars(env_path, ports)
            else:
                # Other envs: only replace placeholder defaults (e.g., ${APACHE_PORT:-8080} -> ${APACHE_PORT:-5999}); don't hardcode ports
                self.update_docker_compose_ports(env_path, ports)
        try:
            import subprocess, time
            compose_file = _find_compose_file(env_path)
            if not compose_file:
                print(f"❌ Compose file not found: {env_path}")
                return False
            os.chdir(compose_file.parent)
            compose_base = self._compose_cmd()
            result = subprocess.run(compose_base + ["up", "-d", "--build"], env=compose_env, capture_output=True, text=True)
            if result.returncode == 0:
                # Wait up to 30 seconds for services to be Up
                for _ in range(30):
                    ps = subprocess.run(compose_base + ["ps"], capture_output=True, text=True, env=compose_env)
                    if "Up" in ps.stdout:
                        print(f"✅ {env_info['name']} started!")
                        self._show_access_info(env_name, ports)
                        return True
                    time.sleep(1)
                # Timeout: print logs
                print(f"❌ {env_info['name']} start timed out. Logs:")
                logs = subprocess.run(compose_base + ["logs", "--tail=50"], capture_output=True, text=True, env=compose_env)
                print(logs.stdout)
                return False
            else:
                print(f"❌ {env_info['name']} failed to start:")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ Failed to start environment: {e}")
            return False

    def _build_compose_env_vars(self, env_path: Path, ports: Dict[str, int]) -> Dict[str, str]:
        """Build env vars for docker-compose based on FullChain compose variables.
        Only used for FullChain to avoid modifying the original compose file.
        """
        import os
        compose_file = _find_compose_file(env_path)
        env_vars = os.environ.copy()
        try:
            content = compose_file.read_text(encoding='utf-8') if compose_file else ''
        except Exception:
            content = ''

        # FullChain variable naming rules
        # Support multiple variable names (inject if present in compose)
        mapping_multi = {
            'web': ['FC_FANTASTIC_PORT'],
            'dawa': ['FC_DAWA_PORT'],
            # FullChain2
            'fc2_apache': ['FC2_APACHE_PORT'],
            # FullChain3
            'fc3_ed01': ['FC3_ED01_PORT'],
            'fc3_pgadmin': ['FC3_PGADMIN_PORT']
            ,
            # FullChain4
            'fc4_cve_2022_32991': ['FC4_CVE_2022_32991_PORT'],
            'fc4_cve_2023_50564': ['FC4_CVE_2023_50564_PORT']
            ,
            # FullChain5
            'fc5_cve_2023_7130': ['FC5_CVE_2023_7130_PORT'],
            'fc5_cve_2023_39361': ['FC5_CVE_2023_39361_PORT']
        }

        # Inject only if the variable appears in compose content
        for key, var_names in mapping_multi.items():
            if ports.get(key) is None:
                continue
            for var_name in var_names:
                if var_name in content:
                    env_vars[var_name] = str(ports[key])
                    break

        # Compatibility for keys like ${VAR:-PORT} in datasets.json (e.g., ${HTTP_PORT:-8080})
        for k, v in ports.items():
            if isinstance(k, str) and k.startswith('${') and k.endswith('}'):
                var = k[2:-1].split(':')[0]
                env_vars[var] = str(v)

        return env_vars

    def start_by_task(self, task: str) -> bool:
        env_name = self.task_to_env.get(task)
        if not env_name:
            print(f"❌ Task {task} has no mapped environment")
            return False
        
        # Allocate available ports (avoid conflicts). Fallback to static ports on failure
        try:
            ports = port_manager.allocate_ports_for_environment(env_name)
        except Exception:
            task_info = dataset_manager.get_task(task)
            ports = task_info.get('ports', {}) if task_info else None
        
        # Generate and prepare flags
        print(f"🎯 Generate and prepare flags for task {task}...")
        self.generate_flags_for_task(task)

        # Pre-start cleanup: SQL flags require volume cleanup to avoid cache
        remove_volumes = self.task_requires_fresh_volumes(task)
        if remove_volumes:
            print("🧹 Pre-start cleanup (including volumes) to avoid stale flags...")
        else:
            print("🧹 Pre-start cleanup (excluding volumes)...")
        self.prestart_cleanup(env_name, remove_volumes=remove_volumes)
        
        # Start environment with port config
        return self.start_environment(env_name, ports)

    def start_by_category(self, category: str) -> bool:
        env_names = self.category_to_envs.get(category, [])
        if not env_names:
            print(f"❌ Category {category} has no environments")
            return False
        success_count = 0
        for env_name in env_names:
            if self.start_environment(env_name):
                success_count += 1
        print(f"✅ Started {success_count}/{len(env_names)} environments")
        return success_count > 0

    def stop_environment(self, env_name: str) -> bool:
        env_info = self.environments.get(env_name)
        if not env_info:
            print(f"❌ Environment not found: {env_name}")
            return False
        env_path = env_info["path"]
        if not env_path or not env_path.exists():
            print(f"❌ Environment path does not exist: {env_path}")
            return False
        print(f"🛑 Stopping {env_info['name']}...")
        try:
            compose_file = _find_compose_file(env_path)
            if not compose_file:
                print(f"❌ Compose file not found: {env_path}")
                return False
            os.chdir(compose_file.parent)
            compose_base = self._compose_cmd()
            result = subprocess.run(compose_base + ["down"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {env_info['name']} stopped!")
                return True
            else:
                print(f"❌ {env_info['name']} failed to stop:")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ Failed to stop environment: {e}")
            return False

    def cleanup_environment(self, env_name: str, remove_images: bool = True, remove_volumes: bool = False) -> bool:
        """Clean environment thoroughly: stop containers, remove containers, images and volumes"""
        env_info = self.environments.get(env_name)
        if not env_info:
            print(f"❌ Environment not found: {env_name}")
            return False
        env_path = env_info["path"]
        if not env_path or not env_path.exists():
            print(f"❌ Environment path does not exist: {env_path}")
            return False
        
        print(f"🧹 Cleaning {env_info['name']}...")
        try:
            compose_file = _find_compose_file(env_path)
            if not compose_file:
                print(f"❌ Compose file not found: {env_path}")
                return False
            
            original_dir = os.getcwd()
            os.chdir(compose_file.parent)
            
            # 1. Stop and remove containers (basic cleanup)
            print("🛑 Stopping and removing containers...")
            compose_base = self._compose_cmd()
            down_cmd = compose_base + ["down"]
            if remove_volumes:
                down_cmd.append("--volumes")
            
            result = subprocess.run(down_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"⚠️ docker-compose down warning: {result.stderr}")
            
            # 2. Get compose project name (default: lowercase dir name)
            project_name = compose_file.parent.name.lower()
            
            # 3. Remove remaining containers
            print("🔄 Removing remaining containers...")
            ps_result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={project_name}", "--format", "{{.ID}}"],
                capture_output=True, text=True
            )
            if ps_result.stdout.strip():
                container_ids = ps_result.stdout.strip().split('\n')
                subprocess.run(["docker", "rm", "-f"] + container_ids, capture_output=True)
                print(f"   Removed containers: {len(container_ids)}")
            
            # 4. Remove images (if requested)
            if remove_images:
                print("🖼️ Removing related images...")
                # Get images of the project
                images_result = subprocess.run(
                    ["docker", "images", "--filter", f"label=com.docker.compose.project={project_name}", "--format", "{{.ID}}"],
                    capture_output=True, text=True
                )
                if images_result.stdout.strip():
                    image_ids = list(set(images_result.stdout.strip().split('\n')))  # deduplicate
                    subprocess.run(["docker", "rmi", "-f"] + image_ids, capture_output=True)
                    print(f"   Removed images: {len(image_ids)}")
            
            # 5. Remove volumes (only when explicitly requested)
            if remove_volumes:
                print("💾 Removing related volumes...")
                volumes_result = subprocess.run(
                    ["docker", "volume", "ls", "--filter", f"label=com.docker.compose.project={project_name}", "--format", "{{.Name}}"],
                    capture_output=True, text=True
                )
                if volumes_result.stdout.strip():
                    volume_names = volumes_result.stdout.strip().split('\n')
                    subprocess.run(["docker", "volume", "rm", "-f"] + volume_names, capture_output=True)
                    print(f"   Removed volumes: {len(volume_names)}")
            
            os.chdir(original_dir)
            print(f"✅ {env_info['name']} cleanup completed!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to clean environment: {e}")
            return False

    def cleanup_by_task(self, task: str, remove_images: bool = True, remove_volumes: bool = False) -> bool:
        """Cleanup by task ID"""
        env_name = self.task_to_env.get(task)
        if not env_name:
            print(f"❌ Task {task} has no mapped environment")
            return False
        return self.cleanup_environment(env_name, remove_images, remove_volumes)

    def cleanup_by_category(self, category: str, remove_images: bool = True, remove_volumes: bool = False) -> bool:
        """Cleanup all envs by category"""
        env_names = self.category_to_envs.get(category, [])
        if not env_names:
            print(f"❌ Category {category} has no environments")
            return False
        
        success_count = 0
        for env_name in env_names:
            if self.cleanup_environment(env_name, remove_images, remove_volumes):
                success_count += 1
        
        print(f"✅ Cleaned {success_count}/{len(env_names)} environments")
        return success_count > 0

    def get_environment_status(self, env_name: str) -> Dict:
        env_info = self.environments.get(env_name)
        if not env_info:
            return {"status": "not_found"}
        env_path = env_info["path"]
        if not env_path or not env_path.exists():
            return {"status": "path_not_found"}
        try:
            os.chdir(env_path)
            result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                if "Up" in result.stdout:
                    return {"status": "running"}
                else:
                    return {"status": "stopped"}
            else:
                return {"status": "error", "error": result.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def read_file_in_container(self, env_name: str, file_path: str) -> str:
        """Read a file from the container of the given environment (assumes a single primary container)"""
        env_info = self.environments.get(env_name)
        if not env_info:
            raise Exception(f"Environment not found: {env_name}")
        env_path = env_info["path"]
        compose_file = _find_compose_file(env_path)
        if not compose_file:
            raise Exception(f"Compose file not found: {env_path}")
        # Get main container id
        os.chdir(compose_file.parent)
        ps = subprocess.run(["docker-compose", "ps", "-q"], capture_output=True, text=True)
        container_ids = [line.strip() for line in ps.stdout.splitlines() if line.strip()]
        if not container_ids:
            raise Exception("No running container found")
        container_id = container_ids[0]
        cat = subprocess.run(["docker", "exec", container_id, "cat", file_path], capture_output=True, text=True)
        if cat.returncode == 0:
            return cat.stdout.strip()
        else:
            raise Exception(f"Failed to read file in container: {cat.stderr}")

    def _generate_random_flag(self) -> str:
        """Generate a random flag"""
        random_str = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(30))
        return f"flag{{{random_str}}}"

    def _create_flag_file(self, flag_content: str, flag_type: str) -> str:
        """Create flag file content according to type"""
        if flag_type == "sql":
            return f"""CREATE TABLE IF NOT EXISTS flags (
  id INTEGER PRIMARY KEY,
  flag CHAR(255)
  );

INSERT INTO flags (id, flag) VALUES (1, '{flag_content}') ON DUPLICATE KEY UPDATE flag = VALUES(flag);
"""
        else:  # file type
            return flag_content

    def generate_flags_for_task(self, task_name: str) -> Dict[str, str]:
        """Generate flags for the specified task"""
        task_info = dataset_manager.get_task(task_name)
        if not task_info:
            return {}

        flags = {}
        flag_type = task_info.get('flag_type')
        
        if flag_type == "mixed":
            # Handle multiple flags
            flag_locations = task_info.get('flag_locations', {})
            for flag_name, flag_config in flag_locations.items():
                flag_content = self._generate_random_flag()
                flags[flag_name] = flag_content
                
                # Create flag file
                flag_file_content = self._create_flag_file(flag_content, flag_config['type'])
                flag_file_path = self.flags_dir / f"{task_name}_{flag_name}.{'sql' if flag_config['type'] == 'sql' else 'txt'}"
                
                with open(flag_file_path, 'w', encoding='utf-8') as f:
                    f.write(flag_file_content)
                    
                print(f"📝 Generated {flag_name}: {flag_content}")
        elif flag_type in ["sql", "file"]:
            # Handle single flag
            flag_content = self._generate_random_flag()
            flags["flag"] = flag_content
            
            # Create flag file
            flag_file_content = self._create_flag_file(flag_content, flag_type)
            flag_file_path = self.flags_dir / f"{task_name}_flag.{'sql' if flag_type == 'sql' else 'txt'}"
            
            with open(flag_file_path, 'w', encoding='utf-8') as f:
                f.write(flag_file_content)
                
            print(f"📝 Generated flag: {flag_content}")

        # Save flags into global flags.json
        self._update_global_flags(task_info['id'], flags)

        # Prepare all flags (pre-build)
        env_name = self.task_to_env.get(task_name)
        if flags and env_name:
            print("📋 Preparing flags...")
            self.prepare_flags_for_build(task_name, env_name)

        return flags

    def _update_global_flags(self, task_id: str, flags: Dict[str, str]):
        """Update global flags.json"""
        global_flags_path = self.flags_dir / "flags.json"
        
        # Read existing flags
        all_flags = {}
        if global_flags_path.exists():
            with open(global_flags_path, 'r', encoding='utf-8') as f:
                all_flags = json.load(f)
        
        # Update flags for current task
        if len(flags) == 1 and "flag" in flags:
            # Single flag
            all_flags[task_id] = flags["flag"]
        else:
            # Multiple flags
            all_flags[task_id] = flags
        
        # Save back to file
        with open(global_flags_path, 'w', encoding='utf-8') as f:
            json.dump(all_flags, f, indent=2, ensure_ascii=False)

    def get_task_flags(self, task_name: str) -> Dict[str, str]:
        """Get flags of a task"""
        task_info = dataset_manager.get_task(task_name)
        if not task_info:
            return {}
        
        task_id = task_info['id']
        global_flags_path = self.flags_dir / "flags.json"
        
        if global_flags_path.exists():
            with open(global_flags_path, 'r', encoding='utf-8') as f:
                all_flags = json.load(f)
                if task_id in all_flags:
                    flag_value = all_flags[task_id]
                    if isinstance(flag_value, str):
                        return {"flag": flag_value}
                    else:
                        return flag_value
        return {}

    def prepare_flags_for_build(self, task_name: str, env_name: str) -> bool:
        """Prepare all flag files for build (copy to configured locations)"""
        task_info = dataset_manager.get_task(task_name)
        if not task_info:
            return False

        env_info = self.environments.get(env_name)
        if not env_info:
            return False

        env_path = env_info["path"]
        flag_type = task_info.get('flag_type')
        
        try:
            import shutil

            def safe_copy_flag_file(source_file, dest_file, flag_name):
                """Safely copy the flag file, handling the case where destination is a directory"""
                # Normalize: if absolute and under env path, keep; else map into env path
                try:
                    if dest_file.is_absolute():
                        try:
                            rel = dest_file.relative_to(env_path)
                        except ValueError:
                            # If not under env path, fallback to file name only
                            rel = dest_file.name
                        dest_file = env_path / rel
                except Exception:
                    dest_file = env_path / Path(str(dest_file)).name
                if dest_file.exists():
                    if dest_file.is_dir():
                        print(f"⚠️ Destination is a directory, removing: {dest_file}")
                        shutil.rmtree(dest_file)
                    else:
                        print(f"📄 Overwriting existing file: {dest_file}")
                
                # Ensure parent directory exists
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_file, dest_file)
                print(f"📋 Prepared {flag_name} to: {dest_file}")
            
            if flag_type == "mixed":
                # Handle multiple flags
                flag_locations = task_info.get('flag_locations', {})
                for flag_name, flag_config in flag_locations.items():
                    if flag_config['type'] == 'sql':
                        source_file = self.flags_dir / f"{task_name}_{flag_name}.sql"
                        if source_file.exists():
                            # Use configured relative path
                            flag_path = flag_config.get('flag_path', f'{flag_name}.sql')
                            dest_file = env_path / flag_path
                            safe_copy_flag_file(source_file, dest_file, f"SQL flag {flag_name}")
                    elif flag_config['type'] == 'file':
                        source_file = self.flags_dir / f"{task_name}_{flag_name}.txt"
                        if source_file.exists():
                            # Use configured relative path
                            flag_path = flag_config.get('flag_path', f'{flag_name}.txt')
                            dest_file = env_path / flag_path
                            safe_copy_flag_file(source_file, dest_file, f"file flag {flag_name}")
                            
            elif flag_type == "sql":
                # Handle single SQL flag
                source_file = self.flags_dir / f"{task_name}_flag.sql"
                if source_file.exists():
                    # Use configured relative path
                    flag_path = task_info.get('flag_path', 'flag.sql')
                    dest_file = env_path / flag_path
                    safe_copy_flag_file(source_file, dest_file, "SQL flag")
            elif flag_type == "file":
                # Handle single file flag
                source_file = self.flags_dir / f"{task_name}_flag.txt"
                if source_file.exists():
                    # Use configured relative path
                    flag_path = task_info.get('flag_path', 'flag.txt')
                    dest_file = env_path / flag_path
                    safe_copy_flag_file(source_file, dest_file, "file flag")

            return True
            
        except Exception as e:
            print(f"❌ Failed to prepare flags: {e}")
            return False

    def task_requires_fresh_volumes(self, task_name: str) -> bool:
        """Decide if volumes must be pruned before start to avoid stale flags.
        Rules:
        - Clean when flag_type == 'sql'
        - Clean when flag_type == 'mixed' and any flag has type == 'sql'
        - Clean when compose includes persistent DB/init dirs (/var/lib/mysql, /var/lib/postgresql/data, docker-entrypoint-initdb.d)
        """
        try:
            # Prioritize cleanup if the environment has persistent DB volumes
            env_name = self.task_to_env.get(task_name)
            if env_name and self.env_requires_fresh_volumes(env_name):
                return True

            task_info = dataset_manager.get_task(task_name)
            if not task_info:
                return False
            flag_type = task_info.get('flag_type')
            if flag_type == 'sql':
                return True
            if flag_type == 'mixed':
                flag_locations = task_info.get('flag_locations', {})
                for _flag_name, flag_cfg in flag_locations.items():
                    try:
                        if str(flag_cfg.get('type', '')).lower() == 'sql':
                            return True
                    except Exception:
                        continue
            return False
        except Exception:
            return False

    def prestart_cleanup(self, env_name: str, remove_volumes: bool = True) -> bool:
        """Cleanup before start; by default containers only. When remove_volumes=True, include volumes."""
        try:
            return self.cleanup_environment(env_name, remove_images=True, remove_volumes=remove_volumes)
        except Exception:
            return False

    def env_requires_fresh_volumes(self, env_name: str) -> bool:
        """Determine whether the environment requires volume cleanup.
        Triggered when any of these holds:
        - Compose includes persistent DB dirs (/var/lib/mysql, /var/lib/postgresql/data)
        - Compose includes init dir (docker-entrypoint-initdb.d)
        - Any mapped task uses SQL-type flags (backward compatibility)
        """
        try:
            # First detect persistent DB markers in compose content
            env_info = self.environments.get(env_name)
            if env_info:
                env_path = env_info["path"]
                compose_file = _find_compose_file(env_path)
                if compose_file and compose_file.exists():
                    try:
                        content = compose_file.read_text(encoding='utf-8')
                    except Exception:
                        content = ''
                    db_markers = [
                        '/var/lib/mysql',
                        '/var/lib/postgresql/data',
                        'docker-entrypoint-initdb.d'
                    ]
                    if any(marker in content for marker in db_markers):
                        return True

            # Compatibility: if any SQL-type task belongs to this environment, clean volumes as well
            for category in dataset_manager.list_categories():
                tasks = dataset_manager.get_datasets(category)
                for _task_name, task_info in tasks.items():
                    if task_info.get('environment') != env_name:
                        continue
                    flag_type = task_info.get('flag_type')
                    if flag_type == 'sql':
                        return True
                    if flag_type == 'mixed':
                        flag_locations = task_info.get('flag_locations', {})
                        for _fname, _fcfg in flag_locations.items():
                            try:
                                if str(_fcfg.get('type', '')).lower() == 'sql':
                                    return True
                            except Exception:
                                continue
            return False
        except Exception:
            return False
    def cleanup_incorrect_flag_directories(self) -> bool:
        """Remove all incorrectly created flag.txt directories"""
        print("🧹 Checking and removing incorrect flag.txt directories...")
        cleaned_count = 0
        
        for env_name, env_info in self.environments.items():
            env_path = env_info["path"]
            if not env_path.exists():
                continue
                
            # Check whether a flag.txt directory exists
            flag_txt_path = env_path / "flag.txt"
            if flag_txt_path.exists() and flag_txt_path.is_dir():
                try:
                    import shutil
                    shutil.rmtree(flag_txt_path)
                    print(f"🗑️ Removed incorrect flag.txt directory: {flag_txt_path}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"❌ Failed to remove directory {flag_txt_path}: {e}")
        
        if cleaned_count > 0:
            print(f"✅ Removed {cleaned_count} incorrect flag.txt directories")
        else:
            print("✅ No incorrect flag.txt directories found")
        
        return True


# Global instance
docker_manager = DockerManager() 