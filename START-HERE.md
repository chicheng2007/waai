# 从这里开始 · 网安实战版（14 天做出一个能写进简历的项目）

> **前置**：如果你一看 `for line in ...split()` 就懵，先花 3 天看 [SYNTAX-BOOTCAMP.md（语法急救包）](guides/SYNTAX-BOOTCAMP.md)，用"发牌/切香肠"讲懂 5 个必备零件，再回来做这个计划。
>
> **默认你会基础语法**（变量 / 循环 / 函数不再从头讲）——不敲 `print` 玩语法。**14 天，每天一个真任务，最后交付一个完整的"AI 日志研判工具"到 GitHub。**
> 只在项目里卡住的地方问本地模型（求助流程在下面），边做边补。

**导航**：[README](README.md) · [每日打卡](checkin-log.md) · [Python 路线](tools/python-roadmap.md) · [硬件环境](reference/hardware-setup.md) · [总览](roadmap/00-overview.md)

---

## 三条规则（照做就行）

1. **只做当天的**，别往前翻。
2. **不会就问本地模型**——你有 Qwen3.5-9B，它是 24 小时助教，问它不要钱。
3. **卡住超过 15 分钟就求助**，别死磕（求助模板在下面）。

---

## PyCharm 速查（每天就这四步）

| 我想做什么 | 怎么点 |
|---|---|
| 新建代码文件 | 左侧项目树右键 → New → Python File → 输入名字 |
| 运行代码 | 代码区右键 → Run '文件名'，或右上角绿色三角 ▶ |
| 看结果 / 报错 | 底部 **Console**；报错看**最后一行** |
| 装库 | 底部 **Terminal** 敲 `pip install 库名` 回车 |

**每天流程**：新建 `.py` → 写代码 → 右键 Run → 看 Console。

---

## 卡住了怎么办（求助流程）

打开 LM Studio，原样复制（把【】换成你的情况）：

```
我在做网安日志分析项目，基础语法没问题，但这段实战代码卡住了：

【粘贴你的代码】

报错信息：【粘贴 Console 里红色字，尤其是最后一行】

请直接告诉我：
1. 哪里错了、为什么
2. 改好的完整代码
3. 涉及的关键库/技巧（如正则、pandas）讲清楚用法就行，基础语法不用解释
```

某段代码没看懂就追问："这段里的【具体语法/函数】是什么意思，给我举个贴近日志分析的例子。" 还不行就来找我问。

---

## 每天的固定节奏

| 时段 | 做什么 | 时长 |
|---|---|---|
| 软考 | 看课 / 教程 + 做真题（这是你的主线，别挂） | 1~2 小时 |
| Python 实战 | 做当天的真任务 | 30~45 分钟 |
| 打卡 | 在 [checkin-log.md](checkin-log.md) 追加一行 | 1 分钟 |

---

# 14 天实战路线

> 每天结构：软考任务 → 今日实战（含可跑代码）→ 网安联系 → 自检 → 打卡。
> **最终产物**：一个能分析日志、识别可疑 IP、还能调本地大模型研判的 Python 工具，托管到 GitHub。

---

## 第 0 天（准备日，10 分钟）：PyCharm 建项目 + 装库

**目标**：建好项目，装好今天开始要用的库。

1. PyCharm → New Project → 路径选 `D:\sec-log-analyzer`（好记），点 Create。
2. 底部打开 **Terminal**，逐行执行（一行执行完再下一行）：
   ```bash
   pip install requests pandas matplotlib
   ```
3. 建一个文件 `data.py`，输入下面这段，右键 Run，Console 打印出示例日志就成：

```python
# 这是我们要分析的访问日志样例（Apache/Nginx 格式）
LOG_SAMPLE = '''192.168.1.100 - - [25/Nov/2026:12:00:01 +0800] "GET /index.html HTTP/1.1" 200 1234
10.0.0.5 - - [25/Nov/2026:12:00:03 +0800] "POST /login HTTP/1.1" 401 512
192.168.1.100 - - [25/Nov/2026:12:00:05 +0800] "GET /admin HTTP/1.1" 404 231
45.33.22.11 - - [25/Nov/2026:12:00:07 +0800] "GET /wp-login.php HTTP/1.1" 404 178'''

for line in LOG_SAMPLE.strip().split("\n"):
    print(line)
```

**今天到这就结束。** 这个文件后面每天都要用。

---

## 第 1 天：从日志里统计 IP 出现次数（你的第一个真分析）

**软考任务**：教程第 1 章 + 10 道选择题。

**今日实战**：新建 `day1.py`，统计每个 IP 访问了多少次：

```python
from collections import Counter
from data import LOG_SAMPLE

ips = []
for line in LOG_SAMPLE.strip().split("\n"):
    ip = line.split()[0]          # 每行第一个空格前就是 IP
    ips.append(ip)

counts = Counter(ips)
for ip, n in counts.most_common():
    print(f"{ip}: {n} 次")
```

**预期输出**：能看到 `192.168.1.100: 2 次`，其他各 1 次。

**网安联系**：访问次数异常高的 IP，可能是扫描器或攻击者——这就是最朴素的威胁检测。

**自检**：能改成"只显示访问超过 1 次的 IP"吗？（提示：`if n > 1`）

**打卡**：`| 日期 | 网安实战 | 第1天：日志IP统计 | 30min | 状态 |`

---

## 第 2 天：用正则提取完整字段（IP / 时间 / 请求 / 状态码）

**软考任务**：搞懂 TCP/IP 分层。

**今日实战**：新建 `day2.py`：

```python
import re
from data import LOG_SAMPLE

# 正则四个括号 = 四个要提取的字段
pattern = r'(\d+\.\d+\.\d+\.\d+).*?\[(.*?)\].*?"(\w+ \S+).*?" (\d+)'

for line in LOG_SAMPLE.strip().split("\n"):
    m = re.match(pattern, line)
    if m:
        ip, time, request, status = m.groups()
        print(f"IP={ip} | 时间={time} | 请求={request} | 状态码={status}")
```

**看不懂正则？** 原样问本地模型："请逐段解释 `r'(\d+\.\d+\.\d+\.\d+).*?\[(.*?)\].*?"(\w+ \S+).*?" (\d+)'` 这段正则。" 它会一段段讲。

**网安联系**：状态码 401（未授权）、404（不存在）大量出现，往往是攻击尝试。

**自检**：能改成只打印状态码是 404 的行吗？

---

## 第 3 天：识别可疑 IP（条件判断 + 字典）

**软考任务**：IP 地址与子网划分（软考重点，多做几道）。

**今日实战**：新建 `day3.py`，标记"访问 /admin 或 /wp-login.php 的 IP"为可疑：

```python
import re
from data import LOG_SAMPLE

pattern = r'(\d+\.\d+\.\d+\.\d+).*?"(\w+ \S+)'
suspicious = {}

for line in LOG_SAMPLE.strip().split("\n"):
    m = re.match(pattern, line)
    if m:
        ip, request = m.groups()
        if "/admin" in request or "/wp-login" in request:
            suspicious[ip] = suspicious.get(ip, 0) + 1

print("=== 可疑 IP ===")
for ip, n in suspicious.items():
    print(f"{ip}: 命中 {n} 次敏感路径")
```

**网安联系**：`/wp-login.php`（WordPress 后台）、`/admin` 是扫描器最爱探测的路径，命中就是强信号。

**自检**：能再加一个敏感路径 `/phpmyadmin` 的判断吗？

---

## 第 4 天：把分析封装成函数（可复用）

**软考任务**：做一套真题的上午选择题。

**今日实战**：新建 `day4.py`，把前几天的代码整理成函数：

```python
import re
from collections import Counter
from data import LOG_SAMPLE

def parse_log(text):
    """把日志文本解析成 (ip, request, status) 列表"""
    pattern = r'(\d+\.\d+\.\d+\.\d+).*?"(\w+ \S+).*?" (\d+)'
    results = []
    for line in text.strip().split("\n"):
        m = re.match(pattern, line)
        if m:
            results.append(m.groups())
    return results

def top_ips(records, n=3):
    """返回访问次数前 n 的 IP"""
    return Counter(r[0] for r in records).most_common(n)

records = parse_log(LOG_SAMPLE)
print("解析出", len(records), "条记录")
print("访问最多的 IP:", top_ips(records))
```

**网安联系**：真实工具都是这样组织的——解析函数、分析函数分开，方便复用和扩展。

**自检**：能写一个 `count_status(records)` 函数，统计各状态码数量吗？

---

## 第 5 天：把结果导出成文件（CSV）

**软考任务**：网络安全基础章节。

**今日实战**：新建 `day5.py`，把分析结果存成 CSV：

```python
import csv
from day4 import parse_log, top_ips
from data import LOG_SAMPLE

records = parse_log(LOG_SAMPLE)

with open("result.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["IP", "访问次数"])          # 表头
    for ip, n in top_ips(records):
        writer.writerow([ip, n])

print("已导出 result.csv，用 PyCharm 或 Excel 打开看看")
```

**新东西**：`encoding="utf-8-sig"` 让 Excel 打开中文不乱码。

**网安联系**：真实取证/分析工作，结果都要导出成报告或表格留档。

**自检**：能把可疑 IP 也导进同一个 CSV 吗？

---

## 第 6 天：用 pandas 做专业分析

**软考任务**：路由基础。

**今日实战**：新建 `day6.py`：

```python
import pandas as pd
from day4 import parse_log
from data import LOG_SAMPLE

records = parse_log(LOG_SAMPLE)
df = pd.DataFrame(records, columns=["IP", "请求", "状态码"])

print(df)
print("\n各状态码数量:")
print(df["状态码"].value_counts())
print("\n每个 IP 的访问次数:")
print(df["IP"].value_counts())
```

**网安联系**：pandas 是安全数据分析的主力工具，比手写循环快得多，真实工作天天用。

**自检**：能筛选出状态码是 404 的所有行吗？（提示：`df[df["状态码"] == "404"]`）

---

## 第 7 天：画一张攻击趋势图

**软考任务**：整理错题。

**今日实战**：新建 `day7.py`：

```python
import pandas as pd
import matplotlib.pyplot as plt
from day4 import parse_log
from data import LOG_SAMPLE

df = pd.DataFrame(parse_log(LOG_SAMPLE), columns=["IP", "请求", "状态码"])
counts = df["IP"].value_counts()

counts.plot(kind="bar", color="#d62728")
plt.title("IP 访问次数统计")
plt.xlabel("IP")
plt.ylabel("次数")
plt.tight_layout()
plt.savefig("ip_stats.png")
plt.show()
```

**注意**：matplotlib 中文可能显示成方块，问本地模型："matplotlib 中文显示成方框怎么解决？" 它会给你设置字体的方法。

**网安联系**：可视化是给领导/同事看分析报告的关键技能，一张图胜过千言。

**自检**：能改成画状态码分布的饼图吗？

---

## 第 8 天：综合项目 v1 —— 命令行版日志分析器

**软考任务**：做一套完整模拟题。

**今日实战**：新建 `analyzer.py`，把前面所有功能整合成一个工具：

```python
from day4 import parse_log, top_ips
from data import LOG_SAMPLE

def analyze(text):
    records = parse_log(text)
    print("=== 日志分析报告 ===")
    print(f"总记录数: {len(records)}")
    print("\n访问最多的 IP:")
    for ip, n in top_ips(records):
        print(f"  {ip}: {n} 次")
    
    suspicious = [r for r in records if "/admin" in r[1] or "wp-login" in r[1]]
    print(f"\n可疑请求: {len(suspicious)} 条")
    for ip, req, status in suspicious:
        print(f"  {ip} -> {req}")

if __name__ == "__main__":
    analyze(LOG_SAMPLE)
```

**网安联系**：这就是一个能用的小工具雏形了。加上 AI 分析就是完整产品。

**自检**：能运行它并读懂每一行输出吗？

---

## 第 9 天：调用你的本地大模型（LM Studio API）

**软考任务**：网络管理章节。

**前置**：打开 LM Studio → **Developer** 标签 → 点 **Start Server**，记下地址（一般是 `http://localhost:1234`）。

**今日实战**：新建 `ai_client.py`：

```python
import requests

def ask_local_ai(question):
    url = "http://localhost:1234/v1/chat/completions"
    payload = {
        "model": "local-model",   # LM Studio 里模型名随便写都行
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.3,
    }
    resp = requests.post(url, json=payload, timeout=60)
    return resp.json()["choices"][0]["message"]["content"]

if __name__ == "__main__":
    print(ask_local_ai("用一句话解释什么是 SQL 注入"))
```

**预期**：LM Studio 里能看到请求进来了，Console 打印模型的回答。

**排错**：连不上就问本地模型："LM Studio 开了 server 但 Python requests 连不上 localhost:1234，可能是什么原因？"

**网安联系**：你已经把本地 AI 接进代码了——这是 Agent 开发的第一步。

**自检**：能让它解释"什么是端口扫描"吗？

---

## 第 10 天：让 AI 帮你研判可疑 IP（项目核心）

**软考任务**：做 10 道案例题。

**今日实战**：新建 `day10.py`，把日志分析结果喂给本地模型，让它判断：

```python
from day4 import parse_log
from data import LOG_SAMPLE
from ai_client import ask_local_ai

records = parse_log(LOG_SAMPLE)
suspicious = [r for r in records if "/admin" in r[1] or "wp-login" in r[1]]

summary = "以下是可疑访问记录（IP, 请求, 状态码）：\n"
for ip, req, status in suspicious:
    summary += f"- {ip} {req} {status}\n"

question = f"""你是网络安全分析师。请分析这些日志：
{summary}
请回答：
1. 哪些 IP 最可疑？为什么？
2. 这可能是什么类型的攻击？
3. 给出 3 条处置建议。
用简洁的中文回答。"""

print(ask_local_ai(question))
```

**网安联系**：这就是 AI+网安的真实场景——让大模型帮你从海量日志里快速研判，你做最终决策。

**注意**：本地 9B 模型能力有限，回答可能不完美——**这正是你要练的：判断 AI 说得对不对**，别盲信。

**自检**：AI 的分析有哪里说得不对？你能指出来吗？

---

## 第 11 天：模块化整理 + Git 版本管理

**软考任务**：复习薄弱章节。

**今日实战**：
1. 整理项目结构（在 PyCharm 里拖动文件）：
   ```
   sec-log-analyzer/
   ├── analyzer.py        # 主程序
   ├── parser.py          # 解析（由 day4.py 改名）
   ├── ai_client.py       # AI 接口
   ├── data.py            # 样例日志
   └── README.md          # 项目说明（下一步写）
   ```
2. PyCharm 底部 **Terminal** 执行：
   ```bash
   git init
   git add .
   git commit -m "first version: log analyzer with local AI"
   ```

**网安联系**：版本管理是工程基本功，也是你 GitHub 作品集的基础。

**自检**：能说清楚每个文件是干什么的吗？

---

## 第 12 天：写项目 README（这是给招生老师/面试官看的）

**软考任务**：模拟题一套。

**今日实战**：新建 `README.md`，参考这个结构：

```markdown
# AI 日志研判工具

## 项目简介
用 Python + 本地大模型（Qwen3.5-9B）分析 Web 访问日志，
自动统计 IP、识别可疑请求，并调用本地 AI 生成研判报告。

## 功能
- 解析 Apache/Nginx 访问日志
- 统计 IP 访问频次、状态码分布
- 识别访问 /admin、/wp-login.php 等敏感路径的可疑 IP
- 调用本地 LM Studio 模型生成研判建议
- 导出 CSV 报表、可视化图表

## 使用方法
1. 安装依赖：pip install requests pandas matplotlib
2. 打开 LM Studio 并在 Developer 标签启动 Server
3. 运行：python analyzer.py

## 技术栈
Python · requests · pandas · matplotlib · LM Studio (Qwen3.5-9B)

## 法律声明
本项目仅用于合法学习，日志数据为模拟样例。
```

**网安联系**：README 写得好，项目价值翻倍。这是你 14 天成果的门面。

---

## 第 13 天：把项目推上 GitHub

**软考任务**：查漏补缺。

**今日实战**：
1. 去 GitHub 新建一个空仓库（比如 `sec-log-analyzer`），**不要**勾选 README。
2. 在 PyCharm Terminal 执行（换成你自己的地址和用户名）：
   ```bash
   git remote add origin https://github.com/你的用户名/sec-log-analyzer.git
   git push -u origin main
   ```
3. 打开仓库页面，确认文件都在、README 显示正常。

**网安联系**：GitHub 主页就是你的技术简历。这个项目是你第一个像样的作品。

**自检**：能给同学讲清楚这个项目做了什么吗？

---

## 第 14 天：验收 + 写下一段计划

**软考任务**：做一套真题检验。

**验收清单**（对照打勾）：
- [ ] 能解析日志、统计 IP、状态码
- [ ] 能用正则提取字段
- [ ] 能识别可疑 IP
- [ ] 能用 pandas 分析、matplotlib 画图
- [ ] 能调用本地 Qwen3.5-9B 并让它研判日志
- [ ] 项目结构清晰、有 README、已上 GitHub

**全打勾了**：**你已经有了第一个能写进简历的 AI+网安实战项目。**

**下一步**：回到 [学习路线](roadmap/00-overview.md)，按你的节奏推进软考和后续阶段。或者继续深入这个项目（比如接更多数据源、加规则引擎、做 Web 界面）。

**今天可以休息。** 14 天，你从"会基础语法"走到了"有完整实战项目"，值得。

---

## 最后三句

1. 只做当天，别焦虑后面。
2. 不会就问本地模型——这是你的超能力。
3. 语法你会，缺的是"用 Python 解决真实问题"的经验——这个项目就是补这个。

**现在开始第 0 天：打开 PyCharm，建项目，装库。** 那三个 `pip install` 敲完，你就上路了。

---

*制定：2026-11-25 · 实战项目配合 [每日打卡](checkin-log.md)，每做完一天打一次卡。*
