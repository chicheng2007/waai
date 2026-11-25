# 语法库大全 · 随查随用

> 这是一份**字典式语法速查手册**，不是从头到尾读的教程。
> 写代码卡住了、看到某段语法不懂了，按目录找到那个点，看一句话解释 + 一个能跑的最小例子，照着改就行。
> 覆盖 **Python 全套常用语法**（主线）+ **C/C++/Rust/Go 语法对照** + **常见报错速查**。

**导航**：[README](README.md) · [3 天语法急救包](SYNTAX-BOOTCAMP.md)（完全零基础先看这个）· [Python 主教程](tutorial/README.md) · [每日打卡](checkin-log.md)

---

## 怎么用这份手册

| 你的情况 | 去哪 |
|---|---|
| 一看 `for`/`split` 就懵，完全零基础 | 先看 [3 天语法急救包](SYNTAX-BOOTCAMP.md)，用"发牌/切香肠"讲懂 5 个零件 |
| 某个语法点忘了怎么写 | 查下面「第一部分 Python 语法」，按目录定位 |
| 想知道 IP 提取、日志解析这类常用代码怎么写 | 直接跳「网安常用代码片段」 |
| 报错了不知道什么意思 | 查「第三部分 常见报错速查」 |
| 想对比 C/C++/Rust/Go 的语法 | 查「第二部分 多语言语法对照」 |

> 每个示例都能直接粘进 PyCharm 跑。基础类型/变量赋值这些你会的，扫一眼确认即可，重点看标了 ⭐ 的。

---

# 第一部分 · Python 语法大全

## 1. 变量与数据类型

```python
name = "张三"        # 字符串 str
age = 20             # 整数 int
height = 1.75        # 浮点数 float
is_student = True    # 布尔 bool
nothing = None       # 空值

print(type(name))    # <class 'str'>  type() 看类型
```

**类型转换**：

```python
int("42")      # 字符串→整数：42
float("3.14")  # →浮点数：3.14
str(100)       # →字符串："100"
bool(0)        # →False（0/空 是 False，其他是 True）
```

---

## 2. 运算符

```python
# 算术
print(7 + 3, 7 - 3, 7 * 3, 7 / 3)   # 10 4 21 2.333...
print(7 // 3)   # 2   整除（只要整数部分）
print(7 % 3)    # 1   取余（求余数，判断奇偶常用）
print(2 ** 3)   # 8   幂运算

# 比较（结果是 True/False）
print(5 > 3, 5 == 3, 5 != 3)        # True False True

# 逻辑
print(True and False, True or False, not True)  # False True False

# 成员判断 ⭐（网安里判断字符串是否含某内容，天天用）
print("admin" in "/admin/login")     # True
print("sqlmap" in "Mozilla/5.0")     # False
```

---

## 3. 字符串 ⭐

```python
s = "  Hello,World  "

# 切片（从 0 开始，左闭右开）
print(s[0])        # 空格
print(s[2:7])      # Hello
print(s[-1])       # 最后一个字符

# 常用方法
print(s.strip())          # "Hello,World"  去掉首尾空白
print(s.replace("World", "Python"))  # 替换
print(s.lower(), s.upper())          # 大小写
print("a,b,c".split(","))            # ['a', 'b', 'c']  ⭐按分隔符切成列表
print("-".join(["a", "b"]))          # "a-b"  把列表拼成字符串
print("/admin".startswith("/ad"))    # True  判断开头

# f-string：往字符串里塞变量 ⭐
name, n = "/IP统计", 5
print(f"任务{name}完成，共{n}条")     # 任务/IP统计完成，共5条

# 转义与多行
print("第一行\n第二行")   # \n 换行
print('''多行
字符串''')
```

---

## 4. 列表 list ⭐

```python
ips = ["192.168.1.1", "10.0.0.5"]

ips.append("45.33.22.11")     # 末尾加一个
ips.insert(0, "1.1.1.1")      # 指定位置插入
ips.remove("1.1.1.1")         # 删掉某个值
last = ips.pop()              # 删掉并返回最后一个

print(len(ips))               # 长度
print(ips[0])                 # 第一个
print(ips[-1])                # 最后一个
print(ips[1:3])               # 切片
print("10.0.0.5" in ips)      # 判断在不在

nums = [3, 1, 2]
nums.sort()                   # 原地排序 → [1,2,3]
print(sorted(nums))           # 返回新的排序结果

# 列表推导式 ⭐（一行代码生成列表）
print([x * 2 for x in range(5)])          # [0,2,4,6,8]
print([x for x in range(10) if x % 2 == 0])  # [0,2,4,6,8] 带过滤
```

---

## 5. 元组 tuple 与 集合 set

```python
# 元组：不可变的列表，用 ()
t = (1, 2, 3)
print(t[0], len(t))

# 集合：自动去重、无序，用 {}
s = {1, 2, 2, 3}
print(s)                 # {1, 2, 3}  重复的 2 没了
print({1,2} | {2,3})     # {1,2,3} 并集
print({1,2} & {2,3})     # {2}    交集
print({1,2} - {2,3})     # {1}    差集
```

---

## 6. 字典 dict ⭐

```python
d = {"name": "张三", "age": 20}

print(d["name"])          # 张三  按键取值
print(d.get("age"))       # 20    get 更安全，键不存在不报错
print(d.get("sex", "未知"))  # 未知  第二个参数是默认值

d["sex"] = "男"           # 增/改
del d["age"]              # 删

# 遍历 ⭐
for key, value in d.items():
    print(f"{key} = {value}")

# 计数累加套路 ⭐（统计 IP 次数必用）
counts = {}
for ip in ["1.1.1.1", "2.2.2.2", "1.1.1.1"]:
    counts[ip] = counts.get(ip, 0) + 1
print(counts)   # {'1.1.1.1': 2, '2.2.2.2': 1}
```

---

## 7. 条件判断

```python
score = 85
if score >= 90:
    print("优秀")
elif score >= 60:      # else if 的缩写
    print("及格")
else:
    print("不及格")

# 三元表达式（一行的 if）
result = "及格" if score >= 60 else "不及格"
```

---

## 8. 循环 ⭐

```python
# for 循环：挨个处理 ⭐（急救包里的"发牌"）
for x in ["a", "b", "c"]:
    print(x)

# range()：生成数字序列
for i in range(5):        # 0,1,2,3,4
    print(i)
for i in range(1, 6):     # 1,2,3,4,5
    print(i)

# while 循环：条件成立就一直跑
n = 3
while n > 0:
    print(n)
    n -= 1

# break 跳出 / continue 跳过本次
for i in range(5):
    if i == 2: break       # 到 2 就结束整个循环
    if i == 1: continue    # 跳过 1

# enumerate ⭐（既要索引又要值）
for i, v in enumerate(["a", "b"]):
    print(i, v)   # 0 a / 1 b
```

---

## 9. 函数 ⭐

```python
# 定义与调用（急救包里的"菜谱"）
def greet(name):
    return f"你好, {name}"

print(greet("张三"))

# 默认参数
def power(x, n=2):
    return x ** n
print(power(3))      # 9
print(power(3, 3))   # 27

# 多返回值（实际是返回元组）
def min_max(nums):
    return min(nums), max(nums)
lo, hi = min_max([3, 1, 5])
print(lo, hi)   # 1 5

# lambda：匿名小函数
square = lambda x: x * x
print(square(4))   # 16

# 可变参数（了解即可）
def f(*args, **kwargs):
    print(args, kwargs)
f(1, 2, name="x")   # (1,2) {'name':'x'}
```

---

## 10. 文件操作 ⭐

```python
# with 写法：自动关闭文件，推荐 ⭐
with open("test.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n第二行")

with open("test.txt", "r", encoding="utf-8") as f:
    content = f.read()        # 读全部
    # 或逐行读（日志分析常用 ⭐）
    f.seek(0)                 # 回到开头
    for line in f:
        print(line.strip())
```

| 模式 | 含义 |
|---|---|
| `r` | 读（默认）|
| `w` | 写（清空原内容）|
| `a` | 追加 |
| `rb` / `wb` | 二进制（图片/zip）|

> 中文乱码：加 `encoding="utf-8"`；给 Excel 看用 `utf-8-sig`。

---

## 11. 异常处理

```python
try:
    n = int(input("输入数字:"))
    print(10 / n)
except ValueError:
    print("你输入的不是数字")
except ZeroDivisionError:
    print("除数不能为 0")
except Exception as e:      # 兜底：任何异常
    print("出错了:", e)
else:
    print("没出错时执行")
finally:
    print("无论如何都执行（清理用）")

# 主动抛异常
raise ValueError("数据格式不对")
```

---

## 12. 面向对象 class

```python
class Player:
    def __init__(self, name, hp):    # 构造方法
        self.name = name             # 属性
        self.hp = hp

    def attack(self, other):         # 方法
        other.hp -= 10

    def __str__(self):               # print 时的显示
        return f"{self.name}(HP:{self.hp})"

p1 = Player("甲", 100)
p2 = Player("乙", 100)
p1.attack(p2)
print(p2)   # 乙(HP:90)

# 继承
class VIP(Player):
    def attack(self, other):
        other.hp -= 20    # 重写父类方法
```

---

## 13. 模块与包

```python
import math                  # 导入整个模块
print(math.sqrt(16))         # 4.0

from math import sqrt        # 只导入一个函数
print(sqrt(9))               # 3.0

import pandas as pd          # 起别名（数据科学常用）
from collections import Counter   # 从模块导入类

# 主程序入口 ⭐（脚本被直接运行时才执行）
if __name__ == "__main__":
    print("我是主程序")
```

---

## 14. 正则表达式 re ⭐

```python
import re

text = '45.33.22.11 - - [25/Nov] "GET /admin HTTP/1.1" 404'

# search：找第一个匹配
m = re.search(r'\d+\.\d+\.\d+\.\d+', text)
print(m.group())   # 45.33.22.11

# findall：找出所有匹配，返回列表
print(re.findall(r'\d+', "a1b22c333"))   # ['1','22','333']

# match：从头匹配（急救包/实战计划里用这个解析日志）
m = re.match(r'(\S+).*?"(\w+ \S+)', text)
print(m.groups())   # ('45.33.22.11', 'GET /admin')

# sub：替换
print(re.sub(r'\d+', 'X', "ip=1.2.3.4"))   # ip=X.X.X.X
```

**常用元字符速查**：

| 符号 | 含义 | 符号 | 含义 |
|---|---|---|---|
| `\d` | 数字 0-9 | `\w` | 字母数字下划线 |
| `\s` | 空白字符 | `.` | 任意字符（换行除外）|
| `*` | 前一个重复 0+ 次 | `+` | 前一个重复 1+ 次 |
| `?` | 前一个重复 0 或 1 次 | `[abc]` | a/b/c 任一 |
| `^` | 开头 | `$` | 结尾 |
| `(...)` | 分组（提取用）| `.*?` | 非贪婪匹配 |

**常用模式**（直接改）：

```python
r'\d+\.\d+\.\d+\.\d+'      # IP 地址（简单版）
r'[\w.+-]+@[\w-]+\.[\w.]+' # 邮箱
r'([^ ]+) - - \[([^]]+)\] "(\w+ \S+)[^"]*" (\d+)'  # Apache 日志四字段
```

---

## 15. 常用内置函数速查表

| 函数 | 作用 | 例子 |
|---|---|---|
| `print()` | 输出 | `print("hi")` |
| `len()` | 长度 | `len([1,2])` → 2 |
| `type()` | 类型 | `type(1)` → int |
| `range()` | 数字序列 | `list(range(3))` → [0,1,2] |
| `enumerate()` | 带索引遍历 | 见第 8 节 |
| `zip()` | 并行遍历多个列表 | `list(zip([1,2],['a','b']))` |
| `sorted()` | 排序返回新列表 | `sorted([3,1])` → [1,3] |
| `sum()` / `max()` / `min()` | 求和/最大/最小 | `sum([1,2])` → 3 |
| `abs()` | 绝对值 | `abs(-5)` → 5 |
| `int()` / `float()` / `str()` / `bool()` | 类型转换 | 见第 1 节 |
| `list()` / `dict()` / `set()` / `tuple()` | 转对应类型 | `list("ab")` → ['a','b'] |
| `isinstance(x, int)` | 判断类型 | `isinstance(1,int)` → True |
| `open()` | 打开文件 | 见第 10 节 |
| `input()` | 读取输入 | `input("请输入:")` |

---

## 16. 网安常用代码片段 ⭐

```python
# ① 从日志行提取 IP（每行第一个词）
ip = line.split()[0]

# ② 统计 IP 次数 Top5
from collections import Counter
cnt = Counter(line.split()[0] for line in open("access.log", encoding="utf-8"))
print(cnt.most_common(5))

# ③ 批量读一个目录的所有日志文件
import glob
for path in glob.glob("datasets/access-logs/*.log"):
    with open(path, encoding="utf-8") as f:
        for line in f:
            pass    # 这里分析每一行

# ④ 判断敏感路径/攻击特征
if "/admin" in line or "/wp-login" in line:
    print("可疑:", line)
if "sqlmap" in line or "UNION SELECT" in line:
    print("攻击:", line)

# ⑤ 调本地 LM Studio 模型（你的 Qwen3.5-9B）
import requests
def ask(q):
    r = requests.post("http://localhost:1234/v1/chat/completions", json={
        "model": "local-model",
        "messages": [{"role": "user", "content": q}],
    }, timeout=60)
    return r.json()["choices"][0]["message"]["content"]
# print(ask("用一句话解释 SQL 注入"))
```

> 更多实战代码见 [14 天实战计划](START-HERE.md) 和 [练习数据集](datasets/README.md)。

---

# 第二部分 · 多语言语法对照（C/C++ · Rust · Go）

> 这是进阶内容，配合 [系统语言教程](tutorial/系统语言/README.md) 查。**大二阶段以 Python 为主，这部分扫一眼即可，别现在就埋头学。**

## 一句话定位

| 语言 | 定位 |
|---|---|
| Python | 快速上手 AI 与安全应用（主线）|
| C/C++ | 底层、逆向、漏洞、高性能计算——安全研究的内功 |
| Rust | 内存安全 + 高性能，写系统级安全工具 |
| Go | 简单 + 高并发 + 易部署，写云安全平台和高并发扫描器 |

## 核心语法对照表

| 语法 | Python | C | C++ | Rust | Go |
|---|---|---|---|---|---|
| 注释 | `# ...` | `//` `/* */` | `//` `/* */` | `//` | `//` |
| 变量 | `x = 5` | `int x = 5;` | `int x = 5;` | `let x = 5;` | `x := 5` / `var x int=5` |
| 常量 | 约定大写 | `const int X=5;` | `const int X=5;` | `const X: i32 = 5;` | `const X int = 5` |
| 输出 | `print(x)` | `printf("%d",x);` | `cout << x;` | `println!("{}",x);` | `fmt.Println(x)` |
| 条件 | `if x>0:` | `if(x>0){}` | `if(x>0){}` | `if x>0 {}` | `if x>0 {}` |
| 循环 | `for i in range(10):` | `for(int i=0;i<10;i++){}` | 同 C | `for i in 0..10 {}` | `for i:=0;i<10;i++{}` |
| 函数 | `def f(a): return a` | `int f(int a){return a;}` | 同 C + 重载 | `fn f(a:i32)->i32{a}` | `func f(a int) int {return a}` |
| 数组/列表 | `[1,2,3]` | `int a[]={1,2,3};` | `vector<int> a{1,2,3};` | `let a=[1,2,3];` | `a := []int{1,2,3}` |
| 字典/Map | `{"k":1}` | 无内置 | `map<string,int> m;` | `HashMap::new()` | `map[string]int{}` |
| 字符串 | `"hi"` | `char s[]="hi";` | `string s="hi";` | `String::from("hi")` | `"hi"` |
| 判等 | `==` | `==` | `==` | `==` | `==` |
| 取地址/引用 | 无 | `&x` | `&x` | `&x`（借用）| `&x` |

## 各自的"招牌特性"

```cpp
// C++：STL 容器 + 面向对象
#include <vector>
std::vector<int> v = {1, 2, 3};
v.push_back(4);
```

```rust
// Rust：所有权系统（编译期保证内存安全，无 GC）
let s = String::from("hi");
let r = &s;        // 借用，不转移所有权
```

```go
// Go：Goroutine 并发（写高并发扫描器/代理的利器）
go func() {
    fmt.Println("并发执行")
}()
```

> 学习顺序建议：Python 站稳 → C++ 保持手感/懂底层 → 大三后按方向选 Rust（底层/恶意代码）或 Go（安全开发/护网）。

---

# 第三部分 · 常见报错速查

看到红色报错**先看最后一行**，对照下表：

| 报错 | 意思 | 常见原因 / 怎么改 |
|---|---|---|
| `SyntaxError` | 语法错误 | 少了冒号 `:`、括号不配对、中文标点（改成英文）|
| `IndentationError` | 缩进错误 | 缩进空格数不一致；该缩进的没缩进 |
| `NameError` | 名字没定义 | 变量拼错了、忘了定义、忘了 `import` |
| `TypeError` | 类型不对 | 字符串和数字直接相加：`"a" + 1` → 改成 `str(1)` |
| `ValueError` | 值不对 | `int("abc")` 转不了；数字格式不对 |
| `IndexError` | 下标越界 | `list[10]` 但列表只有 3 个；数数从 0 开始 |
| `KeyError` | 字典没有这个键 | `d["x"]` 但没这个键 → 用 `d.get("x")` |
| `FileNotFoundError` | 文件找不到 | 路径写错、文件不在当前目录 |
| `ModuleNotFoundError` | 模块没装 | `pip install 模块名`；或名字拼错 |
| `AttributeError` | 对象没这个方法/属性 | 类型搞错了，比如对字符串用 `.append()` |
| `ZeroDivisionError` | 除以 0 | 除数可能为 0，先判断 |
| `ConnectionError` | 连接失败 | LM Studio 没开 Server / 地址端口不对 |

**万能排查法**：把报错最后一行原样粘给本地 Qwen3.5-9B：

```text
这段 Python 代码报错了，报错原文是：【粘贴最后一行红字】
代码是：【粘贴代码】
请告诉我：哪里错了、为什么、给我改好的完整代码。
```

---

## 最后

这份手册是**工具**，不是要背的。用到哪个查哪个，查着查着就记住了。

配合：
- 完全零基础 → [3 天语法急救包](SYNTAX-BOOTCAMP.md)
- 系统学习 → [Python 主教程](tutorial/README.md)
- 动手实战 → [14 天实战计划](START-HERE.md)
- 练手素材 → [250 份日志数据集](datasets/README.md)

---

*整理：2026-11-25 · 示例均可直接运行 · 有新的常用语法/报错想收录，告诉我补进来。*
