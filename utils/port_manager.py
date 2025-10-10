#!/usr/bin/env python3
"""
Port Manager
"""

import socket
import random
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json
from data.dataset_manager import dataset_manager

class PortManager:
    def __init__(self):
        self.config_file = Path(__file__).parent.parent / "config" / "port_config.json"
        self.config_file.parent.mkdir(exist_ok=True)
        self.default_ports = self._build_default_ports()
        self.port_ranges = {
            "waf": (8000, 8999),
            "backend": (5000, 5999),
            "https": (8443, 8443),
            "multiple_host": (10000, 19999)
        }
        self.allocated_ports = self.load_port_config()

    def _build_default_ports(self) -> Dict[str, Dict[str, int]]:
        ports = {}
        for category in dataset_manager.list_categories():
            tasks = dataset_manager.get_datasets(category)
            for task_name, task_info in tasks.items():
                env_name = task_info.get('environment')
                port_info = task_info.get('ports')
                if env_name and port_info:
                    ports[env_name] = port_info
        return ports

    def load_port_config(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_port_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.allocated_ports, f, indent=2, ensure_ascii=False)

    def is_port_available(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    return False
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(1)
                try:
                    sock.bind(('localhost', port))
                    return True
                except OSError:
                    return False
        except Exception:
            return False

    def check_docker_port_conflicts(self, port: int) -> bool:
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Ports}}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f":{port}->" in line or f":{port}/" in line:
                        return True
            return False
        except Exception:
            return False

    def is_port_truly_available(self, port: int) -> bool:
        if not self.is_port_available(port):
            return False
        if self.check_docker_port_conflicts(port):
            return False
        return True

    def _get_port_range(self, port_type: str) -> Tuple[int, int]:
        return self.port_ranges.get(port_type, (8000, 8999))

    def _determine_port_type(self, port_type: str, default_port: int) -> str:
        normalized = str(port_type).lower()
        # WAF-like ports: infer from key name or common public ports
        if (
            "waf" in normalized or
            "apache" in normalized or
            "nginx" in normalized or
            "http" in normalized or
            "admin" in normalized or
            default_port in [80, 8080, 8081, 8082, 8083, 8084, 8085]
        ):
            return "waf"
        # Multi-host scenario: common names or the port range
        elif port_type in ["web", "gitea", "wordpress"] or (10000 <= default_port < 20000):
            return "multiple_host"
        # Compatibility with fc*/mh* prefixes (e.g., fc2_apache, mh3_pgadmin)
        elif normalized.startswith("fc") or normalized.startswith("mh"):
            return "multiple_host"
        elif "backend" in normalized or default_port in [5000, 5584]:
            return "backend"
        elif "https" in normalized or default_port in [443, 8443]:
            return "https"
        else:
            return "backend"

    def find_available_port(self, port_type: str, start_port: Optional[int] = None) -> int:
        range_start, range_end = self._get_port_range(port_type)
        # Normalize start port within the range
        if start_port is None or start_port < range_start or start_port > range_end:
            cursor = range_start
        else:
            cursor = start_port

        # Scan forward from cursor; do not wrap to avoid reusing allocated ports
        for port in range(cursor, range_end + 1):
            if self.is_port_truly_available(port):
                return port

        # Fallback: scan from range start to cursor-1, but only wrap for non-multiple_host types
        if port_type != "multiple_host":
            for port in range(range_start, cursor):
                if self.is_port_truly_available(port):
                    return port

        # Last resort: random attempts (avoid long blocking)
        attempts = 0
        max_attempts = 100
        while attempts < max_attempts:
            port = random.randint(range_start, range_end)
            if self.is_port_truly_available(port):
                return port
            attempts += 1

        raise RuntimeError(f"No available {port_type} port found")

    def allocate_ports_for_environment(self, env_name: str, force_reallocate: bool = False) -> Dict[str, int]:
        if not force_reallocate and env_name in self.allocated_ports:
            ports = self.allocated_ports[env_name]
            if all(self.is_port_truly_available(port) for port in ports.values()):
                return ports
        if env_name not in self.default_ports:
            raise ValueError(f"Unknown environment: {env_name}")
        new_ports: Dict[str, int] = {}
        used_ports: set[int] = set()
        default_config = self.default_ports[env_name]
        base_port = min([v for v in default_config.values() if 10000 <= v < 20000], default=10000)
        for idx, (port_type, default_port) in enumerate(default_config.items()):
            port_range = self._determine_port_type(port_type, default_port)
            # For multiple_host, allocate sequentially
            if port_range == "multiple_host":
                allocated_port = self.find_available_port(port_range, base_port + idx)
            else:
                allocated_port = self.find_available_port(port_range, default_port)
            # Ensure uniqueness within the same environment: if duplicate, keep searching forward
            while allocated_port in used_ports:
                next_start = allocated_port + 1
                allocated_port = self.find_available_port(port_range, next_start)
            used_ports.add(allocated_port)
            new_ports[port_type] = allocated_port
        self.allocated_ports[env_name] = new_ports
        self.save_port_config()
        return new_ports

    def allocate_multiple_ports(self, count: int, port_type: str = "multiple_host") -> List[int]:
        return [self.find_available_port(port_type) for _ in range(count)]

    def release_ports(self, env_name: str):
        if env_name in self.allocated_ports:
            del self.allocated_ports[env_name]
            self.save_port_config()

    def get_environment_ports(self, env_name: str) -> Optional[Dict[str, int]]:
        return self.allocated_ports.get(env_name)

    def list_allocated_ports(self) -> Dict[str, Dict[str, int]]:
        return self.allocated_ports.copy()

    def check_port_conflicts(self) -> List[Tuple[str, str, int]]:
        conflicts = []
        for env_name, ports in self.allocated_ports.items():
            for port_type, port in ports.items():
                if not self.is_port_available(port):
                    conflicts.append((env_name, port_type, port))
        return conflicts

# Global instance
port_manager = PortManager() 