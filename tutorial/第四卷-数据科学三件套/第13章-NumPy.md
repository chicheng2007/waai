# 第 13 章 NumPy：科学计算的基石

## 本章目标

- 理解 NumPy 是什么、为什么比 Python 列表快
- 掌握 ndarray 的创建、属性、索引和切片
- 掌握数组运算（向量化）
- 理解广播机制
- 掌握常用函数（统计、随机数、线性代数）
- 用 NumPy 处理安全/AI 数据

NumPy 是整个 AI 生态的基石。Pandas、Matplotlib、scikit-learn、PyTorch 全都建立在它之上。可以说：**不懂 NumPy，就等于不懂 AI 的数据是怎么被处理的**。

---

## 13.1 为什么需要 NumPy

### 13.1.1 Python 列表的问题

```python
# 两个列表对应元素相加
a = [1, 2, 3, 4, 5]
b = [6, 7, 8, 9, 10]

# 用列表得这样写
result = []
for i in range(len(a)):
    result.append(a[i] + b[i])
print(result)   # [7, 9, 11, 13, 15]
```

问题：

1. **代码啰嗦**：简单加法要写循环
2. **速度慢**：Python 循环很慢，因为每个元素都要经过解释器

### 13.1.2 NumPy 的解决方案

```python
import numpy as np

a = np.array([1, 2, 3, 4, 5])
b = np.array([6, 7, 8, 9, 10])

result = a + b   # 一行搞定，而且是底层 C 语言循环，快几十倍
print(result)    # [ 7  9 11 13 15]
```

NumPy 的两大优势：

1. **简洁**：`a + b` 就是对应元素相加，代码像数学公式一样直观
2. **快速**：底层用 C 语言和连续内存存储，比 Python 循环快 10–100 倍

> **性能对比直观感受**：对 100 万个数求和，Python 循环约 50 毫秒，NumPy 约 0.3 毫秒，快 100 多倍。数据在 AI 里动辄几百万、几十亿个数，没有 NumPy 根本玩不转。

### 13.1.3 安装 NumPy

```bash
pip install numpy
```

（如果装了 Anaconda，NumPy 已经有了。）

约定：几乎所有人都用 `import numpy as np` 这个别名。

---

## 13.2 ndarray：核心数据结构

### 13.2.1 创建数组

```python
import numpy as np

# 从列表创建
a = np.array([1, 2, 3, 4, 5])
print(a)   # [1 2 3 4 5]

# 二维数组（矩阵）
m = np.array([[1, 2, 3], [4, 5, 6]])
print(m)
# [[1 2 3]
#  [4 5 6]]

# 指定数据类型
f = np.array([1, 2, 3], dtype=np.float64)
print(f)   # [1. 2. 3.]
```

### 13.2.2 快速创建特殊数组

```python
np.zeros(5)          # [0. 0. 0. 0. 0.]  全 0 数组
np.zeros((3, 4))     # 3行4列的全 0 矩阵
np.ones((2, 3))      # 全 1 矩阵
np.empty((2, 2))     # 空数组（未初始化，值是随机的）
np.full((2, 3), 7)   # 全部填充为 7

np.arange(0, 10, 2)  # [0 2 4 6 8]  类似 range
np.linspace(0, 1, 5) # [0. 0.25 0.5 0.75 1.]  均匀分成 5 份

np.eye(3)            # 3x3 单位矩阵（对角线是 1）
np.random.rand(3, 2) # 3x2 的随机数组（0-1 之间）
```

### 13.2.3 数组的属性

```python
m = np.array([[1, 2, 3], [4, 5, 6]])

print(m.ndim)    # 2  维度（ndim = number of dimensions）
print(m.shape)   # (2, 3)  形状：2 行 3 列
print(m.size)    # 6  元素总数
print(m.dtype)   # int64  数据类型
print(m.itemsize)# 8  每个元素占的字节数
```

**shape 是最重要的属性**，后面所有操作都跟它打交道。

### 13.2.4  reshape：改变形状

```python
a = np.arange(12)       # [0 1 2 ... 11]
print(a.shape)          # (12,)

b = a.reshape(3, 4)     # 变成 3 行 4 列
print(b)
# [[ 0  1  2  3]
#  [ 4  5  6  7]
#  [ 8  9 10 11]]

c = a.reshape(2, 3, 2)  # 三维数组
```

> **注意**：`reshape` 返回的是**视图**（view），和原数组共享数据。修改 `b` 会影响 `a`。如果想要独立副本，用 `.copy()`。

---

## 13.3 索引和切片

### 13.3.1 一维数组

和列表类似：

```python
a = np.array([10, 20, 30, 40, 50])
print(a[0])      # 10
print(a[-1])     # 50
print(a[1:4])    # [20 30 40]
print(a[::-1])   # [50 40 30 20 10]
```

### 13.3.2 二维数组

用逗号分隔维度：`数组[行, 列]`

```python
m = np.array([[1, 2, 3],
              [4, 5, 6],
              [7, 8, 9]])

print(m[0, 0])    # 1  第 0 行第 0 列
print(m[1, 2])    # 6  第 1 行第 2 列
print(m[0, :])    # [1 2 3]  第 0 行所有列
print(m[:, 0])    # [1 4 7]  第 0 列所有行
print(m[0:2, 1:]) # 前两行，从第1列开始
# [[2 3]
#  [5 6]]
```

**记忆**：逗号前是行，逗号后是列；冒号 `:` 表示"全部"。

### 13.3.3 布尔索引（超实用）

用条件表达式筛选元素：

```python
a = np.array([10, 25, 30, 45, 60])
mask = a > 30
print(mask)         # [False False False  True  True]
print(a[mask])      # [45 60]  只保留大于 30 的

# 更简洁的写法
print(a[a > 30])    # [45 60]

# 组合条件
print(a[(a > 20) & (a < 50)])   # [25 30 45]
```

> **注意**：组合条件要用 `&`（与）、`|`（或），不能用 `and`、`or`（那是给标量用的）。每个条件要加括号。

**安全场景应用**：筛选异常 IP（假设用数值表示）

```python
traffic = np.array([10, 50, 2000, 30, 1500, 45])
# 找出流量超过 1000 的异常值
anomalies = traffic[traffic > 1000]
print("异常流量:", anomalies)   # [2000 1500]
```

---

## 13.4 数组运算（向量化）

### 13.4.1 元素级运算

```python
a = np.array([1, 2, 3])
b = np.array([10, 20, 30])

print(a + b)   # [11 22 33]
print(a - b)   # [-9 -18 -27]
print(a * b)   # [10 40 90]  对应元素相乘（不是矩阵乘法！）
print(a / b)   # [0.1 0.1 0.1]
print(a ** 2)  # [1 4 9]

# 和标量运算
print(a + 5)   # [6 7 8]
print(a * 2)   # [2 4 6]
```

### 13.4.2 广播（Broadcasting）

广播是 NumPy 最优雅的特性：不同形状的数组也能运算。

```python
a = np.array([[1, 2, 3],
              [4, 5, 6]])

b = np.array([10, 20, 30])   # 一维，形状 (3,)

print(a + b)
# [[11 22 33]
#  [14 25 36]]
```

`b` 被"广播"成了 2 行，和 `a` 的每一行分别相加。

**广播规则**：从后往前对比维度，要么相等，要么其中一个为 1。

```python
# 列向量广播
col = np.array([[1], [2], [3]])  # 形状 (3, 1)
print(a + col)  # a 是 (2,3)，col 广播成 (2,3)
```

### 13.4.3 矩阵乘法

```python
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

# 元素级乘法
print(A * B)
# [[ 5 12]
#  [21 32]]

# 矩阵乘法（用 @ 或 np.dot）
print(A @ B)
# [[19 22]
#  [43 50]]

# 等价写法
print(np.dot(A, B))
```

> **关键区别**：`*` 是对应元素相乘，`@` 才是线性代数里的矩阵乘法。这在 AI（神经网络）里至关重要——神经网络的核心就是矩阵乘法。

### 13.4.4 聚合函数

```python
a = np.array([1, 2, 3, 4, 5])

print(a.sum())      # 15  求和
print(a.mean())     # 3.0  平均值
print(a.max())      # 5
print(a.min())      # 1
print(a.std())      # 1.414  标准差
print(a.var())      # 2.0  方差
print(a.argmax())   # 4  最大值的索引（分类任务常用！）
print(a.argmin())   # 0

# 按轴聚合（二维数组）
m = np.array([[1, 2, 3], [4, 5, 6]])
print(m.sum(axis=0))  # [5 7 9]  按列求和
print(m.sum(axis=1))  # [6 15]  按行求和
print(m.mean(axis=0)) # [2.5 3.5 4.5]
```

> **AI 小贴士**：`argmax()` 在分类任务里用来取概率最大的类别，你会经常用到它。

---

## 13.5 常用模块

### 13.5.1 随机数 np.random

```python
np.random.seed(42)   # 设置随机种子，保证结果可复现（重要！）

np.random.rand(3)          # 3 个 0-1 的随机数
np.random.randn(3)         # 3 个标准正态分布的随机数（AI 初始化权重常用）
np.random.randint(0, 100, 5)  # 5 个 0-100 的整数
np.random.choice([1, 2, 3], size=5)  # 从列表里随机选 5 个
np.random.shuffle(arr)     # 打乱数组（原地）
```

> **注意**：AI 实验中一定要设置随机种子，否则每次结果都不一样，无法对比和复现。

### 13.5.2 线性代数 np.linalg

```python
A = np.array([[3, 1], [1, 2]])

print(np.linalg.inv(A))     # 逆矩阵
print(np.linalg.det(A))     # 行列式
print(np.linalg.norm(A))    # 范数（向量长度，AI 里衡量距离/损失）

# 求解线性方程组 Ax = b
b = np.array([9, 8])
x = np.linalg.solve(A, b)
print(x)   # [2. 3.]
```

### 13.5.3 其他实用函数

```python
np.unique(arr)      # 去重并排序
np.sort(arr)        # 排序（返回新数组）
np.concatenate([a, b])  # 拼接数组
np.where(cond, x, y)    # 条件选择（向量化的 if-else）
np.isnan(arr)       # 判断是否是 NaN（缺失值）

# 保存和加载
np.save("data.npy", arr)
arr = np.load("data.npy")
```

---

## 13.6 综合实战：用 NumPy 做异常流量检测

```python
import numpy as np

np.random.seed(42)

# 模拟 1000 条网络流量数据（Mbps）
# 正常流量：均值 50，标准差 10
normal_traffic = np.random.normal(50, 10, 980)
# 异常流量（攻击）：均值 300
attack_traffic = np.random.normal(300, 50, 20)

# 合并数据
traffic = np.concatenate([normal_traffic, attack_traffic])

# 用 3σ 原则检测异常（超过均值+3倍标准差的视为异常）
mean = traffic.mean()
std = traffic.std()
threshold = mean + 3 * std

print(f"流量均值: {mean:.2f} Mbps")
print(f"标准差: {std:.2f}")
print(f"异常阈值: {threshold:.2f} Mbps")

# 找出异常
anomalies = traffic[traffic > threshold]
print(f"\n检测到 {len(anomalies)} 条异常流量:")
print(f"异常值范围: {anomalies.min():.2f} - {anomalies.max():.2f} Mbps")

# 统计
normal_count = len(traffic[traffic <= threshold])
print(f"正常流量: {normal_count} 条")
print(f"异常比例: {len(anomalies)/len(traffic)*100:.2f}%")
```

> **这就是 Machine Learning 异常检测的雏形**！用统计方法设定阈值，超过阈值的判为异常。第六卷你会学到更强大的方法。

---

## 13.7 本章总结

| 知识点 | 核心内容 |
|--------|---------|
| ndarray | N 维数组，底层连续存储，快 |
| 创建 | `np.array`、`zeros`、`ones`、`arange`、`linspace`、`random` |
| 属性 | `shape`（形状）、`ndim`（维度）、`dtype`（类型） |
| 索引切片 | `数组[行, 列]`；布尔索引 `a[a>30]` |
| 向量化 | `a+b` 元素级运算；`*` 元素乘，`@` 矩阵乘 |
| 广播 | 不同形状数组自动对齐运算 |
| 聚合 | `sum/mean/max/std/argmax`；`axis=0` 按列，`axis=1` 按行 |
| 随机数 | `seed` 保证可复现；`randn` 正态分布 |
| 线性代数 | `inv/det/norm/solve` |

---

## 本章练习

1. 创建一个 5x5 的随机数组，找出最大值的位置和最小值的位置。
2. 用广播计算一个 3x4 数组每列的平均值。
3. 用布尔索引筛选出一个数组中所有偶数。
4. 用 `@` 计算两个 3x3 矩阵的乘法，并与 `*` 的结果对比。
5. 用 3σ 原则检测一组数据中的异常值（参考综合实战）。

---

**下一章预告**：我们将学习 Pandas——数据处理与分析的利器。如果说 NumPy 处理的是"数组"，那 Pandas 处理的是"表格"，更接近我们日常接触的数据。
