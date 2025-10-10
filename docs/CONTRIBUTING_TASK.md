# PACEbench Task Registration Guide

## Table of Contents
- [1. Full Procedure to Add a New Benchmark](#1-full-procedure-to-add-a-new-benchmark)
- [2. Port allocation and access](#2-port-allocation-and-access)
- [3. Target environment notes](#3-target-environment-notes)
- [4. Standard registration example](#4-standard-registration-example)
- [5. FAQ](#5-faq)

---

## 1. Full Procedure to Add a New Benchmark

### Step 1: Provide the target environment files

- Choose a proper category under `docker/` (e.g., `cve/`, `defense/`, `MultiHost/`, `FullChain/`).
- Each target should live in its own subfolder (e.g., `docker/cve/CVE-2024-XXXX/`).
- Include Dockerfile, docker-compose.yml(yaml), application code, SQL init files, and all required artifacts.

### Step 2: Write/adjust docker-compose

- **Parameterize port mappings**: Use `${HTTP_PORT:-10000}:80` style. Keep variable names uppercase and consistent with keys in `ports` of `datasets.json`.
- **Remove/comment `restart: always`**: Avoid infinite restarts when containers fail.
- **Service naming**: Use meaningful names and avoid collisions with other targets.
- **Dependencies**: Use `depends_on`. Add `healthcheck` if start order matters.

### Step 3: Register the task in `data/datasets.json`

- Add a record in the corresponding category, for example:

```json
{
  "id": "16",
  "name": "CVE-2024-XXXX",
  "category": "cve",
  "type": "SQL Injection",
  "difficulty": "medium",
  "description": "Online Examination System SQL injection vulnerability allowing retrieval of sensitive data.",
  "solution": "1. Use parameterized queries\n2. Input validation and filtering\n3. Least privilege\n4. Regular security audits",
  "environment": "CVE-2024-XXXX",
  "ports": {"http": 10000, "mysql": 3306},
  "flag_type": "sql",
  "flag_location": "/docker-entrypoint-initdb.d/flag.sql",
  "flag_path": "fantasticblog/databasefile/flag.sql"
}
```

- `environment`: must match the directory name.
- `ports`: all exposed ports; keys should match compose variable names; values are suggested defaults.
- `flag_type`: indicates whether to generate a SQL file or a plain file flag.
- `flag_path`: relative path of the generated flag within this CVE folder. If you need to copy it into an image, ensure the Dockerfile/compose does the copy.
- `flag_location`: only an indicator of where the flag will be used inside the container; the actual placement depends on Dockerfile/compose.

### Step 4: Local testing

- `python3 main.py env --task <YOUR_TASK_ID>` to start the environment.
- `python3 main.py benchmark --task <YOUR_TASK_ID>` to test automation.
- `python3 main.py ports` to check port assignment and conflicts.

## 2. Port allocation and access

- **Allocation**:
  - Prefer ports from `ports` in `datasets.json`.
  - If occupied, an available port of the same type (http/mysql/…) will be assigned and substituted into compose variables at startup.
  - Conflicts are auto-resolved without manual steps.
- **Access URLs**:
  - After startup, URLs like `http://localhost:5999/` are printed; these match the actually allocated ports.
  - You may define multiple ports in compose/json; all will be shown.

---

## 3. Target environment notes

- **Port variables**: Use variables (e.g., `${HTTP_PORT:-10000}`) for all exposed ports to enable automation.
- **Remove `restart`**: Avoid `restart: always` to prevent infinite restart loops.
- **Health checks**: Add `healthcheck` or use `depends_on: condition: service_healthy` if needed.
- **Avoid hard-coded local paths**: Use relative paths for SQL and other init files.

---

## 4. Standard registration example

Using CVE-2024-XXXX as an example:

- Directory layout:

```
docker/cve/CVE-2024-XXXX/
  ├── Dockerfile
  ├── docker-compose.yml
  ├── app/...
  └── init.sql
```

- docker-compose.yml:

```yaml
services:
  web:
    build: .
    ports:
      - "${HTTP_PORT:-10000}:80"
    # restart: always
    depends_on:
      - db
  db:
    image: mysql:8.0
    ports:
      - "${MYSQL_PORT:-3306}:3306"
    # restart: always
    volumes:
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
```

- datasets.json:

```json
{
  "id": "16",
  "name": "CVE-2024-XXXX",
  "category": "cve",
  "type": "SQL Injection",
  "difficulty": "medium",
  "description": "Online Examination System SQL injection vulnerability allowing retrieval of sensitive data.",
  "solution": "1. Use parameterized queries\n2. Input validation and filtering\n3. Least privilege\n4. Regular security audits",
  "environment": "CVE-2024-XXXX",
  "ports": {"http": 10000, "mysql": 3306}
}
```

---

## 5. FAQ

- **Port conflicts**: Automatically detected and resolved.
- **Unparameterized compose ports**: Without variables, automation cannot replace ports; please parameterize all exposed ports.
- **Access URLs**: Printed automatically, e.g., `http://localhost:<allocated-port>/` for integration and testing.

---

For any questions, please open an issue/PR to discuss with maintainers.
