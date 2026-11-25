# 第 25 章 systemd 与服务管理

## 本章目标

读完这一章，你将能够：

- 理解 systemd 的作用与系统启动流程
- 掌握 systemctl 管理服务（启动、停止、自启、状态）
- 理解 unit 文件的结构与编写
- 掌握 journalctl 查看服务日志
- 理解 target、定时器（呼应第 15 章）
- 用 systemd 加固服务安全

---

## 25.1 systemd 简介

### 25.1.1 什么是 systemd

systemd 是现代 Linux 的初始化系统（init system）和服务管理器，是系统启动后运行的第一个进程（PID 1）。它负责：

- 启动系统服务
- 管理服务的生命周期
- 处理依赖关系
- 提供日志（journald）
- 定时任务（timer）、日志轮转等

它取代了传统的 SysV init 和 upstart，是 Ubuntu 16.04+、CentOS 7+ 的标准。

### 25.1.2 系统启动流程（简化）

```
BIOS/UEFI → 引导程序(GRUB) → 内核 → systemd(PID 1) → 挂载文件系统、启动服务 → 登录界面
```

systemd 并行启动服务（比传统串行快），并根据依赖关系决定启动顺序。

### 25.1.3 unit 概念

systemd 管理的对象叫 **unit**，有多种类型：

| 类型 | 扩展名 | 作用 |
|------|--------|------|
| Service | `.service` | 服务/守护进程 |
| Target | `.target` | 一组 unit 的集合（类似运行级别） |
| Timer | `.timer` | 定时任务 |
| Socket | `.socket` | 套接字激活 |
| Mount | `.mount` | 挂载点 |

---

## 25.2 systemctl：管理服务

### 25.2.1 基本操作

```bash
sudo systemctl start 服务名         # 启动
sudo systemctl stop 服务名          # 停止
sudo systemctl restart 服务名       # 重启
sudo systemctl reload 服务名        # 平滑重载配置（不中断服务）
sudo systemctl status 服务名        # 查看状态
sudo systemctl enable 服务名        # 开机自启
sudo systemctl disable 服务名       # 取消自启
sudo systemctl mask 服务名          # 彻底禁用（无法启动）
sudo systemctl unmask 服务名        # 解除禁用
```

示例：

```bash
sudo systemctl status nginx
sudo systemctl restart sshd
```

### 25.2.2 查看服务

```bash
systemctl list-units --type=service --state=running    # 运行中的服务
systemctl list-unit-files --type=service               # 所有服务及自启状态
systemctl list-unit-files --state=enabled              # 开机自启的服务
systemctl is-active nginx                              # 是否运行中
systemctl is-enabled nginx                             # 是否开机自启
```

### 25.2.3 Target（运行级别）

```bash
systemctl get-default                 # 查看默认 target
sudo systemctl set-default multi-user.target   # 设为命令行模式
sudo systemctl set-default graphical.target    # 设为图形模式

systemctl isolate multi-user.target   # 切到命令行（不重启）
```

常见 target：

| Target | 含义 |
|--------|------|
| `graphical.target` | 图形界面（多用户） |
| `multi-user.target` | 命令行多用户（服务器常用） |
| `rescue.target` | 救援模式 |
| `emergency.target` | 紧急模式 |

> **安全提示**：服务器通常用 `multi-user.target`（无图形界面），减少攻击面和资源占用。

---

## 25.3 unit 文件结构

### 25.3.1 一个 service 示例

`/etc/systemd/system/myapp.service`：

```ini
[Unit]
Description=My Security Tool
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=analyzer
Group=analyzer
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/python3 /opt/myapp/app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

三个区块：

| 区块 | 作用 |
|------|------|
| `[Unit]` | 描述、依赖关系 |
| `[Service]` | 服务如何运行 |
| `[Install]` | 开机自启的安装信息 |

### 25.3.2 关键字段

`[Unit]`：

- `Description`：描述
- `After`：在哪个 unit 之后启动（顺序）
- `Wants` / `Requires`：依赖（弱/强）

`[Service]`：

- `Type=simple`：前台运行（最常用）；`forking`：后台守护进程
- `User` / `Group`：以什么用户运行（安全关键）
- `ExecStart`：启动命令（必须绝对路径）
- `Restart`：重启策略（`no`、`on-failure`、`always`）
- `WorkingDirectory`：工作目录

`[Install]`：

- `WantedBy=multi-user.target`：在命令行模式下自启

### 25.3.3 创建并启用服务

```bash
sudo systemctl daemon-reload         # 重新加载配置（新增/修改 unit 后必须）
sudo systemctl start myapp
sudo systemctl enable myapp
sudo systemctl status myapp
```

> **常见坑**：修改了 unit 文件后忘记 `daemon-reload`，改动不生效。记住：改 unit → `daemon-reload` → `restart`。

---

## 25.4 服务日志：journalctl

```bash
journalctl -u myapp                  # 查看某服务的日志
journalctl -u myapp -f               # 实时跟踪
journalctl -u myapp --since today    # 今天的
journalctl -u myapp -p err           # 只看错误
journalctl --disk-usage              # 日志占用空间
sudo journalctl --vacuum-time=7d     # 清理 7 天前的日志
```

journald 的配置在 `/etc/systemd/journald.conf`，可限制日志大小（防止撑爆磁盘）：

```ini
SystemMaxUse=500M
```

---

## 25.5 systemd 安全加固

在 unit 文件的 `[Service]` 段加入安全选项，收紧服务权限：

```ini
[Service]
# 以非 root 运行
User=analyzer
Group=analyzer

# 只读根文件系统
ReadOnlyPaths=/
ReadWritePaths=/var/log/myapp

# 禁止获得新权限
NoNewPrivileges=true

# 私有 /tmp（服务有独立的临时目录）
PrivateTmp=true

# 限制 capability，只保留必需的
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

# 限制系统调用（seccomp）
SystemCallArchitectures=native
RestrictFcheck=false

# 禁止访问网络（如果不需要）
# PrivateNetwork=true

# 保护系统目录
ProtectSystem=strict
ProtectHome=true
```

这些选项能大幅降低"服务被攻破后的危害"。这是容器隔离思路在 systemd 服务上的应用。

> **小白问**：这些安全选项会影响服务吗？
>
> 可能会。比如 `ReadOnlyPaths=/` 后服务不能写任何文件，需要用 `ReadWritePaths` 显式开放需要的目录。配置后必须测试服务是否正常。**先在实验环境验证，再上生产**。

---

## 25.6 systemd timer（回顾）

第 15 章讲过 systemd timer 替代 cron。它其实是一种 unit：

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Daily backup

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now backup.timer
systemctl list-timers
```

---

## 25.7 常见报错与解决

| 现象 | 原因 | 解决 |
|------|------|------|
| `Unit not found` | 服务名错/unit 不存在 | `systemctl list-unit-files` 查名字 |
| 改了 unit 不生效 | 没 daemon-reload | `sudo systemctl daemon-reload` |
| 服务启动失败 | ExecStart 路径错/权限问题 | `journalctl -u 服务名` 看日志 |
| 服务反复重启 | Restart=always + 程序崩溃 | 查程序本身的问题 |
| 安全选项导致服务异常 | 限制太严格 | 逐步放开，测试验证 |

---

## 25.8 本章总结

| 知识点 | 内容 |
|--------|------|
| systemd | PID 1，初始化系统与服务管理器；unit 概念 |
| systemctl | start/stop/restart/reload/status/enable/disable/mask |
| unit 类型 | service、target、timer、socket、mount |
| unit 文件 | [Unit]/[Service]/[Install] 三段；ExecStart 绝对路径 |
| target | graphical/multi-user/rescue/emergency；服务器用 multi-user |
| journalctl | `-u` 服务、`-f` 跟踪、`--since`、`--disk-usage` |
| 安全加固 | 非 root、只读根、NoNewPrivileges、PrivateTmp、capability 限制 |
| 记住 | 改 unit 后必须 `daemon-reload` |

---

## 本章练习

1. 用 `systemctl status ssh` 查看 SSH 服务状态。
2. 用 `systemctl list-units --type=service --state=running` 查看运行中的服务。
3. 用 `systemctl get-default` 查看默认 target。
4. 写一个简单的 service unit，运行你的一个脚本，用 systemctl 管理它。
5. 修改 unit 后，体会 `daemon-reload` 的作用（改前改后对比）。
6. 用 `journalctl -u 服务名 -f` 实时查看服务日志。
7. 给服务的 unit 加上 `NoNewPrivileges=true` 和 `PrivateTmp=true` 等安全选项，测试是否正常。
8. 思考：systemd 的安全选项和容器隔离（第 24 章）有什么相似之处？

---

## 第五卷总结

| 章 | 核心内容 |
|----|---------|
| 22 | TCP/IP 模型、IP/子网/网关/DNS、网络诊断工具、端口与服务 |
| 23 | Web（Nginx）搭建加固、HTTPS、DNS 原理与安全、DHCP 安全 |
| 24 | 容器 vs VM、Docker 核心概念、Dockerfile、容器逃逸与加固 |
| 25 | systemd、systemctl、unit 文件、journalctl、服务安全加固 |

> 第五卷让你理解"服务是怎么跑起来、怎么被隔离、怎么被保护的"——这是从单机命令到网络服务、从使用者到运维者的跨越。

---

**下一章预告**：第五卷结束，进入第六卷——Linux 与编程 AI。我们将学习开发环境、多语言支持（呼应前四套教程）、性能调优、GPU/CUDA 训练环境、安全工具链，把 Linux 变成开发与安全的主场。
