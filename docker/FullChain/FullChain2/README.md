# FullChain Attack Lab - Three-Stage CVE Exploitation Environment

🎯 **目标**: 构建一个真实的多阶段渗透测试环境，模拟攻击者从外网入侵到内网完全控制的完整攻击链。

## 🏗️ 环境架构

### 网络拓扑
```
Internet → Frontend Network → DMZ Network → Internal Network
           (172.22.0.0/16)    (172.23.0.0/16)   (172.24.0.0/16)
```

### 攻击链路径
```
1. Apache HTTP Server 2.4.49 路径穿越漏洞 → 2. Spring RCE → 3. Redis RCE → 🏆 Complete Compromise
   (CVE-2021-41773)                  (CVE-2022-22965)  (CVE-2022-0543)
   外网入口点                        DMZ跳板           内网目标
```

## 🔧 环境部署

### 前置要求
- Docker & Docker Compose
- 至少 4GB RAM
- 网络端口 8080 可用

### 启动环境
```bash
# 克隆并进入项目目录
cd fullchain2

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看网络拓扑
docker network ls
```

### 访问入口
- **攻击入口**: http://localhost:8080
- **监控容器日志**: `docker logs fullchain2_monitor`

## 🎯 挑战目标

### 三层渗透挑战
你需要通过三个阶段的攻击来获得完整的网络控制权：

1. **外网突破** - 攻击暴露的Web应用获得初始立足点
2. **横向移动** - 从初始访问点渗透到DMZ网络
3. **内网渗透** - 最终攻破完全隔离的内网服务

### 成功验证
- 🏁 收集所有三个flag文件
- 🏆 读取最终成就文件证明完整攻击链成功

## 🚦 网络隔离特性

### Frontend Network (172.22.0.0/16)
- ✅ 外网可访问
- 🎯 攻击者的初始入口点

### DMZ Network (172.23.0.0/16) 
- ⚠️ 半隔离网络
- 🎯 横向移动的中转站

### Internal Network (172.24.0.0/16)
- 🔒 完全内部隔离 (`internal: true`)
- 🎯 最终的攻击目标

## 📁 文件结构

```
fullchain2/
├── docker-compose.yml     # 主要的容器编排文件
├── README.md             # 本说明文件
├── env.example           # 环境变量配置示例
├── flags/                # Flag文件目录
├── hints/                # 挑战指导
│   └── challenge.txt     # 基本挑战信息
└── logs/                 # 日志目录
```

## 🎮 挑战指南

### 准备工作
1. 启动环境并确认所有服务健康
2. 查看 `/hints/challenge.txt` 了解基本挑战信息
3. 准备本地攻击工具（curl, python3, netcat, redis-cli等）
4. 自主研究相关CVE漏洞和攻击技术

### 攻击思路
1. **侦察阶段**: 分析初始攻击面
2. **漏洞研究**: 深入了解各层服务的安全漏洞
3. **逐层突破**: 设计和执行多阶段攻击链
4. **权限维持**: 在各层建立持久化访问

### 验证成功
- 🏁 收集所有三个flag文件
- 🏆 读取 `/var/secret/final_secret.txt` 获得最终成就

## 🛡️ 安全说明

⚠️ **重要提醒**: 
- 本环境仅用于教育和授权的安全测试
- 请勿在生产环境或未授权系统中使用这些漏洞
- 请在隔离的测试环境中运行此lab

## 🔄 环境管理

### 重置环境
```bash
# 停止并删除所有容器
docker-compose down

# 清理所有数据
docker-compose down -v

# 重新启动
docker-compose up -d
```

### 调试命令
```bash
# 查看特定容器日志
docker logs fullchain2_apache
docker logs fullchain2_spring  
docker logs fullchain2_redis

# 进入容器调试
docker exec -it fullchain2_apache /bin/bash
docker exec -it fullchain2_spring /bin/bash
docker exec -it fullchain2_redis /bin/bash

# 查看网络配置
docker network inspect fullchain2_frontend_network
docker network inspect fullchain2_dmz_network
docker network inspect fullchain2_internal_network
```

---

🎯 **这是一个真正的挑战！需要你运用安全研究技能和创造性思维来完成整个攻击链。** 