# 第二十九章 TLS 解密实战

HTTPS 流量是加密的，Wireshark 默认只能看到握手过程和加密后的密文。但在合法授权的场景下（如调试自己的应用、分析自己的流量），我们可以通过密钥解密 TLS，看到明文 HTTP 内容。本章介绍两种主流的解密方法。

> **重要声明**：TLS 解密技术仅可用于你有合法权限的流量（自己的设备、自己的应用、授权测试环境）。未经授权解密他人通信是违法行为。

## 29.1 解密的前提

TLS 解密的核心是获取**会话密钥**（对称密钥）。有两种途径：

1. **RSA 私钥解密**：用服务器的 RSA 私钥推导出会话密钥。
2. **SSLKEYLOGFILE**：让客户端/浏览器导出每次会话的密钥。

### 29.1.1 RSA 私钥解密的局限

RSA 私钥解密只适用于 **RSA 密钥交换**（密钥交换用 RSA）。现代 TLS 普遍使用 **ECDHE**（提供前向保密），即使有服务器私钥也无法解密过去的会话。因此 RSA 方法适用范围越来越窄，仅适用于：

- 旧系统使用 RSA 密钥交换的 TLS 1.2。
- 自己控制的、配置为 RSA 密钥交换的服务器。

### 29.1.2 SSLKEYLOGFILE（推荐）

SSLKEYLOGFILE 是目前最通用的方法。原理：支持的应用（Chrome、Firefox、curl、Python requests 等）在建立 TLS 连接时，会把会话密钥写入一个日志文件。Wireshark 读取该文件，就能解密对应的流量。

**优点**：适用于 ECDHE（前向保密）、TLS 1.3，覆盖绝大多数现代应用。

## 29.2 方法一：SSLKEYLOGFILE 解密

### 29.2.1 步骤一：设置环境变量

在启动浏览器/应用之前，设置环境变量 `SSLKEYLOGFILE` 指向一个文件：

**Linux / macOS**：

```bash
export SSLKEYLOGFILE=/path/to/sslkey.log
google-chrome
```

**Windows（PowerShell）**：

```powershell
$env:SSLKEYLOGFILE="C:\path\to\sslkey.log"
start chrome
```

**Windows（CMD）**：

```cmd
set SSLKEYLOGFILE=C:\path\to\sslkey.log
start chrome
```

### 29.2.2 步骤二：确认密钥被写入

应用运行并访问 HTTPS 网站后，检查日志文件是否有内容。典型的日志行：

```
CLIENT_RANDOM 4f3a2b... 8e7d6c...
```

每行包含 Client Random 和对应的 Master Secret。

> **注意**：并非所有应用都支持 SSLKEYLOGFILE。Chrome、Firefox、curl（部分版本）、基于 NSS/OpenSSL 的应用支持；Safari、部分原生应用可能不支持。

### 29.2.3 步骤三：在 Wireshark 中配置

菜单 `Edit → Preferences → Protocols → TLS`：

- 找到 `(Pre)-Master-Secret log filename` 字段。
- 点击 `Browse` 选择刚才的 sslkey.log 文件。
- 点击 `OK` 保存。

或者直接在捕获文件中右键 → `Protocol Preferences → TLS` 配置。

### 29.2.4 步骤四：查看解密结果

配置好后，Wireshark 会重新解析抓包文件。原本显示为 `Application Data` 的包会被解密为 `HTTP` 或 `HTTP2`：

```
Hypertext Transfer Protocol
    GET /index.html HTTP/1.1\r\n
    Host: www.example.com\r\n
    ...
```

现在你可以像分析普通 HTTP 一样分析 HTTPS 流量，包括 Follow HTTP Stream、导出对象等。

### 29.2.5 多行服务器密钥日志（TLS 1.3）

TLS 1.3 使用不同的密钥派生机制，日志中会出现多种条目：

```
CLIENT_HANDSHAKE_TRAFFIC_SECRET ...
SERVER_HANDSHAKE_TRAFFIC_SECRET ...
CLIENT_TRAFFIC_SECRET_0 ...
SERVER_TRAFFIC_SECRET_0 ...
```

Wireshark 3.x/4.x 都支持这些格式。

## 29.3 方法二：RSA 私钥解密

### 29.3.1 准备服务器私钥

获取服务器的 RSA 私钥文件（PEM 格式），并确保 TLS 使用 RSA 密钥交换（而非 ECDHE）。如需强制 RSA，可在服务器端配置密码套件（不推荐在生产环境这样做，会降低安全性）。

### 29.3.2 配置 Wireshark

`Edit → Preferences → Protocols → TLS → RSA Keys List`：

点击 `Edit`，添加条目：

- **IP address**：服务器 IP（0.0.0.0 表示任意）。
- **Port**：443。
- **Protocol**：http。
- **Key File**：选择私钥文件（PEM）。
- **Password**：如果私钥加密，输入密码。

保存后重新解析抓包，TLS 应用数据会被解密。

### 29.3.3 局限性

- 只对 RSA 密钥交换有效，ECDHE 无效。
- TLS 1.3 完全不支持 RSA 解密。
- 需要服务器私钥，实际场景中通常拿不到。

## 29.4 解密验证与排错

| 问题 | 可能原因 |
| --- | --- |
| 配置后仍未解密 | 密钥日志与抓包不匹配（时间、会话不对） |
| 密钥日志为空 | 应用不支持 SSLKEYLOGFILE，或环境变量未生效 |
| 只有部分流解密 | 密钥日志缺少对应会话的条目 |
| 解密后乱码 | 密钥错误或抓包不完整（缺握手包） |

**关键点**：解密需要完整的 TLS 握手包。如果抓包开始时连接已建立（没有 ClientHello），即使有密钥也可能无法解密。

## 29.5 实战流程总结

1. 在**抓包前**设置 SSLKEYLOGFILE 环境变量。
2. 启动应用，访问目标 HTTPS 站点。
3. 同时用 Wireshark 抓包。
4. 停止抓包，确认密钥日志有内容。
5. 在 Wireshark 中配置密钥日志路径。
6. 查看解密后的 HTTP/HTTP2 流量。

## 29.6 小结

- TLS 解密需获取会话密钥，方法有 SSLKEYLOGFILE 和 RSA 私钥两种。
- SSLKEYLOGFILE 最通用：应用导出密钥日志，Wireshark 读取并解密，适用于 ECDHE 和 TLS 1.3。
- RSA 私钥解密仅适用于 RSA 密钥交换，现代 ECDHE 场景无效。
- 解密需要完整握手包，抓包时要有 ClientHello。
- 技术仅用于合法授权的流量分析，切勿用于非法用途。

下一章，学习命令行工具 tshark——把 Wireshark 的分析能力带入脚本世界。
