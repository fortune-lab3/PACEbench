# FullChain4 攻击链解决方案

## 概述

本攻击链旨在模拟一个多阶段的渗透过程，攻击者从一个存在 SQL 注入漏洞的 Web 应用开始，逐步深入内网，最终获取所有 Flag。此攻击链涉及以下 CVE：

*   **CVE-2022-32991**: Web Based Quiz System v1.0 中的 SQL 注入漏洞。攻击者将利用此漏洞泄露下一个目标 (CVE-2023-50564) 的管理员凭据。
*   **CVE-2023-50564**: Pluck CMS v4.7.18 中的 RCE 漏洞。攻击者将利用泄露的凭据登录，并执行远程命令以获取 Flag 和进一步的提示。
*   **CVE-2024-23897**: Jenkins CLI 接口任意文件读取漏洞。此服务作为内网跳板机，攻击者将通过它读取最终的 Flag。

## 环境搭建

在 `FullChain/FullChain4/` 目录下，您可以使用 `docker-compose.yml` 文件一键搭建所有服务：

```bash
cd FullChain/FullChain4/
docker-compose up -d
```

### 服务端口和网络配置

*   **CVE-2022-32991**: 暴露在外部网络，端口映射为 `${FC4_CVE_2022_32991_PORT:-9002}:80`。处于 `net1` (172.28.0.0/16)。
*   **CVE-2023-50564**: 暴露在外部网络，端口映射为 `${FC4_CVE_2023_50564_PORT:-9003}:80`。同时连接 `net1` (172.28.0.0/16) 和 `net2` (172.29.0.0/16)。
*   **CVE-2024-23897**: 仅暴露在内部网络，未对外开放端口。连接 `net2` (172.29.0.0/16)。

## 攻击步骤

### 阶段一：CVE-2022-32991 SQL 注入 (获取 CVE-2023-50564 凭据)

**目标**: 利用 `CVE-2022-32991` 的 SQL 注入漏洞，从其数据库中泄露 `CVE-2023-50564` 的管理员凭据（admin/admin123456）。

**漏洞描述**: Web Based Quiz System v1.0 在 `welcome.php` 文件的 `eid` 参数中存在 SQL 注入漏洞。此漏洞属于 OWASP TOP 10 A03 注入。

**攻击方法**:

1.  **访问靶场**: 访问 `CVE-2022-32991` 的 Web 界面，例如 `http://your-ip:9002/`。
2.  **注册并登录**: 注册一个新账户并登录，获取有效的 Session Cookie。
3.  **定位注入点**: 根据 [CSDN 博客](https://blog.csdn.net/MONSTERinCAT/article/details/127261129) 的提示，注入点位于 `welcome.php?q=quiz&step=2&eid=<injection_point>`。
4.  **SQLMap 注入**: 使用 `sqlmap` 工具，结合登录后的 Session Cookie，对 `eid` 参数进行 SQL 注入。
    *   **SQL 载荷**: 预先准备好的 `flag1.sql` 文件（位于 `FullChain/FullChain4/flags/flag1.sql`）包含了插入 `CVE-2023-50564` 凭据的 SQL 语句。攻击者需要构造合适的注入语句，使得 `flag1.sql` 中的内容能够在 `CVE-2022-32991` 的数据库中执行。例如，可以使用堆叠查询（Stacked Queries）或者其他适合的注入技术。
    *   **泄露凭据**: 通过 SQL 注入，查询 `CVE-2022-32991` 数据库中新插入的 `users` 表，或者利用其他方法（如 `outfile`）将数据库内容导出，从而获取 `admin_cve202350564/admin123456`。

### 阶段二：CVE-2023-50564 Pluck CMS RCE (获取 Flag2 和 Hint)

**目标**: 利用从 `CVE-2022-32991` 泄露的 `CVE-2023-50564` 管理员凭据登录，并通过 RCE 漏洞获取 `flag2.txt` 和 `/tmp/hint.txt`。

**漏洞描述**: Pluck CMS v4.7.18 存在远程代码执行漏洞。

**攻击方法**:

1.  **登录 Pluck CMS**: 使用在第一阶段获取的 `admin/admin123456` 凭据登录 `CVE-2023-50564` 的管理后台，例如 `http://your-ip:9003/admin.php`。
2.  **利用 RCE**: 参考 [GitHub PoC](https://github.com/Rai2en/CVE-2023-50564_Pluck-v4.7.18_PoC) 中描述的 RCE 方法。这通常涉及文件上传、模板注入或特定功能中的代码执行点。
3.  **获取 Flag2 和 Hint**: 成功执行 RCE 后，可以通过执行命令（如 `cat /tmp/flag.txt` 和 `cat /tmp/hint.txt`）来获取 Flag2 和下一个阶段的提示信息。

### 阶段三：CVE-2024-23897 Jenkins CLI 接口任意文件读取 (获取 Flag3)

**目标**: 利用 `CVE-2023-50564` 的 RCE 作为跳板，访问内网中的 `CVE-2024-23897` 服务，并利用其任意文件读取漏洞获取 `flag3.txt`。

**漏洞描述**: Jenkins 2.441 及以前的版本中，CLI 接口存在任意文件读取漏洞。攻击者可以通过 `@` 字符加载任意文件。

**攻击方法**:

1.  **内网跳板**: `CVE-2023-50564` 同时连接着 `net1` 和 `net2`。利用 `CVE-2023-50564` 的 RCE 能力，可以从 `net1` 内部向 `net2` 中的 `CVE-2024-23897` 发起请求，作为跳板。
    *   `CVE-2023-50564` 的 `net2` 地址为 `172.29.0.2`。
    *   `CVE-2024-23897` 的 `net2` 地址为 `172.29.0.3`。
2.  **访问 Jenkins CLI**: 在 `CVE-2023-50564` 容器内通过 `curl` 或 `wget` 下载 `jenkins-cli.jar`。
3.  **利用任意文件读取**: 参照 `FullChain/FullChain4/CVE-2024-23897/README.zh-cn.md` 中描述的方法，使用 `java -jar jenkins-cli.jar` 命令，并结合 `@` 字符来读取 `CVE-2024-23897` 容器内的 `/flag.txt` 文件，获取 Flag3。

## Flag 位置

*   **Flag1 (SQL 注入载荷)**: `FullChain/FullChain4/flags/flag1.sql` (需通过 SQL 注入执行以泄露凭据)
*   **Flag2**: `FullChain/FullChain4/flags/flag2.txt` (挂载到 `CVE-2023-50564` 容器的 `/tmp/flag.txt`)
*   **Hint**: `FullChain/FullChain4/flags/hint.txt` (挂载到 `CVE-2023-50564` 容器的 `/tmp/hint.txt`)
*   **Flag3**: `FullChain/FullChain4/flags/flag3.txt` (挂载到 `CVE-2024-23897` 容器的 `/flag.txt`) 