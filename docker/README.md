# Docker Environment Management

This directory contains all Docker target environments for the PACEbench framework.

## Directory Structure

```
docker/
├── cve/              # CVE scenarios
├── MultiHost/        # Multi-IP scenarios
├── FullChain/        # Full-chain attack scenarios
├── defense/          # Defense evasion scenarios
│   └── naive_waf/    # NAIVE-WAF scenario
└── README.md         # This file
```

## Integrated Environments

### NAIVE-WAF Scenario
- **Location**: `defense/naive_waf/`
- **Task**: NAIVE-WAF (ID 14)
- **Ports**: 8082 (WAF), 8083 (application service)
- **Description**: WAF bypass scenario containing an SQL injection vulnerability

## Add a New Environment

### 1. Create the environment directory
Create a new environment directory under the corresponding category:
```bash
mkdir docker/cve/my_new_cve/
```

### 2. Add Docker files
Add the required Docker files in the new environment directory:
- `docker-compose.yml` - container orchestration file
- `Dockerfile` - image build file
- `requirements.txt` - Python dependencies (if needed)
- `README.md` - environment documentation

### 3. Register the environment
Register the new environment in `utils/docker_manager.py`:

```python
self.environments = {
    "NAIVE-WAF": {
        "path": "defense/naive_waf",
        "ports": ["8082", "8083"],
        "description": "WAF bypass scenario - user management system with an SQL injection vulnerability"
    },
    "MY_NEW_CVE": {  # Added
        "path": "cve/my_new_cve",
        "ports": ["8084"],
        "description": "Description of the new CVE scenario"
    }
}
```

### 4. Add task mapping
Add task-to-environment mapping in the `start_by_task` method:

```python
task_to_env = {
    "NAIVE-WAF": "NAIVE-WAF",
    "MY_NEW_CVE": "MY_NEW_CVE"  # Added
}
```

### 5. Add category mapping
Add category-to-environments mapping in the `start_by_category` method:

```python
category_to_envs = {
    "defense": ["NAIVE-WAF"],
    "cve": ["MY_NEW_CVE"]  # Added
}
```

## Environment Guidelines

### Docker Compose file
- Use `version: '3.8'` or higher
- Explicitly specify port mappings
- Set appropriate container names
- Handle service dependencies

### Port management
- Avoid port conflicts
- Explicitly list all ports in the environment configuration
- Provide access address information

### Documentation requirements
Each environment directory should include:
- `README.md` - detailed environment description
- Default users and passwords
- Vulnerable points and attack methods
- Access addresses and ports

## Usage Examples

```bash
# Start a specific environment
python3 main.py env --task NAIVE-WAF

# Start all environments in a category
python3 main.py env --dataset defense

# Show environment info
python3 main.py show --task NAIVE-WAF
```

## Troubleshooting

### Common issues
1. **Port conflicts**: Check whether the ports are already in use
2. **Network issues**: Ensure Docker networking is functioning properly
3. **Permission issues**: Ensure you have permissions to operate Docker
4. **Image build failures**: Check the Dockerfile and dependencies

### Debugging commands
```bash
# Check container status
docker ps

# View service logs
docker-compose logs

# Rebuild images
docker-compose build --no-cache

# Clean up environment
docker-compose down -v
```