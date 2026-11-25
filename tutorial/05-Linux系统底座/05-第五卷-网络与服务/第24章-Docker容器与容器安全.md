# 第 24 章 Docker 容器与容器安全

## 本章目标

读完这一章，你将能够：

- 理解容器与虚拟机的本质区别
- 掌握 Docker 核心概念（镜像、容器、Dockerfile）
- 熟练使用 Docker 常用命令
- 编写 Dockerfile 构建自己的镜像
- 理解容器隔离机制与逃逸风险
- 掌握容器安全加固与镜像安全

---

## 24.1 容器 vs 虚拟机

### 24.1.1 本质区别

| 对比 | 虚拟机（VM） | 容器（Docker） |
|------|-------------|---------------|
| 隔离级别 | 硬件级（每个 VM 有完整 OS） | 进程级（共享宿主内核） |
| 启动速度 | 分钟级 | 秒级 |
| 体积 | GB 级 | MB 级 |
| 性能 | 有虚拟化开销 | 接近原生 |
| 隔离强度 | 强 | 较弱（共享内核） |

```
虚拟机：  [App][Guest OS][Hypervisor][Host OS][硬件]   ← 每个 VM 独立内核
容器：    [App][App][Docker Engine][Host OS][硬件]     ← 共享宿主内核
```

容器本质是**被隔离的进程**：用 namespace（第 17 章）隔离视图、cgroup 限制资源、联合文件系统分层存储。

### 24.1.2 为什么容器对 AI + 安全重要

- **AI**：PyTorch/TensorFlow 环境复杂，容器一键封装依赖；模型服务、向量数据库都用容器部署。
- **安全**：安全工具（扫描器、靶场）容器化后开箱即用；Kali、DVWA、Vulhub 都有 Docker 镜像。
- **云原生**：Kubernetes、Docker 是现代基础设施的标配，云原生安全是热门方向。

---

## 24.2 Docker 核心概念

| 概念 | 说明 |
|------|------|
| 镜像（Image） | 只读模板，包含程序 + 依赖 + 配置（类似"类"） |
| 容器（Container） | 镜像的运行实例（类似"对象"） |
| Dockerfile | 构建镜像的脚本 |
| Registry | 镜像仓库（Docker Hub、私有仓库） |
| Volume | 持久化存储（容器删除数据不丢） |

> **小白问**：镜像和容器的关系？
>
> 镜像是静态的模板（存在硬盘），容器是镜像跑起来的实例（在内存运行）。同一个镜像可以同时跑多个容器。就像"类"和"对象"。

---

## 24.3 Docker 安装与常用命令

### 24.3.1 安装

```bash
# Ubuntu 官方一键安装脚本（或用 apt 仓库）
curl -fsSL https://get.docker.com | sudo sh

# 把当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER
# 重新登录后生效

docker --version
```

### 24.3.2 镜像操作

```bash
docker pull nginx                # 拉取镜像
docker images                    # 列出本地镜像
docker rmi nginx                 # 删除镜像
docker search keyword            # 搜索镜像
```

### 24.3.3 容器操作

```bash
# 运行容器（-d 后台、-p 端口映射、--name 命名）
docker run -d -p 8080:80 --name mynginx nginx

docker ps                        # 查看运行中的容器
docker ps -a                     # 查看所有容器（含停止的）
docker stop mynginx              # 停止
docker start mynginx             # 启动
docker restart mynginx           # 重启
docker rm mynginx                # 删除（先停止）

docker exec -it mynginx bash     # 进入容器交互式 shell
docker logs mynginx              # 查看容器日志
docker cp file mynginx:/path/    # 复制文件到容器
```

`-it` 的含义：`-i` 保持 stdin 打开、`-t` 分配伪终端，组合起来才能交互。

> **小白问**：`-p 8080:80` 是什么？
>
> 端口映射：把宿主机的 8080 端口映射到容器的 80 端口。访问宿主机 `localhost:8080` 就能访问容器里的 Web 服务。

---

## 24.4 Dockerfile：构建自己的镜像

### 24.4.1 基本语法

```dockerfile
FROM ubuntu:22.04              # 基础镜像
LABEL maintainer="you@example.com"
RUN apt update && apt install -y python3   # 构建时执行命令
COPY app.py /app/              # 复制文件
WORKDIR /app                   # 设置工作目录
EXPOSE 8000                    # 声明端口（文档性质）
CMD ["python3", "app.py"]      # 容器启动时执行的命令
```

常用指令：

| 指令 | 作用 |
|------|------|
| FROM | 指定基础镜像 |
| RUN | 构建时执行命令 |
| COPY / ADD | 复制文件到镜像 |
| WORKDIR | 设置工作目录 |
| ENV | 设置环境变量 |
| EXPOSE | 声明端口 |
| CMD / ENTRYPOINT | 容器启动命令 |
| USER | 指定运行用户 |

### 24.4.2 构建与运行

```bash
docker build -t myapp:1.0 .
docker run -d -p 8000:8000 myapp:1.0
```

### 24.4.3 分层与优化

Docker 镜像是分层存储的，`RUN`、`COPY` 等指令会创建新的层。优化技巧：

```dockerfile
# 好的做法：合并 RUN 减少层数，清理缓存
RUN apt update && apt install -y python3 \
    && rm -rf /var/lib/apt/lists/*
```

```dockerfile
# 利用缓存：把不常变的内容放前面（如先 COPY requirements.txt）
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt
COPY . /app/
```

### 24.4.4 多阶段构建（减小镜像）

```dockerfile
# 构建阶段
FROM golang:1.20 AS builder
COPY . /src
RUN cd /src && go build -o app

# 运行阶段（只带编译好的二进制）
FROM alpine:latest
COPY --from=builder /src/app /app
CMD ["/app"]
```

这样最终镜像只有几 MB，不含编译工具链——**更小的镜像 = 更小的攻击面**。

---

## 24.5 容器安全

### 24.5.1 容器隔离机制（回顾第 17 章）

- **Namespace**：PID/NET/MNT/USER 等隔离视图
- **Cgroup**：限制 CPU/内存/IO 资源
- **Capability**：默认丢弃大部分 root 权力
- **Seccomp/AppArmor/SELinux**：限制系统调用

### 24.5.2 容器逃逸风险

容器共享宿主内核，如果内核有漏洞或配置不当，攻击者可能"逃逸"到宿主机：

| 风险 | 原因 | 防护 |
|------|------|------|
| 特权容器 | `--privileged` 给了几乎全部权限 | 绝不用 privileged（除非必要） |
| 敏感挂载 | 挂载了宿主机 `/`、`/var/run/docker.sock` | 避免挂载敏感路径 |
| 内核漏洞 | 共享内核，内核漏洞可逃逸 | 及时更新内核 |
| root 运行 | 容器内 root 可能对应宿主 root | 用非 root 用户 |
| Docker socket | 拿到 socket 等于控制宿主机 Docker | 严格保护 socket |

### 24.5.3 容器安全加固清单

```bash
# 1. 以非 root 用户运行
docker run -u 1000:1000 myapp

# 2. 只读根文件系统
docker run --read-only myapp

# 3. 丢弃所有 capability，只加必需的
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myapp

# 4. 限制资源
docker run --memory=512m --cpus=1 myapp

# 5. 不挂载敏感路径
# 避免 -v /:/host、-v /var/run/docker.sock:/var/run/docker.sock

# 6. 设置安全选项
docker run --security-opt no-new-privileges myapp
```

### 24.5.4 镜像安全

| 风险 | 防护 |
|------|------|
| 恶意镜像 | 只用可信来源的官方镜像；扫镜像漏洞 |
| 镜像含漏洞 | 用 Trivy、Clair 扫描镜像漏洞 |
| 镜像过大 | 用 Alpine 基础镜像、多阶段构建 |
| 硬编码密钥 | 不把密钥写进镜像，用环境变量/secrets |

镜像漏洞扫描：

```bash
# 安装 Trivy
sudo apt install trivy
trivy image nginx:latest
```

### 24.5.5 Docker 守护进程安全

Docker daemon 以 root 运行，控制它等于控制宿主机：

```bash
# 不要暴露 Docker API 到网络（2375 端口是明文，极其危险）
# 检查是否暴露
ss -tuln | grep 2375
```

> ⚠️ 开放的 Docker API（2375）是常见的入侵入口——攻击者连上后能直接创建特权容器、挂载宿主机根目录，完全接管服务器。**绝不要对公网开放 Docker API**。

---

## 24.6 实战：容器化一个安全工具

容器化一个简易的日志分析工具：

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY log_analyzer.py .
RUN adduser -D analyzer
USER analyzer
CMD ["python", "log_analyzer.py"]
```

这个 Dockerfile 体现了：

- 用轻量 Alpine 基础镜像
- 创建非 root 用户运行
- 只复制必需文件
- 攻击面最小化

构建并运行：

```bash
docker build -t log-analyzer:1.0 .
docker run --rm -v /var/log:/logs:ro log-analyzer:1.0
```

`-v /var/log:/logs:ro` 把日志目录挂载进来，`:ro` 表示只读（容器无法篡改日志）。

---

## 24.7 本章总结

| 知识点 | 内容 |
|--------|------|
| 容器 vs VM | 容器进程级隔离、共享内核、轻量快速；VM 硬件级隔离 |
| 核心概念 | 镜像、容器、Dockerfile、Registry、Volume |
| 常用命令 | pull/images/run/ps/stop/rm/exec/logs/cp |
| Dockerfile | FROM/RUN/COPY/WORKDIR/CMD；分层、缓存、多阶段构建 |
| 隔离机制 | namespace、cgroup、capability、seccomp |
| 逃逸风险 | privileged、敏感挂载、内核漏洞、Docker socket |
| 加固 | 非 root、只读根、丢弃 capability、限资源、扫镜像 |
| 镜像安全 | 可信来源、Trivy 扫描、不硬编码密钥 |

---

## 本章练习

1. 安装 Docker，运行 `docker run hello-world` 验证。
2. 拉取 nginx 镜像，用 `docker run -d -p 8080:80` 启动，浏览器访问验证。
3. 用 `docker exec -it` 进入容器，看看里面的系统环境。
4. 用 `docker logs` 查看容器日志。
5. 写一个 Dockerfile，构建一个运行你自己的 Python 脚本的镜像。
6. 用多阶段构建优化一个镜像，对比体积变化。
7. 用 `docker run --read-only --cap-drop=ALL` 运行一个容器，理解加固参数。
8. 思考：容器为什么"不是虚拟机"？容器逃逸的原理是什么？为什么不能开放 Docker API？

---

**下一章预告**：我们将学习 systemd 与服务管理——理解 Linux 如何启动、管理服务，这是运维和安全的必备技能，也是本卷的收官。
