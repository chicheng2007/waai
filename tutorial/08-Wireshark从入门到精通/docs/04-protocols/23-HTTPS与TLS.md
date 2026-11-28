# 第二十三章 HTTPS 与 TLS

HTTPS 是 HTTP over TLS，即在 TLS（Transport Layer Security，传输层安全）保护下传输 HTTP。TLS 为通信提供机密性（加密）、完整性（防篡改）和身份认证（证书）。本章解析 TLS 的工作原理、握手流程，以及在 Wireshark 中能看到什么、看不到什么。

## 23.1 TLS 概述

TLS 的前身是 SSL（Secure Sockets Layer），由网景公司开发。SSL 3.0 之后更名为 TLS 1.0，后续发展到 TLS 1.2、TLS 1.3。目前 TLS 1.2 和 1.3 是主流，旧版本（SSLv2/3、TLS 1.0/1.1）已被废弃。

TLS 位于传输层和应用层之间，为上层协议（HTTP、SMTP、IMAP 等）提供安全通道。

### 23.1.1 TLS 提供的保障

- **机密性**：对称加密保护数据，第三方无法读取明文。
- **完整性**：MAC（消息认证码）确保数据未被篡改。
- **身份认证**：数字证书验证服务器（可选也验证客户端）身份。
- **防重放**：序列号和随机数防止重放攻击。

## 23.2 TLS 记录协议

TLS 把所有数据封装在**记录（Record）**中：

```
┌──────────┬──────────┬──────────┬──────────────────┬─────────────┐
│ Content  │ Version  │ Length   │ Payload          │ MAC         │
│ Type(1B) │ (2B)     │ (2B)     │ (加密的)          │ (加密的)    │
└──────────┴──────────┴──────────┴──────────────────┴─────────────┘
```

Content Type 主要有：

| 类型 | 值 | 含义 |
| --- | --- | --- |
| Change Cipher Spec | 20 | 切换加密套件通知 |
| Alert | 21 | 告警（如证书错误、关闭通知） |
| Handshake | 22 | 握手消息 |
| Application Data | 23 | 加密的应用数据 |

在 Wireshark 中，加密后的应用数据显示为：

```
Transport Layer Security
    TLSv1.2 Record Layer: Application Data Protocol: http-over-tls
        Content Type: Application Data (23)
        Version: TLS 1.2 (0x0303)
        Length: 512
        Encrypted Application Data: ...
```

**关键点**：Application Data 是加密的，Wireshark 无法看到内容（除非解密）。你能看到的只是记录的长度、类型等元信息。

## 23.3 TLS 握手流程（TLS 1.2）

TLS 1.2 的完整握手需要 2 个往返（2-RTT）：

```
客户端                                          服务器
   |                                               |
   |---- ClientHello ----------------------------->|  1. 客户端问候
   |       (支持的版本、密码套件、随机数、SNI)      |
   |                                               |
   |<--- ServerHello ------------------------------|  2. 服务器回应
   |       (选定版本、密码套件、随机数、会话ID)    |
   |<--- Certificate ----------------------------- |  3. 服务器证书
   |<--- ServerKeyExchange (可选) ---------------- |  4. 密钥交换参数
   |<--- ServerHelloDone ------------------------- |  5. 服务器问候结束
   |                                               |
   |---- ClientKeyExchange ----------------------->|  6. 客户端密钥交换
   |---- ChangeCipherSpec ------------------------>|  7. 切换加密
   |---- Finished -------------------------------->|  8. 握手完成验证
   |                                               |
   |<--- ChangeCipherSpec ------------------------ |  9. 服务器切换加密
   |<--- Finished -------------------------------- | 10. 服务器完成验证
   |                                               |
   |<======== 安全通道建立，开始加密通信 ===========>|
```

### 23.3.1 各消息详解

**ClientHello**：客户端发起握手，包含：

- 支持的最高 TLS 版本。
- 客户端随机数（Client Random，32 字节）。
- 支持的密码套件列表（Cipher Suites）。
- 支持的压缩方法。
- 扩展：SNI（Server Name Indication，请求的域名）、ALPN（应用层协议协商，如 h2/http1.1）、支持的曲线、签名算法等。

```
Handshake Type: Client Hello (1)
    Version: TLS 1.2 (0x0303)
    Random: ...
    Session ID Length: 0
    Cipher Suites Length: ...
    Cipher Suites (N suites)
        Cipher Suite: TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 (0xc02f)
        ...
    Extensions
        Extension: server_name (SNI) - www.example.com
        Extension: application_layer_protocol_negotiation (ALPN) - h2, http/1.1
        Extension: supported_groups (elliptic curves)
```

**ServerHello**：服务器回应，包含：

- 选定的 TLS 版本和密码套件。
- 服务器随机数（Server Random）。
- 会话 ID。

**Certificate**：服务器发送数字证书链，包含服务器公钥、域名、颁发者、有效期等。客户端验证证书合法性。

**ServerKeyExchange**（使用 ECDHE 等密钥交换时）：服务器发送临时公钥和签名。

**ServerHelloDone**：服务器问候阶段结束。

**ClientKeyExchange**：客户端发送临时公钥（Pre-Master Secret 相关参数）。

**ChangeCipherSpec**：通知对方「后续消息将使用协商的密钥加密」。

**Finished**：用协商密钥加密的握手摘要，验证密钥协商成功且握手未被篡改。

### 23.3.2 密钥协商原理

握手的核心目标是双方协商出相同的**会话密钥**（对称密钥），用于加密后续通信。现代 TLS 使用 **ECDHE（椭圆曲线迪菲-赫尔曼临时密钥交换）**：

1. 双方各自生成临时密钥对，交换公钥。
2. 双方用「自己的私钥 + 对方的公钥」计算出相同的共享密钥。
3. 即使攻击者窃听了所有交换，也无法计算出共享密钥（离散对数难题）。
4. 前向保密（Forward Secrecy）：临时密钥每次不同，即使长期私钥泄露，历史通信也无法解密。

## 23.4 TLS 1.3 的改进

TLS 1.3（2018 年标准化）大幅简化了握手：

- **1-RTT 握手**：把 ServerHello 之后的消息合并，减少一个往返。
- **0-RTT 恢复**：连接复用时可在第一个包就发送数据。
- **简化密码套件**：只保留安全的 AEAD 加密（如 AES-GCM、ChaCha20），移除不安全的算法。
- **强制前向保密**：只支持 ECDHE/DHE 密钥交换。
- **加密更多握手消息**：ServerHello 之后的消息都加密，保护隐私。

TLS 1.3 握手在 Wireshark 中显示为 `TLSv1.3`，字段结构与 1.2 有明显差异（如 Cipher Suite 字段位置变化、扩展重要性提升）。

## 23.5 证书解析

证书是 TLS 身份认证的核心。Wireshark 中展开 Certificate 消息可以看到：

```
Certificate (485 bytes)
    Certificate Length: 482
    Certificate: 30:82:01:de... (x509-certificate)
        Version: 3 (0x2)
        Serial Number: 03:...
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: C=US, O=Let's Encrypt, CN=R3
        Validity
            Not Before: Jan 1 00:00:00 2024 GMT
            Not After : Apr 1 00:00:00 2024 GMT
        Subject: CN=www.example.com
        Subject Public Key Info
            Public Key Algorithm: id-ecPublicKey
            Public-Key: (256 bit)
        X509v3 extensions
            X509v3 Subject Alternative Name: DNS:www.example.com, DNS:example.com
            X509v3 Key Usage: Digital Signature, Key Encipherment
```

**分析要点**：

- **Subject / SAN**：证书绑定的域名，检查是否与访问的域名匹配。
- **Issuer**：颁发者，是否可信 CA。
- **Validity**：有效期，是否过期。
- **签名算法**：是否使用弱算法（如 SHA-1）。

## 23.6 Wireshark 中的 TLS 分析

### 23.6.1 基本过滤

```
tls                                      # 所有 TLS 流量
tls.handshake                            # TLS 握手消息
tls.handshake.type == 1                  # ClientHello
tls.handshake.type == 2                  # ServerHello
tls.handshake.type == 11                 # Certificate
tls.handshake.type == 12                 # ServerKeyExchange
tls.handshake.type == 16                 # ClientKeyExchange
tls.handshake.type == 20                 # Finished
tls.alert                                # TLS 告警
tls.record.version == 0x0303             # TLS 1.2
tls.record.content_type == 23            # 应用数据
```

### 23.6.2 不解密能看到什么

即使不解密，TLS 握手仍提供大量信息：

- 客户端/服务器支持的 TLS 版本和密码套件。
- SNI（访问的域名）——**SNI 是明文的**，这是 TLS 隐私的一个弱点（ESNI/ECH 正在改善）。
- 证书内容（域名、颁发者、有效期）。
- ALPN 协商结果（HTTP/1.1 还是 h2）。
- 告警消息（如 `bad certificate`、`handshake failure`）。

### 23.6.3 分析握手失败

| 现象 | 可能原因 |
| --- | --- |
| ClientHello 后收到 Alert | 服务器拒绝（版本/套件不兼容、证书问题） |
| Alert: handshake failure | 密码套件协商失败 |
| Alert: bad certificate | 证书验证失败 |
| ServerHello 后无响应 | 网络问题或客户端验证失败 |
| 大量 ClientHello 无完成握手 | TLS 扫描或攻击 |

### 23.6.4 解密 TLS

要看到加密的应用数据（HTTP 内容），需要解密密钥。Wireshark 支持：

- **RSA 私钥解密**（仅适用于 RSA 密钥交换，现代 ECDHE 无效）。
- **SSLKEYLOGFILE**（Pre-Master Secret 日志，适用于 ECDHE，推荐）。

详见第二十九章「TLS 解密实战」。

## 23.7 小结

- HTTPS = HTTP over TLS，TLS 提供机密性、完整性、身份认证。
- TLS 记录类型：Handshake(22)、Alert(21)、ChangeCipherSpec(20)、Application Data(23)。
- TLS 1.2 握手需 2-RTT：ClientHello → ServerHello → Certificate → ... → Finished。
- 核心是 ECDHE 密钥协商，生成会话密钥，提供前向保密。
- TLS 1.3 简化为 1-RTT（甚至 0-RTT），加密更多握手消息，只保留安全算法。
- Wireshark 可看握手细节、证书、SNI（明文）、告警，但应用数据需密钥才能解密。

下一章，我们快速浏览其他常见的应用层协议。
