# 第 23 章 Burp Suite 深入使用

## 本章目标

读完这一章，你将能够：

- 理解 Burp Suite 各模块的作用与协作关系
- 熟练使用 Proxy 拦截、改包、Repeater 重放
- 用 Intruder 做爆破与模糊测试
- 用 Decoder 做编码解码
- 掌握常见 CTF 场景下的 Burp 使用技巧
- 理解插件（BApp Store）扩展能力

> 第 2 章你已经配好了 Burp，会用基本抓包。这一章深入它的核心模块——这是 Web 题"提速十倍"的关键工具。工具用得熟，解题才快。

---

## 23.1 Burp 的模块地图

Burp Suite 由多个模块（Tool）组成，各司其职：

| 模块 | 作用 | CTF 用途 |
|------|------|---------|
| **Proxy** | 拦截/查看/修改 HTTP 流量 | 抓包、改包（核心入口） |
| **Repeater** | 手动重放单个请求，反复改 | 手工测注入、调 payload |
| **Intruder** | 自动化爆破/模糊测试 | 爆破密码、枚举参数、fuzz |
| **Scanner** | 自动扫描漏洞（专业版才有） | 社区版无，了解即可 |
| **Decoder** | 编码解码转换 | Base64/Hex/URL 快速转换 |
| **Comparer** | 比较两个请求/响应的差异 | 找盲注/条件差异 |
| **Sequencer** | 分析随机数质量（如 token） | 判断 token 是否可预测 |
| **Extender** | 加载插件 | 扩展功能 |

**核心工作流**：Proxy 抓包 → 右键发送到 Repeater 手工调 → 需要爆破时发送到 Intruder → Decoder 辅助编码。记住这条链，80% 的 Web 操作都在这几个模块间流转。

---

## 23.2 Proxy：拦截与改包

### 23.2.1 Intercept（拦截）

Proxy 的 Intercept 标签能"截住"请求，让你在它发到服务器前修改。

- **Intercept is on/off**：开关拦截
- **Forward**：放行（发送修改后的请求）
- **Drop**：丢弃请求
- **Action**：右键菜单，把请求发送到其他模块

**改包示例**：拦截一个登录 POST 请求，把 `password=123` 改成 `password=admin' or '1'='1`，再 Forward——这就是手工注入测试。

### 23.2.2 HTTP History

所有经过 Burp 的请求都记录在 HTTP History 里。可以快速筛选：

- 按方法（GET/POST）、状态码、MIME 类型过滤
- 搜索关键词（如 flag、admin）
- 右键请求 → Send to Repeater / Intruder

**技巧**：浏览网站时开着 Proxy 但关掉 Intercept（不拦截，只记录），事后在 HTTP History 里慢慢分析——这是最常见的用法。

---

## 23.3 Repeater：手工重放的主战场

Repeater 让你把一个请求拿出来，反复修改、发送、观察响应，不影响浏览器。

**典型用法**：

```
① Proxy 里右键请求 → Send to Repeater
② 在 Repeater 里改参数（如 id=1' or 1=1）
③ 点 Send，看右侧响应
④ 反复调整 payload，直到拿到想要的结果
```

**为什么重要**：Repeater 是手工测试漏洞的主战场——SQL 注入、XSS、逻辑漏洞，都在它里面一遍遍调。它比在浏览器里改 URL 灵活得多，而且能精确控制每一个字节。

**小技巧**：Repeater 支持多标签页，可以同时开多个请求对比。

---

## 23.4 Intruder：爆破与模糊测试

Intruder 把请求里的某个位置用 payload 字典批量替换，自动发送并收集结果。

### 23.4.1 四个标签

| 标签 | 作用 |
|------|------|
| **Target** | 目标地址 |
| **Positions** | 标记要替换的位置（用 `§` 包裹） |
| **Payloads** | 设置 payload 字典 |
| **Options** | 线程数、延迟、结果匹配规则 |

### 23.4.2 使用流程

```
① 右键请求 → Send to Intruder
② Positions：选中要爆破的值 → Add §（如密码字段）
③ Payloads：加载字典（如 passwords.txt）
④ Start Attack → 查看结果
⑤ 分析：按状态码、长度、响应时间排序，找"不一样的"结果
```

### 23.4.3 四种攻击模式

| 模式 | 说明 | 用途 |
|------|------|------|
| Sniper | 单位置逐个试 | 爆破密码单字段 |
| Battering ram | 多位置用同一个 payload | 用户名密码相同 |
| Pitchfork | 多位置用不同字典，一一对应 | 用户名字典+密码字典对应 |
| Cluster bomb | 多位置笛卡尔积组合 | 用户名×密码全组合 |

### 23.4.4 分析结果（关键）

爆破后几百上千条结果，怎么找正确的？看**响应差异**：

- **Status**（状态码）：200 通常比 403/302 可疑
- **Length**（响应长度）：正确的登录响应长度往往不同
- **Time**（响应时间）：时间盲注靠这个

**CTF 技巧**：爆破验证码、密码、目录时，按 Length 排序，找"异类"——那就是答案。

---

## 23.5 Decoder 与 Comparer

### 23.5.1 Decoder

快速编码/解码工具，支持 Base64、Hex、URL、HTML、Gzip 等，还能做哈希。

```
输入一段字符串 → 选择 Decode as Base64 → 立即看到结果
```

CTF 里快速验证编码时很方便（比开 CyberChef 还快）。

### 23.5.2 Comparer

比较两个请求/响应的逐字节差异。用途：

- 盲注时对比"条件为真"和"条件为假"的响应差异
- 找两个相似页面中唯一不同的部分

把 Repeater 里两次不同 payload 的响应分别送到 Comparer，高亮显示差异。

---

## 23.6 CTF 常用技巧合集

| 场景 | Burp 操作 |
|------|----------|
| 改前端校验 | Proxy 拦截，改文件名/参数后 Forward |
| 测 SQL 注入 | Send to Repeater，逐个试 payload |
| 爆破密码 | Send to Intruder，Sniper + 字典 |
| 越权测试 | 改 Cookie/user_id 参数，Repeater 观察 |
| 找隐藏参数 | Intruder fuzz 参数名 |
| 绕过 IP 限制 | 加 `X-Forwarded-For` 头，Repeater 试不同 IP |
| 编码转换 | Decoder |
| 对比响应 | Comparer |

---

## 23.7 插件（BApp Store）

Burp 的 Extender 可以装插件扩展能力。CTF 常用：

| 插件 | 作用 |
|------|------|
| **Decoder Improved** | 更强的解码 |
| **JSON Web Tokens** | JWT 解码和篡改 |
| **SQLiPy** | 集成 sqlmap |
| **Collaborator Everywhere** | 检测 SSRF/盲打 |
| **Logger++** | 增强日志 |

安装：Extender → BApp Store → 搜索 → Install。社区版也能装大部分插件。

---

## 23.8 本章总结

| 模块 | 核心用途 |
|------|---------|
| Proxy | 抓包、拦截改包、HTTP History |
| Repeater | 手工重放调 payload（主战场） |
| Intruder | 爆破/fuzz；看状态码/长度/时间差异 |
| Decoder | 编码解码 |
| Comparer | 对比响应差异 |
| 工作流 | Proxy 抓 → Repeater 调 → Intruder 爆破 → Decoder 辅助 |

---

## 本章练习

1. 在 DVWA 上，用 Proxy 抓一个登录请求，发送到 Repeater，手工改密码字段测试。
2. 用 Intruder 对一个登录框做密码爆破（用自己的弱密码字典），按 Length 排序找正确结果。
3. 用 Decoder 解码一段 Base64 和 Hex 字符串。
4. 用 Comparer 对比两个不同响应的差异。
5. 装一个 JWT 插件，用它解码一个 JWT 令牌。
6. 总结：Proxy、Repeater、Intruder 三个模块分别在什么场景下用？

---

**下一章预告**：Burp 是"交互式工具"，第 24 章讲用 Python 写自己的 CTF 工具——批量请求、自动化爆破、编解码脚本。把工具变成自己的代码，能力才算真正内化。
