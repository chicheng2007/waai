# 第 17 章 Linux 安全模型

## 本章目标

读完这一章，你将能够：

- 系统理解 Linux 的安全模型：用户/权限、capability、命名空间、SELinux/AppArmor
- 理解 DAC 与 MAC 的区别
- 掌握 capability 的查看与管理
- 理解容器隔离的底层基础（namespace + cgroup）
- 理解纵深防御（Defense in Depth）思想

---

## 17.1 Linux 安全模型总览

Linux 的安全不是单一机制，而是**多层防线**叠加：

```
┌─────────────────────────────────────┐
│  应用层：用户认证、sudo、密码策略      │  第 8、18、19 章
├─────────────────────────────────────┤
│  文件层：DAC 权限（rwx、SUID）        │  第 8 章
├─────────────────────────────────────┤
│  内核层：Capability、Namespace        │  本章
├─────────────────────────────────────┤
│  强制访问：SELinux / AppArmor          │  本章
├─────────────────────────────────────┤
│  网络层：防火墙、TCP Wrappers          │  第 18 章
├─────────────────────────────────────┤
│  监控层：日志、审计、入侵检测          │  第 20 章
└─────────────────────────────────────┘
```

任何一层都不是银弹，**纵深防御**的思想是：一层被突破，还有下一层兜底。

---

## 17.2 DAC：自主访问控制

### 17.2.1 什么是 DAC

DAC（Discretionary Access Control，自主访问控制）是我们第 8 章学的传统权限模型：文件的**所有者**决定谁能访问。它的"自主"体现在：所有者可以自主地把权限授予别人（chmod、chown）。

DAC 的核心：

- 身份：用户（UID）和组（GID）
- 权限：读/写/执行（rwx）
- 特殊位：SUID/SGID/Sticky

### 17.2.2 DAC 的局限

DAC 有个根本弱点：**root 拥有所有权限**。一旦攻击者拿到 root（提权成功），DAC 就形同虚设——他想读什么读什么，想改什么改什么。

此外，DAC 无法表达更细的策略，比如"nginx 进程只能读 /var/www，即使它被攻破"。这就引出了 MAC。

---

## 17.3 MAC：强制访问控制

### 17.3.1 什么是 MAC

MAC（Mandatory Access Control，强制访问控制）不由文件所有者决定，而是由**系统管理员制定的全局策略**决定。即使是 root，也要遵守策略。

Linux 上的两大 MAC 实现：

- **SELinux**：Red Hat 系（RHEL/CentOS/Fedora）默认，策略强大但复杂
- **AppArmor**：Ubuntu/Debian 默认，配置相对简单

### 17.3.2 SELinux 基础

SELinux 给每个进程和文件打上"安全上下文（context）"，策略规定"什么类型的进程能访问什么类型的文件"。

查看上下文：

```bash
ls -Z file.txt
ps -eZ | head
```

SELinux 有三种模式：

```bash
getenforce                 # 查看当前模式
# Enforcing（强制）：违反策略的行为被阻止
# Permissive（宽容）：只记录不阻止（用于调试）
# Disabled（禁用）：完全关闭
```

切换模式（临时）：

```bash
sudo setenforce 0          # 切到 Permissive
sudo setenforce 1          # 切回 Enforcing
```

配置文件 `/etc/selinux/config` 控制开机模式。

> **运维现实**：SELinux 很强大，但很多管理员因为不熟悉而直接禁用它——这相当于拆掉一层重要防线。正确做法是学习它、用 `audit2allow` 分析日志、编写策略，而不是一关了之。生产环境强烈建议保持 Enforcing。

### 17.3.3 AppArmor 基础

AppArmor 用"配置文件（profile）"限制程序的权限，基于路径，比 SELinux 直观。

```bash
sudo aa-status              # 查看 AppArmor 状态和已加载的 profile
sudo apparmor_status        # 同上（老命令）
```

Ubuntu 上很多服务（如 nginx、mysql）自带 AppArmor profile，默认处于 enforce 或 complain 模式。

---

## 17.4 Capability：拆分 root 权力

### 17.4.1 为什么要拆分

传统上，某些操作只有 root 能做。但"能绑定 80 端口"和"能删除整个系统"是完全不同的权力，凭什么要一起给？

**Capability（能力）** 把 root 的权力拆成 30 多个细粒度单元，进程可以只拥有需要的那部分。

常见 capability：

| Capability | 允许的 operation |
|-----------|-----------------|
| `CAP_NET_BIND_SERVICE` | 绑定 1024 以下的端口 |
| `CAP_NET_RAW` | 使用 raw socket（ping、抓包） |
| `CAP_CHOWN` | 改变文件所有者 |
| `CAP_DAC_OVERRIDE` | 绕过文件读写权限检查 |
| `CAP_SYS_ADMIN` | 大量管理操作（几乎等同 root） |
| `CAP_SYS_PTRACE` | ptrace 其他进程（调试/注入） |

### 17.4.2 查看 capability

```bash
# 查看某个文件的 capability
getcap /usr/bin/ping

# 查看某个进程的 capability
sudo getpcaps PID

# 查看当前 shell 的 capability
capsh --print
```

输出示例：

```bash
/usr/bin/ping cap_net_raw=ep
```

`ping` 只需要 `CAP_NET_RAW` 就能发原始 ICMP 包，不需要完整 root。所以系统给它设置 capability 而不是 SUID root——这比 SUID 更安全。

### 17.4.3 capability 的安全意义

- **最小权限**：进程只拿到必需的权力，被攻破后危害有限。
- **减少 SUID**：用 capability 替代 SUID root 程序，缩小攻击面。
- **容器基础**：Docker 默认会丢弃大部分 capability，只保留少量，这就是容器隔离的一部分。

> **安全提示**：`CAP_SYS_ADMIN` 几乎等同 root，攻击者拿到它就是提权成功。审计时留意哪些进程/文件拥有这个 capability。

---

## 17.5 Namespace 与 Cgroup：容器隔离的基石

### 17.5.1 Namespace（命名空间）

Namespace 让一组进程看到"隔离的"系统视图。Linux 有多种 namespace：

| Namespace | 隔离的内容 |
|-----------|-----------|
| PID | 进程编号空间（容器内 PID 1 不是宿主机 PID 1） |
| NET | 网络栈（IP、端口、路由） |
| MNT | 文件系统挂载点 |
| UTS | 主机名 |
| IPC | 进程间通信 |
| USER | 用户/组 ID 映射 |

Docker 就是这些 namespace 的组合——容器里的进程"以为"自己在一台独立的机器上。

查看进程的 namespace：

```bash
ls -l /proc/PID/ns/
```

### 17.5.2 Cgroup（控制组）

Cgroup（control group）负责**资源限制**：CPU、内存、磁盘 I/O、网络带宽。它防止一个进程/容器吃光所有资源（DoS）。

```bash
# 查看 cgroup
cat /proc/cgroups
systemd-cgtop        # 实时查看 cgroup 资源使用
```

> **小白问**：namespace 和 cgroup 有什么区别？
>
> namespace 管"隔离"（你看到什么），cgroup 管"限额"（你能用多少）。容器 = namespace（隔离视图）+ cgroup（限制资源）+ 其他技术。第 24 章讲 Docker 时会再深入。

### 17.5.3 容器安全的隐患

容器不是虚拟机，隔离是"进程级"的，共享同一个内核。如果内核有漏洞，攻击者可能"容器逃逸"到宿主机。常见加固：

- 不以 root 运行容器
- 丢弃不必要的 capability
- 只读根文件系统
- 限制资源（cgroup）
- 及时更新内核和容器运行时

---

## 17.6 纵深防御实战：构建一个多层防线

把本章知识串起来，为一台服务器设计纵深防御：

| 层次 | 措施 | 对应技术 |
|------|------|---------|
| 身份层 | 禁用 root 登录、强密码、sudo 审计 | 第 8、19 章 |
| 文件层 | 最小权限、审计 SUID、关键文件只读 | DAC（第 8 章） |
| 内核层 | 精简 capability、启用 namespace 隔离 | Capability/Namespace |
| 强制层 | 启用 SELinux/AppArmor | MAC |
| 网络层 | 防火墙只开必要端口 | 第 18 章 |
| 应用层 | 服务以非特权用户运行 | 用户隔离 |
| 监控层 | 日志集中、入侵检测、定期审计 | 第 20 章 |
| 更新层 | 及时打补丁 | 第 10 章 |

**没有一个措施能单独保证安全，但叠加起来，攻击成本会高到让大多数攻击者放弃。** 这就是纵深防御的精髓。

---

## 17.7 常见报错与解决

| 现象 | 原因 | 解决 |
|------|------|------|
| 服务被 SELinux 阻止 | 策略不允许 | 查 `/var/log/audit/audit.log`，用 `audit2allow` 生成策略 |
| `Operation not permitted` 即使 root | MAC 或 capability 限制 | 检查 getenforce、getcap |
| 容器能访问宿主机文件 | 挂载配置不当 | 检查 volume 挂载、privileged 设置 |

---

## 17.8 本章总结

| 知识点 | 内容 |
|--------|------|
| 纵深防御 | 多层防线叠加，一层被破还有下一层 |
| DAC | 传统 rwx 权限，所有者自主授权；弱点是 root 万能 |
| MAC | SELinux/AppArmor，全局策略强制，连 root 也受限 |
| SELinux | 安全上下文 + 策略；Enforcing/Permissive/Disabled |
| AppArmor | 基于路径的 profile，Ubuntu 默认，较直观 |
| Capability | 拆分 root 权力；最小权限；替代 SUID |
| Namespace | 隔离视图（PID/NET/MNT 等），容器基础 |
| Cgroup | 资源限额（CPU/内存/IO），防资源耗尽 |

---

## 本章练习

1. 用 `getenforce` 查看你的系统 SELinux 状态（Ubuntu 可能没有 SELinux，用 `aa-status` 看 AppArmor）。
2. 用 `getcap /usr/bin/ping` 查看 ping 的 capability。
3. 用 `capsh --print` 查看当前 shell 拥有的 capability。
4. 用 `ls -Z` 查看几个文件的安全上下文（在启用了 SELinux 的系统上）。
5. 用 `ls -l /proc/self/ns/` 查看当前进程的 namespace。
6. 思考：DAC 的根本弱点是什么？MAC 如何弥补？
7. 思考：为什么容器"不是虚拟机"？从 namespace 和 cgroup 的角度解释。
8. 结合本章，列出你认为一台 Web 服务器应该有的 5 层防线。

---

**下一章预告**：我们将学习防火墙——iptables、nftables 和 firewalld。这是网络层的第一道防线，决定"谁能连进来、谁不能"。
