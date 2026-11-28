# 第二十二章 HTTP 协议

HTTP（HyperText Transfer Protocol，超文本传输协议）是 Web 的基础，也是 Wireshark 分析中最常见的应用层协议。本章解析 HTTP 的请求/响应格式、方法、状态码、会话机制，以及在 Wireshark 中跟踪和分析 HTTP 流量的方法。

## 22.1 HTTP 基础

HTTP 是客户端—服务器模型的协议：

- **客户端**（通常是浏览器）发送请求。
- **服务器**返回响应。
- 默认端口 80（HTTPS 为 443）。
- HTTP/1.1 是目前主流，HTTP/2、HTTP/3 逐渐普及。

HTTP 是**无状态**协议——服务器不保留客户端的历史请求信息。状态保持依靠 Cookie、Session 等机制。

## 22.2 HTTP 请求报文

```
GET /index.html HTTP/1.1\r\n
Host: www.example.com\r\n
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...\r\n
Accept: text/html,application/xhtml+xml,...\r\n
Accept-Language: zh-CN,zh;q=0.9\r\n
Accept-Encoding: gzip, deflate\r\n
Connection: keep-alive\r\n
Cookie: sessionid=abc123; token=xyz\r\n
\r\n
```

结构：

1. **请求行**：`方法 URI 版本`
2. **请求头**：若干 `字段名: 值` 行
3. **空行**：`\r\n\r\n`，标志头部结束
4. **请求体**（可选）：POST 提交的数据

### 22.2.1 常见方法

| 方法 | 含义 |
| --- | --- |
| GET | 请求资源（最常见） |
| POST | 提交数据（表单、登录、上传） |
| PUT | 上传/替换资源 |
| DELETE | 删除资源 |
| HEAD | 只请求头部，不返回内容 |
| OPTIONS | 查询服务器支持的方法 |
| PATCH | 部分更新资源 |

### 22.2.2 常见请求头

- **Host**：目标主机和端口（HTTP/1.1 必需，支持虚拟主机）。
- **User-Agent**：客户端标识（浏览器、系统信息）。
- **Accept / Accept-Language / Accept-Encoding**：客户端可接受的内容类型、语言、压缩方式。
- **Cookie**：客户端携带的会话 Cookie。
- **Referer**：来源页面。
- **Content-Type / Content-Length**：请求体的类型和长度（POST 时）。
- **Connection**：连接管理（keep-alive / close）。

## 22.3 HTTP 响应报文

```
HTTP/1.1 200 OK\r\n
Date: Mon, 01 Jan 2024 12:00:00 GMT\r\n
Server: nginx/1.20.0\r\n
Content-Type: text/html; charset=UTF-8\r\n
Content-Length: 1234\r\n
Set-Cookie: sessionid=abc123; Path=/; HttpOnly\r\n
Cache-Control: max-age=3600\r\n
\r\n
<!DOCTYPE html>...
```

结构：

1. **状态行**：`版本 状态码 原因短语`
2. **响应头**
3. **空行**
4. **响应体**

### 22.3.1 状态码

| 类别 | 范围 | 含义 | 常见码 |
| --- | --- | --- | --- |
| 1xx | 100~199 | 信息性 | 100 Continue |
| 2xx | 200~299 | 成功 | 200 OK、201 Created、204 No Content |
| 3xx | 300~399 | 重定向 | 301 永久、302 临时、304 未修改 |
| 4xx | 400~499 | 客户端错误 | 400 错误请求、401 未授权、403 禁止、404 未找到 |
| 5xx | 500~599 | 服务器错误 | 500 内部错误、502 网关错误、503 服务不可用 |

### 22.3.2 常见响应头

- **Server**：服务器软件信息。
- **Content-Type / Content-Length**：响应体类型和长度。
- **Set-Cookie**：服务器下发 Cookie。
- **Cache-Control / Expires / ETag**：缓存控制。
- **Location**：重定向目标。
- **Transfer-Encoding**：分块传输编码。

## 22.4 Wireshark 中的 HTTP 分析

### 22.4.1 基本过滤

```
http                                     # 所有 HTTP 包（1.0/1.1）
http.request                             # HTTP 请求
http.response                            # HTTP 响应
http.request.method == "GET"             # GET 请求
http.request.method == "POST"            # POST 请求
http.request.uri contains "login"        # URI 含 login
http.host == "www.example.com"           # 特定主机
http.response.code == 200                # 200 响应
http.response.code >= 400                # 错误响应
http.content_type contains "json"        # JSON 内容
http.cookie                              # 含 Cookie 的请求
http.set_cookie                          # 含 Set-Cookie 的响应
http.user_agent contains "Firefox"       # 特定客户端
```

### 22.4.2 协议详情窗格

一个 HTTP 请求的展开示例：

```
Hypertext Transfer Protocol
    GET /index.html HTTP/1.1\r\n
        [Expert Info (Chat/Sequence): GET /index.html HTTP/1.1\r\n]
        Request Method: GET
        Request URI: /index.html
        Request Version: HTTP/1.1
    Host: www.example.com\r\n
    User-Agent: Mozilla/5.0 ...\r\n
    Accept: text/html,...\r\n
    \r\n
    [Full request URI: http://www.example.com/index.html]
    [HTTP request 1/1]
    [Response in frame: 123]
```

注意 `[Response in frame: 123]`——Wireshark 自动标注了对应的响应包，点击可跳转。响应包中也有 `[Request in frame: X]`。

### 22.4.3 Follow HTTP Stream

右键 HTTP 包 → `Follow → TCP Stream`（或 HTTP Stream），会打开一个新窗口，以对话形式显示完整的请求和响应内容：

```
GET /index.html HTTP/1.1
Host: www.example.com
...

HTTP/1.1 200 OK
Content-Type: text/html
...

<!DOCTYPE html>
...
```

这是查看 HTTP 会话最直观的方式。客户端内容通常显示为红色，服务器显示为蓝色。

### 22.4.4 导出 HTTP 对象

前面第十五章提到，`File → Export Objects → HTTP` 可以提取传输的文件（图片、脚本、文档等）。这在取证和 CTF 中非常实用。

### 22.4.5 重组分片

HTTP 响应体可能跨越多个 TCP 段。Wireshark 会自动重组，在最后一个段显示：

```
[Reassembled TCP Segments: 5]
Hypertext Transfer Protocol
    HTTP/1.1 200 OK\r\n
    ...
    File Data: 45678 bytes
```

如果重组失败（如丢包），会显示 `[Continuation]` 或无法解析。

## 22.5 HTTP 会话分析实战

### 22.5.1 分析一次网页加载

1. 过滤 `http`，观察请求顺序。
2. 看第一个请求（通常是 HTML 文档）及其 200 响应。
3. 看后续的资源请求（CSS、JS、图片）——现代网页通常有几十个请求。
4. 关注 4xx/5xx 响应（加载失败的资源）。
5. 关注时间戳，找出加载慢的请求。

### 22.5.2 分析登录过程

1. 过滤 `http.request.method == "POST"` 找到登录提交。
2. 展开请求，查看请求体中的用户名、密码（明文 HTTP 下可见）。
3. 看响应中的 `Set-Cookie` 和状态码（302 重定向通常表示登录成功）。
4. 后续请求携带 `Cookie` 维持会话。

> **安全提示**：HTTP 明文传输，用户名、密码、Cookie 都能被抓包看到。这就是为什么必须使用 HTTPS。在 Wireshark 中抓 HTTP 登录包，能直观理解明文传输的风险。

### 22.5.3 性能分析

- 用 `Statistics → HTTP → Requests by URI` 查看请求分布。
- 用 `http.time > 1`（需启用）找慢响应。
- 结合 TCP 层分析（重传、RTT）判断慢的原因在网络还是服务器。

## 22.6 HTTP/2 与 HTTP/3 简述

- **HTTP/2**：二进制协议，多路复用、头部压缩（HPACK）、服务器推送。在 Wireshark 中显示为 `HTTP2` 协议，基于 TLS 时需要解密才能看到（见第二十九章）。
- **HTTP/3**：基于 QUIC（UDP），进一步减少延迟，在 Wireshark 中显示为 `HTTP/3` 或 `QUIC`。

传统 HTTP/1.1 的分析方法（Follow Stream、导出对象）依然适用，但协议细节差异较大。

## 22.7 小结

- HTTP 是请求—响应模型的无状态应用层协议，默认端口 80。
- 请求报文：请求行（方法/URI/版本）+ 头部 + 空行 + 请求体。
- 响应报文：状态行（版本/状态码/原因）+ 头部 + 空行 + 响应体。
- 方法：GET、POST、PUT、DELETE 等；状态码分 1xx~5xx 五类。
- Wireshark 中用 `http.request`、`http.response.code`、`http.host` 等过滤；Follow Stream 看完整会话；Export Objects 提取文件。
- HTTP 明文传输存在安全风险；HTTP/2、HTTP/3 需要解密才能深度分析。

下一章，我们解析保护 Web 通信的 TLS/HTTPS 协议。
