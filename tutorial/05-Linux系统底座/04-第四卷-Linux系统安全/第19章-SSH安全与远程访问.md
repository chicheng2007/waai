# 第 19 章 SSH 安全与远程访问

## 本章目标

读完这一章，你将能够：

- 理解 SSH 的工作原理（加密、认证、客户端/服务端）
- 掌握 SSH 密钥登录的配置（比密码更安全）
- 加固 SSH 服务（改端口、禁 root、禁密码、限用户）
- 使用 sshd 配置与 fail2ban 防御暴力破解
- 掌握 SSH 端口转发、scp/sftp、ssh 配置别名
- 理解 SSH 安全审计

---

## 19.1 SSH 基础

### 19.1.1 什么是 SSH

SSH（Secure Shell）是加密的远程登录协议。它取代了不加密的 telnet，让你能安全地远程控制服务器。

- **服务端**：sshd（守护进程），监听 22 端口
- **客户端**：ssh 命令

基本用法：

```bash
ssh 用户名@主机           # 登录远程主机
ssh -p 2222 用户@主机     # 指定端口
ssh 用户@主机 "命令"      # 执行单条命令后返回
```

示例：

```bash
ssh root@192.168.1.10
```

### 19.1.2 SSH 的加密

SSH 用非对称加密建立安全通道：

1. 客户端连接服务端，服务端发送公钥指纹
2. 双方协商会话密钥（用于加密后续通信）
3. 客户端认证身份（密码或密钥）
4. 建立加密通道，所有通信加密

**首次连接**会看到主机密钥确认提示：

```bash
The authenticity of host '192.168.1.10' can't be established.
ED25519 key fingerprint is SHA256:xxxxx.
Are you sure you want to continue connecting (yes/no)?
```

这是在问你"信任这台服务器吗？"。确认指纹正确后输入 yes，主机会被记录到 `~/.ssh/known_hosts`。

> **安全提示（中间人攻击）**：如果某天连接同一台服务器时突然提示"主机密钥已改变（REMOTE HOST IDENTIFICATION HAS CHANGED）"，要高度警惕——可能是服务器重装了，也可能是有人在做中间人攻击。不要盲目删除记录，先核实。

### 19.1.3 服务端配置文件

`/etc/ssh/sshd_config` 是 SSH 服务端配置（注意别和客户端配置 `~/.ssh/config` 搞混）。

查看当前有效配置：

```bash
sudo sshd -T | grep -E "port|permitrootlogin|passwordauthentication"
```

---

## 19.2 密钥登录：告别密码

### 19.2.1 为什么用密钥

密码容易被暴力破解、被猜测、被钓鱼。密钥登录用非对称加密：

- **私钥**：保存在你的电脑，绝不外泄（像密码但更长）
- **公钥**：放到服务器的 `~/.ssh/authorized_keys`

登录时，服务器用公钥验证你持有私钥。私钥（通常 2048/4096 位）几乎无法暴力破解。

### 19.2.2 生成密钥对

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

或传统 RSA：

```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

按提示选择保存位置（默认 `~/.ssh/id_ed25519`）和口令（passphrase，建议设置，给私钥再加一层保护）。

生成后：

```bash
~/.ssh/id_ed25519       # 私钥（绝密，权限 600）
~/.ssh/id_ed25519.pub   # 公钥（可以公开）
```

> **小白问**：ed25519 和 rsa 选哪个？
>
> ed25519 更现代、更快、密钥更短且安全性高，推荐首选。只有兼容非常老的系统时才用 rsa。

### 19.2.3 部署公钥到服务器

```bash
# 方法一：ssh-copy-id（最简单）
ssh-copy-id user@server

# 方法二：手动追加
cat ~/.ssh/id_ed25519.pub | ssh user@server 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'
```

部署后测试：

```bash
ssh user@server
```

如果设置了密钥口令，会提示输入口令（不是服务器密码）。配置成功后可以进一步禁用密码登录。

### 19.2.4 权限要求

SSH 对权限非常严格，权限不对会导致密钥登录失败：

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/id_ed25519
```

> **常见坑**：`authorized_keys` 权限如果是 644（组/其他人可读），sshd 会拒绝使用它——因为这可能被其他用户读取篡改。这是 SSH 的安全设计。

### 19.2.5 ssh-agent：管理密钥口令

每次输入密钥口令很烦，用 ssh-agent 缓存：

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

输入一次口令后，本次会话内不用再输。

---

## 19.3 加固 SSH 服务

### 19.3.1 关键配置项

编辑 `/etc/ssh/sshd_config`：

```bash
sudo nano /etc/ssh/sshd_config
```

推荐的安全配置：

```bash
Port 2222                        # 1. 改默认端口（减少自动化扫描）
PermitRootLogin no               # 2. 禁止 root 直接登录（重要！）
PasswordAuthentication no        # 3. 禁用密码登录（用密钥，防暴力破解）
PubkeyAuthentication yes         # 4. 启用密钥认证
PermitEmptyPasswords no          # 5. 禁止空密码
MaxAuthTries 3                   # 6. 最多 3 次认证尝试
LoginGraceTime 30                # 7. 登录超时 30 秒
AllowUsers alice bob             # 8. 只允许特定用户登录（白名单）
X11Forwarding no                 # 9. 禁用 X11 转发（不需要的话）
ClientAliveInterval 300          # 10. 300 秒无响应断开
ClientAliveCountMax 2
```

修改后检查语法并重启：

```bash
sudo sshd -t                     # 检查配置语法
sudo systemctl restart sshd      # 重启服务
```

> ⚠️ **至关重要的操作流程**：修改 SSH 配置时，**务必保留一个已登录的会话不要断开**，用另一个终端测试新配置能否登录，确认成功后再关闭旧会话。否则一个错误配置就会把你永久锁在服务器外面（尤其是云服务器，只能重装）。
>
> 建议顺序：先配置密钥登录并验证 → 再禁用密码登录 → 最后改端口。每步都验证。

### 19.3.2 fail2ban：自动封禁暴力破解

fail2ban 监控日志，发现多次失败登录就自动用防火墙封禁 IP。

```bash
sudo apt install fail2ban
sudo systemctl enable --now fail2ban

sudo fail2ban-client status        # 查看状态
sudo fail2ban-client status sshd   # 查看 sshd  jail 状态
```

配置 `/etc/fail2ban/jail.local`：

```ini
[sshd]
enabled = true
port = ssh
maxretry = 3          # 失败 3 次
bantime = 3600        # 封禁 1 小时（秒）
findtime = 600        # 在 10 分钟内
```

重启生效：

```bash
sudo systemctl restart fail2ban
```

查看被封禁的 IP：

```bash
sudo fail2ban-client status sshd
sudo iptables -L -n | grep f2b
```

手动解封：

```bash
sudo fail2ban-client set sshd unbanip 1.2.3.4
```

---

## 19.4 SSH 实用技巧

### 19.4.1 配置文件别名

在 `~/.ssh/config` 里配置常用主机：

```bash
Host myserver
    HostName 192.168.1.10
    User alice
    Port 2222
    IdentityFile ~/.ssh/id_ed25519
```

之后只需：

```bash
ssh myserver
```

### 19.4.2 文件传输

```bash
# scp：复制文件
scp file.txt user@server:/path/          # 上传
scp user@server:/path/file.txt ./        # 下载
scp -r dir/ user@server:/path/           # 递归目录

# sftp：交互式文件管理
sftp user@server
```

### 19.4.3 端口转发

```bash
# 本地转发：把本地 8080 转发到远程的 80（访问远程内网服务）
ssh -L 8080:localhost:80 user@server

# 远程转发：把远程 8080 转发到本地的服务
ssh -R 8080:localhost:80 user@server

# 动态转发：SOCKS 代理
ssh -D 1080 user@server
```

> **安全场景**：端口转发在渗透测试和运维中都很常用，但它能绕过网络边界。企业环境应对 SSH 转发加以限制（如 `AllowTcpForwarding no`）。

### 19.4.4 保持连接不断线

在 `~/.ssh/config` 加：

```bash
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

让客户端定期发心跳包，防止 NAT/防火墙断开空闲连接。配合第 9 章的 tmux，远程工作更稳定。

---

## 19.5 SSH 安全审计

```bash
# 1. 查看配置是否安全
sudo sshd -T | grep -E "permitrootlogin|passwordauthentication|port|permitemptypasswords"

# 2. 查看登录历史
last                          # 所有登录历史
last -n 20                    # 最近 20 条

# 3. 查看失败的登录尝试
sudo grep "Failed password" /var/log/auth.log | tail -20

# 4. 统计攻击来源 IP
sudo grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn | head

# 5. 查看当前登录用户
who
w
```

> **应急响应场景**：发现 SSH 被暴力破解时：
> 1. 用上面的命令统计攻击 IP 和频率
> 2. 立即用 fail2ban 或 iptables 封禁
> 3. 检查有没有成功的登录（`grep "Accepted"`）
> 4. 如果有可疑成功登录，检查该会话做了什么（history、日志）
> 5. 加固配置（改端口、禁密码、禁 root）
> 6. 必要时更换所有密码/密钥

---

## 19.6 常见报错与解决

| 现象 | 原因 | 解决 |
|------|------|------|
| `Permission denied (publickey)` | 密钥没配好 / 权限错 | 检查 authorized_keys 权限、公钥内容 |
| `Connection refused` | 服务没开 / 端口错 / 防火墙 | 检查 sshd 状态、端口、防火墙 |
| `Host key verification failed` | 主机密钥变更 | 核实后删除 `~/.ssh/known_hosts` 中对应记录 |
| 改配置后连不上 | 配置错误把自己锁外面 | 用保留的会话修复；云服务器用控制台 VNC |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | 可能中间人攻击 | 核实服务器身份，不要盲目忽略 |

---

## 19.7 本章总结

| 知识点 | 内容 |
|--------|------|
| SSH | 加密远程登录；服务端 sshd，客户端 ssh；默认 22 端口 |
| 密钥登录 | 私钥保密、公钥上服务器；`ssh-keygen`、`ssh-copy-id` |
| 权限 | `.ssh` 700、`authorized_keys` 600，否则密钥失效 |
| 加固 | 改端口、禁 root 登录、禁密码、限用户、MaxAuthTries |
| 关键流程 | 先配密钥验证，再禁密码；保留会话防锁死 |
| fail2ban | 监控日志自动封禁暴力破解 IP |
| 实用 | `~/.ssh/config` 别名、scp/sftp、端口转发、心跳保活 |
| 审计 | `last`、`w`、分析 auth.log，应急响应六步 |

---

## 本章练习

1. 生成一对 ed25519 密钥，查看公私钥文件内容（私钥不要外泄）。
2. （在两台实验机/虚拟机之间）配置密钥登录并验证。
3. 检查 `~/.ssh` 和 `authorized_keys` 的权限是否符合要求。
4. 查看你系统 `/etc/ssh/sshd_config` 的当前配置，找出可以加固的点。
5. 安装 fail2ban，查看 sshd jail 状态。
6. 用 `last` 和 `grep "Failed password" /var/log/auth.log` 查看登录情况。
7. 在 `~/.ssh/config` 里配置一个主机别名并测试。
8. 思考：为什么"先配置密钥登录并验证，再禁用密码登录"这个顺序如此重要？

---

**下一章预告**：我们将学习日志分析与入侵检测——日志是安全事件的"黑匣子"，掌握它，你就能发现攻击痕迹、还原攻击过程、构建检测规则。
