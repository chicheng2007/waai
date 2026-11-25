# 3 天语法急救包 · 读懂代码就够了

> **给谁**：只会 `print`、变量赋值，一看 `for` / `.split()` 就懵的人。
> **目标**：不学完整语法书，只搞定**读代码必备的 5 个零件**。3 天后，你能读懂 [START-HERE.md](../START-HERE.md) 里 14 天计划的大部分代码。
> **怎么用**：每天照着把代码**粘进 PyCharm 跑一遍**，对着"预期输出"认每个零件。别只看，一定要跑。

**导航**：[README](../README.md) · [回到实战计划 START-HERE](../START-HERE.md) · [每日打卡](../checkin-log.md)

---

## 为什么有这份

你之前说："这种语法不懂，只会最简单的。"

那就别硬上实战了——**读不懂代码，做实战就是抄，抄了也不进步**。

好消息是：你不需要从头学一遍语法。Python 语法很多，但**读懂那 14 天计划，只需要 5 个零件**：

| 零件 | 生活比喻 | 出现频率 |
|---|---|---|
| ① 字符串切开 `.split()` / `.strip()` | 切香肠 / 削边角 | 天天见 |
| ② 列表 `[...]` | 装东西的盘子 | 天天见 |
| ③ `for ... in ...` 循环 | 发牌 | 天天见 |
| ④ 字典 `{...}` | 通讯录 | 常见 |
| ⑤ 函数 `def` | 菜谱 | 常见 |

外加半个：**f-string**（往字符串里塞变量），见到就懂。

这 5 个零件，**每个都能用一句生活的话讲明白**。下面开始。

---

## 准备工作（2 分钟，只做一次）

在 PyCharm 里新建一个文件 `data.py`，把这段粘进去保存。后面 3 天都用它，它就是我们的"样例日志"。

```python
# 这是一小段 Web 访问日志，每行是一条访问记录
LOG_SAMPLE = '''192.168.1.100 - - [25/Nov/2026:12:00:01 +0800] "GET /index.html HTTP/1.1" 200 1234
10.0.0.5 - - [25/Nov/2026:12:00:03 +0800] "POST /login HTTP/1.1" 401 512
192.168.1.100 - - [25/Nov/2026:12:00:05 +0800] "GET /admin HTTP/1.1" 404 231
45.33.22.11 - - [25/Nov/2026:12:00:07 +0800] "GET /wp-login.php HTTP/1.1" 404 178'''
```

> 注：三引号 `'''...'''` 就是"一整块字符串"，里面可以随便换行。比普通引号 `''` 适合装多行文字。

---

# 第 1 天：字符串切开 + 列表 + for 循环

**今天解决你最卡的那行**：`for line in LOG_SAMPLE.strip().split("\n"):`

学完今天，这行你能逐字讲出来。

---

## 零件①：`.split()` = 切香肠

一段文字像一根长香肠，`\n`（换行符）是香肠上预先切好的刀口。`.split("\n")` 就是"**沿着换行把所有刀口切开，切成一段一段**"。

新建一个文件 `day1_a.py`，跑：

```python
from data import LOG_SAMPLE

text = "苹果,香蕉,橘子"
fruits = text.split(",")          # 按逗号切开
print(fruits)
print(type(fruits))               # 看看切开后变成什么类型
```

**预期输出**：

```python
['苹果', '香蕉', '橘子']
<class 'list'>
```

**看懂了吗**：
- `split(",")` 里的 `","` 是"刀"——按逗号切
- 切开后从一串文字变成 `[...]` 包起来的一堆东西，这个叫**列表（list）**
- `type()` 就是"看看它是啥类型"

放回你的日志：`.split("\n")` 就是"按换行切"，把 4 行日志切成 4 段。

---

## 零件②：列表 `[...]` = 装东西的盘子

`['苹果', '香蕉', '橘子']` 就是一个列表——一个盘子，按顺序装着好几个东西。

三个必会动作，跑 `day1_b.py`：

```python
fruits = ['苹果', '香蕉', '橘子']

print(len(fruits))        # 1. 盘子里有几个？(长度)
print(fruits[0])          # 2. 拿第 1 个（注意：从 0 开始数！）
print(fruits[1])          #    拿第 2 个
print(fruits[-1])         # 3. 拿最后 1 个（-1 表示倒数第一）
```

**预期输出**：

```python
3
苹果
香蕉
橘子
```

**关键点**：Python 数数**从 0 开始**。`fruits[0]` 是第一个，不是 `fruits[1]`。这是新手最常懵的地方，记住就行。

---

## 零件③：`for ... in ...` = 发牌

有一摞牌（列表）。`for x in 列表:` 就是"**从这摞牌里一张一张发出来，每次发到的那张暂时叫 x，然后做事**"。

跑 `day1_c.py`：

```python
fruits = ['苹果', '香蕉', '橘子']

for f in fruits:            # 把 fruits 里的东西挨个发出来，每次叫 f
    print("我拿到了:", f)   # 缩进的这行 = 每发一张就执行一次
```

**预期输出**：

```python
我拿到了: 苹果
我拿到了: 香蕉
我拿到了: 橘子
```

**看懂结构**：

```python
for 变量 in 列表:
    这里缩进的代码，列表里有几个就跑几次
```

- `for` 后面跟一个你起的名字（这里叫 `f`）
- `in` 后面是列表
- **冒号 `:` + 下一行缩进**——缩进里的代码就是"每次要做的事"
- 列表有 3 个东西，就打印 3 次

---

## 追加：`.strip()` = 削边角

整块日志的首尾常有多余的空格、换行，`.strip()` 把它们削掉。

```python
s = "  你好   "
print(repr(s))            # repr 能看到隐藏的空格
print(repr(s.strip()))    # 首尾空格没了
```

---

## 现在，回到你最卡的那行

```python
for line in LOG_SAMPLE.strip().split("\n"):
```

从左到右读：

| 片段 | 意思 |
|---|---|
| `LOG_SAMPLE` | 一整块日志文字 |
| `.strip()` | 削掉首尾多余空白 |
| `.split("\n")` | 按换行切成 4 段 → 变成一个**列表**（4 行 = 4 个元素）|
| `for line in 列表:` | 把 4 行**挨个发出来**，每次那行叫 `line`，执行缩进里的代码 |

**整句翻译**："把日志按换行切成一行一行，然后一行一行拿出来，每次管当前这行叫 `line`。"

跑 `day1_d.py` 亲眼确认：

```python
from data import LOG_SAMPLE

lines = LOG_SAMPLE.strip().split("\n")   # 先切开，存到 lines
print("切成了几行:", len(lines))

for line in lines:                        # 再一行行发牌
    print("当前行:", line[:30])           # line[:30] 只显示前 30 个字符
```

**动手改一改**：把 `print("当前行:", line[:30])` 改成 `print("IP是:", line.split()[0])`，看看会发生什么——这就是 [START-HERE 第 1 天](../START-HERE.md) 提取 IP 的核心代码。

---

## 第 1 天打卡

- [ ] 我能说清 `split` 是按什么切
- [ ] 我知道列表从 0 开始数
- [ ] 我能解释 `for line in ...` 每次在干什么
- [ ] 我跑通了 `day1_d.py`

在 [checkin-log.md](../checkin-log.md) 追加一行：`语法急救 第1天`。

---

# 第 2 天：字典 + f-string

## 零件④：字典 `{...}` = 通讯录

列表是"按顺序排号"（第 0 个、第 1 个）。字典是"**按名字查**"——像一个通讯录，存"名字 → 电话"。

统计"每个 IP 访问了几次"，用字典最合适：键是 IP，值是次数。

跑 `day2_a.py`：

```python
visits = {}                      # 空字典，用 {} 表示

visits["192.168.1.100"] = 2      # 存：这个 IP 访问 2 次
visits["10.0.0.5"] = 1

print(visits)                            # 打印整个字典
print(visits["192.168.1.100"])           # 按 IP 查次数
```

**预期输出**：

```python
{'192.168.1.100': 2, '10.0.0.5': 1}
2
```

**结构是**：

```python
字典名 = { "键": 值, "键": 值 }
字典名["键"]          # 查
字典名["键"] =  newValue   # 改/存
```

---

### 字典的招牌动作：计数累加

这行你会反复见到：

```python
counts[ip] = counts.get(ip, 0) + 1
```

拆开讲（跑 `day2_b.py`）：

```python
counts = {}

ip = "192.168.1.100"
counts[ip] = counts.get(ip, 0) + 1   # 第一次：没这个 IP，get 返回 0，0+1=1
counts[ip] = counts.get(ip, 0) + 1   # 第二次：已有 1，1+1=2
counts[ip] = counts.get(ip, 0) + 1   # 第三次：已有 2，2+1=3

print(counts)
```

**预期输出**：

```python
{'192.168.1.100': 3}
```

**`.get(ip, 0)` 的意思**："查 ip 的值；如果没有这个 ip，就当它是 0"。这样第一次也不会报错。整行就是"**这个 IP 的次数加 1**"。

> 这就是 [START-HERE 第 1 天](../START-HERE.md) 那个 `Counter` 计数的手写版，本质一样。

---

## 零件⑤（半个）：f-string = 往字符串里塞变量

```python
name = "张三"
age = 20
print(f"我叫{name}, 今年{age}岁")     # 注意引号前的 f
```

**预期输出**：

```python
我叫张三, 今年20岁
```

**用法**：字符串前加 `f`，然后用 `{变量名}` 把变量塞进去。比 `"我叫" + name + ...` 拼接方便得多。你会在几乎每天的代码里见到它。

---

## 第 2 天实战：统计日志里每个 IP 的次数

把今天零件全用上，跑 `day2_c.py`：

```python
from data import LOG_SAMPLE

counts = {}                                   # 空字典，准备装 次数

for line in LOG_SAMPLE.strip().split("\n"):   # 一行行发牌（第1天学的）
    ip = line.split()[0]                      # 这行的第一个词就是 IP
    counts[ip] = counts.get(ip, 0) + 1        # 这个 IP 次数 +1（今天学的）

for ip, n in counts.items():                  # items() 把字典拆成一对对
    print(f"{ip} 访问了 {n} 次")              # f-string 塞变量（今天学的）
```

**预期输出**：

```python
192.168.1.100 访问了 2 次
10.0.0.5 访问了 1 次
45.33.22.11 访问了 1 次
```

**新东西**：`for ip, n in counts.items()` —— `items()` 把字典变成一对对的"(键, 值)"，`ip` 接键、`n` 接值。也是发牌，一次发两个。

看懂这段，你就已经写出了 [START-HERE 第 1 天](../START-HERE.md) 的核心功能。

---

## 第 2 天打卡

- [ ] 我知道字典是"名字→值"，用 `["键"]` 查
- [ ] 我理解 `counts[ip] = counts.get(ip, 0) + 1` 是计数加一
- [ ] 我会用 f-string 往字符串塞变量
- [ ] 我跑通了 `day2_c.py`，看到了 IP 统计结果

在 [checkin-log.md](../checkin-log.md) 追加一行：`语法急救 第2天`。

---

# 第 3 天：函数 + 读懂真代码

## 零件⑥：函数 `def` = 菜谱

函数就是"**给一段代码起个名字，以后喊名字就能反复用**"。像菜谱：写一次步骤，以后每次想做这道菜，照着做就行，不用重写。

跑 `day3_a.py`：

```python
def say_hello(name):          # def = 定义函数；name 是"参数"（原材料）
    print(f"你好, {name}!")   # 缩进里 = 这个函数要做的事

say_hello("张三")             # 调用：喊名字，把"张三"递进去
say_hello("李四")             # 再调用一次，换个名字
```

**预期输出**：

```python
你好, 张三!
你好, 李四!
```

**结构**：

```python
def 函数名(参数):
    要做的事（缩进）

函数名(具体的值)      # 调用
```

**函数还能"返回"结果**——用 `return` 把处理好的东西交出来：

```python
def add(a, b):
    return a + b          # 把结果交出来

result = add(3, 5)        # 用变量接住返回的值
print(result)             # 8
```

`result = add(3, 5)` 的意思："执行 add 函数，把 return 出来的结果存进 result"。

---

## 第 3 天实战：把统计逻辑做成函数

跑 `day3_b.py`：

```python
from data import LOG_SAMPLE

def count_ips(text):                          # 定义函数：统计 IP 次数
    counts = {}
    for line in text.strip().split("\n"):
        ip = line.split()[0]
        counts[ip] = counts.get(ip, 0) + 1
    return counts                             # 把统计结果交出来

result = count_ips(LOG_SAMPLE)                # 调用函数，接住结果
print(result)
```

**预期输出**：

```python
{'192.168.1.100': 2, '10.0.0.5': 1, '45.33.22.11': 1}
```

这就是 [START-HERE 第 4 天](../START-HERE.md)"封装成函数"的样子。**你已经会了。**

---

## 终极检验：读一段计划里的真代码

下面是 [START-HERE 第 3 天](../START-HERE.md) 的真实代码片段。现在试着**逐行讲出来**（讲不出来就回看对应零件）：

```python
import re
from data import LOG_SAMPLE

pattern = r'(\d+\.\d+\.\d+\.\d+).*?"(\w+ \S+)'
suspicious = {}                                  # ① 空字典：装可疑 IP

for line in LOG_SAMPLE.strip().split("\n"):      # ② 一行行发牌
    m = re.match(pattern, line)                  # ③ 正则提取（第1天计划会讲，这里先当黑盒）
    if m:                                        # ④ 如果提取到了
        ip, request = m.groups()                 #    拆出 IP 和请求
        if "/admin" in request or "/wp-login" in request:   # ⑤ 如果是敏感路径
            suspicious[ip] = suspicious.get(ip, 0) + 1      # ⑥ 计数加一

for ip, n in suspicious.items():                 # ⑦ 字典拆成一对对发牌
    print(f"{ip}: 命中 {n} 次敏感路径")          # ⑧ f-string 打印
```

**对照答案**（先自己讲，再看）：

| 行 | 用的零件 |
|---|---|
| ② | 第 1 天：`split` + `for` |
| ①③ | 正则，暂时当它是"按规则提取字段"的黑盒 |
| ④ | `if` 判断——这个你会（"如果...就..."） |
| ⑤⑥ | 第 2 天：字典计数 |
| ⑦⑧ | 第 2 天：`items()` + f-string |

**能不能读懂？** 如果能讲出七八成，恭喜——**你已经具备读实战代码的能力了**，可以回去 [START-HERE](../START-HERE.md) 正式开始 14 天计划。遇到没见过的语法（比如正则），照样用生活比喻的思路问本地模型："用切香肠/发牌这种打比方，讲讲这行在干嘛。"

---

## 3 天打卡总清单

- [ ] 第 1 天：能讲清 `for line in ...strip().split("\n")` 每一行
- [ ] 第 2 天：能手写 IP 计数（字典 + f-string）
- [ ] 第 3 天：能定义函数、能读懂终极检验代码
- [ ] 3 天代码全部亲手跑过（不是只看）

**全部打勾 → 回到 [START-HERE.md](../START-HERE.md) 开始第 0 天。** 那时候你会发现代码不再是天书。

---

## 给你的一句话

你不是学不会，是之前没人把 `for` 讲成"发牌"、把 `split` 讲成"切香肠"。**Python 的语法就这几块积木，认全了，剩下的都是搭法。** 3 天，把积木认熟，够了。

---

*制定：2026-11-25 · 配合 [每日打卡](../checkin-log.md) 使用，每天学完打一次卡。*
