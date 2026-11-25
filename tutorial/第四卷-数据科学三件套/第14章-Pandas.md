# 第 14 章 Pandas：数据处理与分析

## 本章目标

- 理解 Pandas 的核心数据结构：Series 和 DataFrame
- 掌握数据的读取、查看、选择和过滤
- 掌握数据清洗（缺失值、重复值、类型转换）
- 掌握分组聚合、合并、透视表
- 用 Pandas 分析安全日志数据

Pandas 是数据科学的"瑞士军刀"。在 AI 项目里，80% 的时间花在数据准备上，而 Pandas 就是这个环节的主角。安全分析中的日志、告警、威胁情报，也全靠它处理。

---

## 14.1 Pandas 简介

### 14.1.1 安装和导入

```bash
pip install pandas
```

```python
import pandas as pd   # 约定俗成的别名
```

### 14.1.2 两大核心数据结构

| 结构 | 说明 | 类比 |
|------|------|------|
| Series | 一维带标签的数组 | Excel 的一列 |
| DataFrame | 二维表格，带行标签和列标签 | Excel 的一张表 |

---

## 14.2 Series：一维数据

### 14.2.1 创建 Series

```python
import pandas as pd

# 从列表创建
s = pd.Series([10, 20, 30, 40])
print(s)
# 0    10
# 1    20
# 2    30
# 3    40
# dtype: int64
```

左边是**索引**（index），右边是**值**（values）。

```python
# 自定义索引
s = pd.Series([10, 20, 30], index=["a", "b", "c"])
print(s)
# a    10
# b    20
# c    30

# 从字典创建
d = {"北京": 2171, "上海": 2487, "广州": 1873}
s = pd.Series(d)
```

### 14.2.2 访问数据

```python
s = pd.Series([10, 20, 30], index=["a", "b", "c"])

print(s["a"])      # 10  按索引标签
print(s[0])        # 10  按位置
print(s.values)    # [10 20 30]  所有值
print(s.index)     # Index(['a', 'b', 'c'])  所有索引
```

### 14.2.3 Series 运算

```python
s = pd.Series([1, 2, 3])
print(s + 10)         # 每个元素加 10
print(s * 2)
print(s[s > 1])       # 筛选
```

---

## 14.3 DataFrame：二维表格

### 14.3.1 创建 DataFrame

```python
import pandas as pd

# 从字典创建（最常用）
data = {
    "username": ["admin", "root", "guest", "alice"],
    "failed": [2, 5, 1, 0],
    "ip": ["192.168.1.1", "10.0.0.5", "8.8.8.8", "172.16.0.3"],
}
df = pd.DataFrame(data)
print(df)
```

输出：

```
  username  failed            ip
0    admin       2    192.168.1.1
1     root       5      10.0.0.5
2    guest       1       8.8.8.8
3    alice       0    172.16.0.3
```

### 14.3.2 读取数据（CSV / Excel）

```python
df = pd.read_csv("data.csv")          # 读 CSV
df = pd.read_excel("data.xlsx")       # 读 Excel（需 openpyxl）
```

> **注意**：中文 CSV 经常是 GBK 编码，读取时可能需要 `pd.read_csv("data.csv", encoding="gbk")`。UTF-8 是首选，遇到乱码再换。

### 14.3.3 查看数据

```python
df.head()        # 前 5 行
df.tail(3)       # 后 3 行
df.shape         # (行数, 列数)
df.info()        # 数据概况（列名、类型、缺失情况）
df.describe()    # 统计摘要（均值、标准差、最大最小值等）
df.columns       # 所有列名
df.dtypes        # 每列的数据类型
```

### 14.3.4 选择数据

```python
# 选择一列（返回 Series）
df["username"]

# 选择多列（返回 DataFrame）
df[["username", "failed"]]

# 按位置选择：iloc[行, 列]
df.iloc[0]           # 第 0 行
df.iloc[0:2, 1:3]    # 前 2 行，第 1-2 列

# 按标签选择：loc[行标签, 列标签]
df.loc[0, "username"]

# 选择单个值
df.at[0, "username"]   # 用标签
df.iat[0, 0]           # 用位置
```

> **记忆口诀**：`loc` 用**标签**，`iloc` 用**位置**（i = index/整数）。

### 14.3.5 过滤数据

```python
# 单个条件
df[df["failed"] >= 3]

# 多个条件（用 & |，每个条件加括号）
df[(df["failed"] >= 2) & (df["username"] != "guest")]

# 字符串包含
df[df["ip"].str.contains("192.168")]

# isin：判断是否在列表中
df[df["username"].isin(["admin", "root"])]

# query 方法（更简洁）
df.query("failed >= 3")
```

**安全场景**：找出失败次数 >= 3 的可疑用户

```python
suspects = df[df["failed"] >= 3]
print(suspects[["username", "ip", "failed"]])
```

### 14.3.6 修改数据

```python
# 添加新列
df["risk"] = df["failed"] >= 3

# 修改列值
df.loc[df["username"] == "root", "failed"] = 10

# 删除列
df.drop("risk", axis=1, inplace=True)

# 删除行
df.drop(0, axis=0, inplace=True)
```

> **注意**：`inplace=True` 表示原地修改。不加的话会返回新 DataFrame，原数据不变。

---

## 14.4 数据清洗

真实数据总是脏的：有缺失、有重复、格式乱。清洗是数据分析的第一步。

### 14.4.1 处理缺失值

```python
df.isnull()          # 判断哪些是缺失值
df.isnull().sum()    # 每列缺失值数量

# 删除缺失值
df.dropna()

# 填充缺失值
df.fillna(0)                    # 用 0 填充
df.fillna(df["col"].mean())     # 用均值填充（数值列常用）
df.fillna(method="ffill")       # 用前一个值填充
```

### 14.4.2 处理重复值

```python
df.duplicated()       # 判断哪些行是重复的
df.drop_duplicates()  # 删除重复行
```

### 14.4.3 数据类型转换

```python
df["failed"] = df["failed"].astype(int)
df["date"] = pd.to_datetime(df["date"])
```

### 14.4.4 重命名列

```python
df.rename(columns={"failed": "失败次数"}, inplace=True)
```

### 14.4.5 apply：自定义处理

```python
# 对某列每个元素应用函数
def classify(count):
    return "高危" if count >= 3 else "正常"

df["level"] = df["failed"].apply(classify)

# lambda 更简洁
df["level"] = df["failed"].apply(lambda x: "高危" if x >= 3 else "正常")
```

---

## 14.5 分组聚合与统计

### 14.5.1 groupby：分组

```python
data = {
    "user": ["admin", "admin", "root", "root", "guest"],
    "event": ["LOGIN", "FAILED", "LOGIN", "FAILED", "FAILED"],
    "count": [1, 2, 1, 5, 1],
}
df = pd.DataFrame(data)

# 按用户分组，求和
df.groupby("user")["count"].sum()
```

```
user
admin    3
guest    1
root     6
Name: count, dtype: int64
```

### 14.5.2 多种聚合

```python
df.groupby("user")["count"].agg(["sum", "mean", "max", "count"])
```

### 14.5.3 排序

```python
df.sort_values("count", ascending=False)   # 降序
df.sort_values(["user", "count"])          # 多列排序
```

### 14.5.4 透视表

```python
pd.pivot_table(df, values="count", index="user", columns="event", aggfunc="sum")
```

---

## 14.6 合并数据

```python
df1 = pd.DataFrame({"ip": ["1.1.1.1", "2.2.2.2"], "status": ["open", "closed"]})
df2 = pd.DataFrame({"ip": ["1.1.1.1", "2.2.2.2"], "port": [80, 443]})

# 内连接
pd.merge(df1, df2, on="ip")

# 左连接
pd.merge(df1, df2, on="ip", how="left")
```

类似 SQL 的 JOIN。

---

## 14.7 综合实战：安全日志分析

```python
import pandas as pd

# 模拟安全日志数据
data = {
    "timestamp": pd.date_range("2026-11-25", periods=10, freq="10min"),
    "username": ["admin", "root", "guest", "admin", "root", "alice", "root", "admin", "guest", "root"],
    "event": ["LOGIN_OK", "LOGIN_FAIL", "LOGIN_FAIL", "LOGIN_OK", "LOGIN_FAIL", 
              "LOGIN_OK", "LOGIN_FAIL", "LOGIN_FAIL", "LOGIN_OK", "LOGIN_FAIL"],
    "ip": ["192.168.1.10", "10.0.0.5", "8.8.8.8", "192.168.1.10", "10.0.0.5",
           "172.16.0.3", "10.0.0.5", "5.6.7.8", "8.8.8.8", "10.0.0.5"],
}
df = pd.DataFrame(data)

print("=== 数据概况 ===")
print(df.info())

print("\n=== 每个用户的登录失败次数 ===")
failed = df[df["event"] == "LOGIN_FAIL"]
failed_by_user = failed.groupby("username").size().sort_values(ascending=False)
print(failed_by_user)

print("\n=== 可疑用户（失败 >= 2 次）===")
suspects = failed_by_user[failed_by_user >= 2]
print(suspects)

print("\n=== 每个 IP 的失败次数 ===")
failed_by_ip = failed.groupby("ip").size().sort_values(ascending=False)
print(failed_by_ip)

print("\n=== 添加风险等级列 ===")
df["risk"] = df["event"].apply(lambda x: "高" if x == "LOGIN_FAIL" else "低")
print(df[["username", "event", "ip", "risk"]])

print("\n=== 保存分析结果 ===")
failed_by_user.to_csv("suspects.csv", encoding="utf-8")
print("已保存到 suspects.csv")
```

---

## 14.8 本章总结

| 知识点 | 核心内容 |
|--------|---------|
| Series | 一维带标签数组 |
| DataFrame | 二维表格 |
| 读取 | `read_csv`、`read_excel` |
| 查看 | `head`、`shape`、`info`、`describe` |
| 选择 | `df[col]`、`iloc`（位置）、`loc`（标签） |
| 过滤 | `df[条件]`、`isin`、`str.contains` |
| 清洗 | `dropna`、`fillna`、`drop_duplicates`、`astype` |
| 分组 | `groupby(...).agg([...])` |
| 排序 | `sort_values` |
| 合并 | `merge(on=...)` |
| apply | 自定义函数处理 |

---

## 本章练习

1. 读取一个 CSV 文件，查看其概况，统计每列缺失值。
2. 用 groupby 统计每个用户的失败次数，找出 > 3 次的用户。
3. 用 apply 给数据添加一列"风险等级"。
4. 用 merge 合并两个数据表。
5. 把分析结果保存为 CSV。

---

**下一章预告**：我们将学习 Matplotlib——数据可视化。一图胜千言，可视化能让你"看见"数据里的规律和异常，是分析和安全报告的关键技能。
