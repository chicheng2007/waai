# 第 4 章 HTTP 协议与 Web 基础

## 本章目标

读完这一章，你将能够：

- 说清楚浏览器访问一个网页时，背后发生了什么
- 看懂一个 HTTP 请求和响应的每个组成部分
- 理解 URL、请求方法、状态码、Header、Cookie、Session 的含义
- 用 curl 和浏览器开发者工具手工观察 HTTP 通信
- 建立起"Web 漏洞本质是 HTTP 通信被钻空子"的认知

> 这一章是 Web 方向的地基。所有 Web 漏洞——注入、XSS、上传、越权——本质上都是"HTTP 请求里的某个部分被攻击者操控了"。看懂 HTTP，你就看懂了 Web 漏洞的战场。

---

## 4.1 从输入网址到看到页面：发生了什么

当你在浏览器输入 `http://www.example.com` 并回车，背后发生了一连串事情。理解这个过程，是理解 Web 的起点。

```
1. DNS 解析：把域名 www.example.com 解析成 IP 地址（如 93.184.216.34）
2. 建立连接：浏览器和服务器通过 TCP 三次握手建立连接（HTTP 基于 TCP）
3. 发送请求：浏览器构造一个 HTTP 请求，发给服务器："请把首页给我"
4. 服务器处理：服务器（如 Nginx/Apache）收到请求，可能交给程序（PHP/Python）处理
5. 返回响应：服务器构造一个 HTTP 响应，包含状态码、响应头和网页内容
6. 浏览器渲染：浏览器解析 HTML，加载 CSS/JS/图片，最终呈现页面
7. 断开/复用连接：HTTP/1.1 默认保持连接，可继续请求其他资源
```

**CTF 视角**：这七步里，**第 3 步（请求）和第 5 步（响应）是漏洞的主战场**。攻击者操控请求（构造恶意参数），或利用响应（泄露敏感信息）。抓包工具（Burp）就是让你能"看见并改写"这两步。

**小白问：HTTP 和 HTTPS 什么区别？**
> HTTPS = HTTP + TLS 加密。内容传输前被加密，旁人看不到明文。对 CTF 来说，逻辑上一样——抓包浏览器解密后依然能看到请求内容（这就是第 2 章要装 CA 证书的原因）。

---

## 4.2 HTTP 请求：解剖一封"索要信"

HTTP 请求就像你给服务器写的一封信。我们用 curl 实际看一个：

```bash
curl -v http://example.com
```

发出的请求大致长这样：

```http
GET / HTTP/1.1
Host: example.com
User-Agent: curl/7.81.0
Accept: */*
Cookie: session=abc123
Referer: http://google.com
```

### 4.2.1 请求行（第一行）

```
GET / HTTP/1.1
```

三部分：
- **请求方法**（GET）：告诉服务器要做什么操作
- **请求路径**（`/`）：要访问的资源，这里是根路径
- **协议版本**（HTTP/1.1）

### 4.2.2 请求方法

| 方法 | 含义 | CTF 中的意义 |
|------|------|-------------|
| **GET** | 获取资源，参数放在 URL 里 | 最常见，注入/XSS 常在 URL 参数里 |
| **POST** | 提交数据，参数放在请求体里 | 登录、表单提交，注入点常在 body |
| PUT | 上传/替换资源 | 配置不当可利用（如 PUT 上传 WebShell） |
| DELETE | 删除资源 | 配置不当可删文件 |
| HEAD | 只取响应头，不要正文 | 快速探测 |
| OPTIONS | 询问服务器支持哪些方法 | 信息收集 |

**小白问：GET 和 POST 有什么区别？**
> GET 参数在 URL（地址栏可见、有长度限制、会被浏览器缓存/记录历史）；POST 参数在请求体（不可见、无长度限制、相对"私密"）。但注意：**POST 并不比 GET 安全**——两者都被抓包工具看得一清二楚，都不能用来传敏感信息（那是 HTTPS 的职责）。CTF 里两种都可能藏漏洞。

### 4.2.3 请求头（Header）

从 `Host:` 开始的每一行都是一个请求头，格式为 `名称: 值`。常见请求头：

| 请求头 | 作用 | CTF 关注点 |
|--------|------|-----------|
| **Host** | 目标域名 | 虚拟主机、Host 头注入 |
| **User-Agent** | 客户端标识（浏览器/工具） | 有时服务器只对特定 UA 开放功能；伪造 UA |
| **Cookie** | 携带客户端状态（会话标识等） | 越权、会话固定、Cookie 注入 |
| **Referer** | 从哪个页面过来的 | 防盗链绕过、CSRF 检查 |
| **X-Forwarded-For** | 声称的客户端 IP | 伪造 IP 绕过限制 |
| **Content-Type** | 请求体格式 | 上传题里决定服务器如何解析 |
| **Authorization** | 认证信息（如 Bearer Token） | JWT、Basic Auth 相关漏洞 |

**CTF 关键点**：**请求头是攻击者可控的**——你可以用 Burp 随意修改任何头。很多漏洞就藏在服务器对某个头的信任上，比如：

- 服务器相信 `X-Forwarded-For` 里的 IP，你伪造它就能绕过 IP 限制
- 服务器相信 `Referer` 判断来源，你伪造它就能绕过防盗链
- 服务器把 `User-Agent` 拼进 SQL 语句（少见但存在），就是注入点

### 4.2.4 请求体（Body）

GET 请求通常没有请求体。POST 请求的参数放在请求体里，例如登录表单：

```http
POST /login HTTP/1.1
Host: example.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 29

username=admin&password=123456
```

最后一行就是请求体，格式是 `参数名=值&参数名=值`。CTF 里POST 参数是注入、XSS、越权的常见入口。

---

## 4.3 HTTP 响应：服务器的"回信"

服务器返回的响应也分三部分。用 curl 看：

```bash
curl -v http://example.com
```

响应大致是：

```http
HTTP/1.1 200 OK
Content-Type: text/html
Server: Apache/2.4.41
Set-Cookie: session=xyz789; HttpOnly
Content-Length: 1256

<!DOCTYPE html>
<html>...网页内容...</html>
```

### 4.3.1 状态行与状态码

```
HTTP/1.1 200 OK
```

**状态码**是服务器对请求结果的"评语"，分五大类：

| 类别 | 范围 | 含义 | 常见码 |
|------|------|------|--------|
| 1xx | 100–199 | 信息性，请求已收到 | 100 Continue |
| **2xx** | 200–299 | **成功** | 200 OK、201 Created、204 No Content |
| **3xx** | 300–399 | **重定向** | 301 永久重定向、302 临时重定向、304 未修改 |
| **4xx** | 400–499 | **客户端错误** | 400 请求错误、**403 禁止访问**、**404 不存在**、405 方法不允许 |
| **5xx** | 500–599 | **服务器错误** | 500 服务器内部错误、502 网关错误、503 不可用 |

**CTF 关注点**：

- **403 Forbidden**：说明资源存在但你没权限——常提示有东西可挖，试试绕过（改 Header、路径变形）
- **404 Not Found**：通常真不存在，但有时是"假装不存在"（用 dirsearch 爆破目录时会遇到）
- **500 Internal Server Error**：服务器报错，有时会在页面里泄露数据库信息/代码路径——注入探测时故意引发 500 是常用手法
- **302 重定向**：注意 Location 头指向哪，有些漏洞利用重定向绕过

### 4.3.2 响应头

| 响应头 | 作用 | CTF 关注点 |
|--------|------|-----------|
| **Server** | 服务器软件及版本 | 信息收集，找已知 CVE |
| **X-Powered-By** | 后端技术（如 PHP/7.4） | 信息收集 |
| **Set-Cookie** | 服务器让浏览器设置 Cookie | 会话、JWT、Cookie 属性检查 |
| **Location** | 重定向目标 | 开放重定向漏洞 |
| **Content-Type** | 内容类型 | 上传题里服务器按此解析 |
| **Content-Disposition** | 下载时的文件名 | 文件下载漏洞 |

**小白问：为什么响应头会泄露信息？**
> 很多服务器默认配置会输出 `Server: Apache/2.4.41` 这样的头，等于告诉攻击者"我用的是这个版本"。攻击者可以查这个版本有没有已知漏洞。所以安全加固时会关掉这些头（第 20 章会讲）。CTF 里这些头是重要的信息收集来源。

### 4.3.3 响应体

响应体就是网页的实际内容（HTML/JSON/图片等）。漏洞的"成果"往往体现在响应体里——比如注入成功后，响应体里出现了本不该显示的数据。

---

## 4.4 URL 与参数：漏洞的常见入口

URL（统一资源定位符）是资源的地址，结构如下：

```
http://example.com:80/path/page.php?id=1&name=test#section
└──┬──┘ └───┬───┘ └─┬─┘ └──────┬──────┘ └──┬──┘
 协议     主机   端口  路径      查询参数      片段
```

- **协议** http/https
- **主机** 域名或 IP
- **端口** 默认 http=80、https=443，可省略
- **路径** 服务器上的资源位置
- **查询参数**（Query String）：`?` 后 `&` 分隔的键值对，如 `id=1&name=test`
- **片段**（Fragment）：`#` 后，浏览器内部用，不发给服务器

**CTF 视角**：查询参数（如 `id=1`）是漏洞最常见的入口。攻击者把参数值改成特殊内容（如 `id=1' or 1=1`），看服务器反应——这就是注入探测的基本思路。

**URL 编码**：URL 里有些字符有特殊含义（如 `?`、`&`、`=`），要传这些字符本身就得编码。编码规则是 `%XX`（XX 是字符的十六进制 ASCII 码）。

| 字符 | 编码 | 说明 |
|------|------|------|
| 空格 | `%20` 或 `+` | |
| `?` | `%3F` | |
| `&` | `%26` | |
| `=` | `%3D` | |
| `'` | `%27` | 注入常用 |
| `<` | `%3C` | XSS 常用 |
| `/` | `%2F` | 路径绕过常用 |

浏览器会自动做部分编码，Burp 里可以手动改。理解 URL 编码对构造 payload 至关重要——很多绕过技巧就是靠编码躲过过滤。

---

## 4.5 Cookie 与 Session：Web 的"记忆"

HTTP 本身是**无状态**的——服务器处理完一个请求就忘了你是谁。但网站需要"记住"用户（比如登录后保持登录状态），这就靠 Cookie 和 Session。

### 4.5.1 Cookie

Cookie 是服务器通过 `Set-Cookie` 响应头让浏览器保存的一小段数据，之后每次请求浏览器都会自动带上它。

```http
# 服务器响应
Set-Cookie: username=admin; Path=/; HttpOnly; Secure

# 浏览器后续请求
Cookie: username=admin
```

Cookie 常见属性：

| 属性 | 含义 | 安全相关 |
|------|------|---------|
| `HttpOnly` | JS 不能读取该 Cookie | 防 XSS 窃取会话 Cookie |
| `Secure` | 只在 HTTPS 下发送 | 防明文传输被窃听 |
| `SameSite` | 限制跨站发送 | 防 CSRF |
| `Expires/Max-Age` | 过期时间 | 持久化 Cookie |

**CTF 关注点**：Cookie 里的值如果是明文的身份标识（如 `username=admin`），你改成 `username=administrator` 或别人的用户名，就可能**越权**访问他人数据（第 15 章逻辑漏洞会讲）。

### 4.5.2 Session

Session 是服务器端的"记忆"。服务器给每个用户分配一个 Session ID（通常存在 Cookie 里，如 `PHPSESSID=abc123`），用户数据存在服务器。浏览器带 Session ID 来，服务器查到对应用户。

**CTF 关注点**：
- Session ID 如果可预测（如按顺序递增），可**会话劫持**
- 登录前后 Session ID 不变，可能**会话固定**漏洞
- Cookie 里的 Session 如果编码可解（如 JWT），可**伪造身份**

---

## 4.6 手工观察 HTTP：curl 与开发者工具

理论讲完，动手看真实的 HTTP。

### 4.6.1 curl：命令行 HTTP 客户端

```bash
# 查看完整请求响应过程
curl -v https://www.baidu.com

# 只看响应头
curl -I https://www.baidu.com

# 发 GET 请求带参数
curl "http://example.com/page?id=1&name=test"

# 发 POST 请求
curl -X POST -d "username=admin&password=123" http://example.com/login

# 自定义请求头
curl -H "X-Forwarded-For: 127.0.0.1" http://example.com

# 带 Cookie
curl -b "session=abc123" http://example.com
```

把玩这些命令，你能真切地看到"请求由什么组成、怎么操控每一部分"。

### 4.6.2 浏览器开发者工具

按 F12 打开开发者工具，切到 **Network（网络）** 标签，刷新页面，你会看到浏览器发出的所有请求。点任意一个请求，能看到：

- **Headers**：请求头 + 响应头
- **Payload/Params**：请求参数（GET 的 query、POST 的 body）
- **Response**：响应内容
- **Cookies**：请求携带的 Cookie

这是比 Burp 更轻量的观察工具，日常快速查看很方便。要**改写**请求则用 Burp。

---

## 4.7 一个完整的手工探测示例

把本章知识串起来。假设有道题给你一个 URL：`http://test.com/news?id=1`，页面显示一篇新闻。按 CTF 方法论走一遍：

**① 观察**：
- 用浏览器开发者工具看请求：`GET /news?id=1`，响应 200，返回新闻内容
- 看源代码：无注释线索
- 用 curl 看响应头：`Server: Apache/2.4.41`, `X-Powered-By: PHP/7.4`

**② 假设**：`id` 参数很可能用于数据库查询（新闻按 id 查），可能存在 SQL 注入

**③ 验证**：
```bash
# 基准
curl "http://test.com/news?id=1"          # 正常显示一篇新闻

# 加单引号探测
curl "http://test.com/news?id=1'"         # 观察是否报错

# 经典注入测试
curl "http://test.com/news?id=1' or 1=1--"  # 是否返回所有新闻

# URL 编码版本（如果直接输入被拦截）
curl "http://test.com/news?id=1%27%20or%201=1--"
```

**④ 归纳**：如果某条 payload 让页面返回了所有新闻，说明存在 SQL 注入——记录这个模式，进入第 6 章系统学习。

这就是 Web 题的基本套路：**观察 HTTP → 定位可控参数 → 构造 payload 测试 → 看响应判断结果**。你现在已经具备了做这件事的全部基础知识。

---

## 4.8 本章总结

| 知识点 | 核心要点 |
|--------|---------|
| 访问网页流程 | DNS → TCP → 发请求 → 服务器处理 → 返回响应 → 渲染 |
| HTTP 请求 | 请求行（方法/路径/版本）+ 请求头 + 请求体 |
| 请求方法 | GET（参数在 URL）、POST（参数在 body）；都不安全，需 HTTPS |
| 请求头可控 | Host/UA/Cookie/Referer/XFF 都可伪造，是漏洞入口 |
| 状态码 | 2xx 成功、3xx 重定向、4xx 客户端错、5xx 服务器错（403/500 重点关注） |
| 响应头泄露 | Server/X-Powered-By 泄露版本，是信息收集来源 |
| URL 参数 | `?id=1` 这类参数是最常见漏洞入口 |
| URL 编码 | `%XX` 格式；绕过过滤的关键技巧 |
| Cookie/Session | 无状态 HTTP 的"记忆"；明文身份 Cookie 可致越权 |
| 手工观察 | curl -v / -I / -d / -H / -b；浏览器 F12 Network |

---

## 本章练习

1. 用 `curl -v https://www.baidu.com` 观察一次完整通信，找出请求行、几个请求头、状态码、几个响应头。
2. 用浏览器 F12 的 Network 面板，打开任意一个网站，随便点一个请求，说出它的请求方法、路径、状态码。
3. 对比 GET 和 POST：用 curl 分别发一个 GET 和一个 POST 请求，观察参数位置的不同。
4. 把字符串 `1' or 1=1--` 做 URL 编码（可以用在线工具或 CyberChef），写出编码结果。
5. 找一个网站，检查它的响应头有没有泄露 `Server`/`X-Powered-By` 信息（只观察，不要测试漏洞）。
6. 思考：为什么说"POST 比 GET 安全"是个误区？

---

**下一章预告**：HTTP 看懂了，下一步是"信息收集"——如何系统性地摸清一个目标：扫描目录、探测技术栈、找隐藏文件。很多 flag 其实就藏在这些"被遗忘的角落"里。
