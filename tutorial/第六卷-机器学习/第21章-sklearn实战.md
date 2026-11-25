# 第 21 章 scikit-learn 实战

## 本章目标

- 掌握 scikit-learn 的基本使用流程
- 学会做分类任务（恶意软件检测）
- 学会做异常检测（ Isolation Forest）
- 学会做聚类（日志分组）
- 掌握模型评估和特征工程
- 用真实风格的数据做完整项目

scikit-learn（简称 sklearn）是 Python 最流行的机器学习库，接口统一、文档优秀，是入门机器学习的最佳选择。

---

## 21.1 scikit-learn 简介

### 21.1.1 安装

```bash
pip install scikit-learn
```

### 21.1.2 统一的 API 设计

sklearn 的所有模型都遵循同样的接口，学会一个就会用全部：

```python
from sklearn.某个模型 import 模型类

model = 模型类(参数)    # 1. 创建模型
model.fit(X, y)         # 2. 训练（监督学习）
predictions = model.predict(X_new)  # 3. 预测
```

- `fit(X, y)`：训练模型，X 是特征，y 是标签
- `predict(X)`：对新数据做预测
- `score(X, y)`：评估模型表现

这种一致性让你可以轻松切换不同算法做对比。

### 21.1.3 数据格式

sklearn 要求输入是二维的 NumPy 数组或 DataFrame：

- `X`：形状 (样本数, 特征数)
- `y`：形状 (样本数,)，一维标签

---

## 21.2 实战一：恶意软件检测（分类）

### 21.2.1 准备数据

我们使用 sklearn 自带的鸢尾花数据集来演示（稍后换成安全场景风格的数据）。先掌握流程：

```python
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

iris = load_iris()
X = iris.data    # 特征（150个样本，4个特征）
y = iris.target  # 标签（3个类别）

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")
```

`train_test_split` 把数据随机分成 80% 训练、20% 测试，`random_state` 保证结果可复现。

### 21.2.2 训练模型

```python
from sklearn.tree import DecisionTreeClassifier

# 创建决策树分类器
model = DecisionTreeClassifier(random_state=42)

# 训练
model.fit(X_train, y_train)

# 预测
predictions = model.predict(X_test)

# 评估
accuracy = model.score(X_test, y_test)
print(f"准确率: {accuracy:.3f}")
```

就这么简单！三步：创建、训练、评估。

### 21.2.3 安全场景：模拟恶意软件检测

```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

np.random.seed(42)

# 模拟恶意软件数据集
# 特征: [文件大小(KB), 字节熵值, 敏感API调用数, 是否加壳(0/1), 数字签名(0/1)]
n_samples = 1000

# 正常软件特征
normal = np.column_stack([
    np.random.normal(5000, 2000, 800),   # 文件大小
    np.random.normal(5.5, 0.5, 800),     # 熵值较低
    np.random.poisson(2, 800),           # 敏感 API 少
    np.random.binomial(1, 0.1, 800),     # 很少加壳
    np.random.binomial(1, 0.7, 800),     # 多有签名
])

# 恶意软件特征
malicious = np.column_stack([
    np.random.normal(2000, 800, 200),    # 文件较小
    np.random.normal(7.5, 0.3, 200),     # 熵值高（加壳/加密）
    np.random.poisson(15, 200),          # 敏感 API 多
    np.random.binomial(1, 0.8, 200),     # 多数加壳
    np.random.binomial(1, 0.05, 200),    # 很少签名
])

# 合并
X = np.vstack([normal, malicious])
y = np.array([0]*800 + [1]*200)   # 0=正常, 1=恶意

# 划分
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 训练随机森林
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 预测和评估
predictions = model.predict(X_test)
print("=== 混淆矩阵 ===")
print(confusion_matrix(y_test, predictions))
print("\n=== 详细报告 ===")
print(classification_report(y_test, predictions, target_names=["正常", "恶意"]))
```

**观察输出**：随机森林能很准确地识别恶意软件。这就是机器学习在安全中的典型应用——**用文件的统计特征训练模型，自动识别未知恶意样本**，比传统特征库更能应对新变种。

### 21.2.4 特征重要性

```python
features = ["文件大小", "字节熵值", "敏感API数", "是否加壳", "数字签名"]
importances = model.feature_importances_

for name, imp in sorted(zip(features, importances), key=lambda x: -x[1]):
    print(f"{name}: {imp:.3f}")
```

输出会告诉你哪些特征对判断最重要（通常是"字节熵值"和"敏感API数"）。这能帮你理解模型的判断依据，也能指导特征工程。

---

## 21.3 实战二：异常流量检测（无监督学习）

异常检测不需要标签，用 Isolation Forest（孤立森林）算法：

```python
import numpy as np
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt

np.random.seed(42)

# 模拟网络流量特征: [请求速率, 数据包大小, 连接时长]
normal = np.column_stack([
    np.random.normal(10, 3, 950),    # 正常请求速率低
    np.random.normal(500, 100, 950),
    np.random.normal(5, 2, 950),
])
attack = np.column_stack([
    np.random.normal(200, 50, 50),   # 攻击请求速率极高
    np.random.normal(100, 30, 50),
    np.random.normal(0.5, 0.2, 50),
])
X = np.vstack([normal, attack])

# Isolation Forest：异常检测算法
model = IsolationForest(contamination=0.05, random_state=42)  # contamination=预期异常比例
model.fit(X)

# 预测：-1 表示异常，1 表示正常
predictions = model.predict(X)
anomalies = predictions == -1

print(f"检测到的异常数: {anomalies.sum()}（实际 50 个）")
print(f"准确率: {(anomalies == (np.arange(1000) >= 950)).mean():.3f}")
```

> **安全价值**：Isolation Forest 能发现"从未见过的攻击模式"，因为它只学习"正常是什么样的"，偏离正常的就是异常。这比基于特征库的检测方法更擅长发现零日攻击。

---

## 21.4 实战三：日志聚类（无监督学习）

```python
from sklearn.cluster import KMeans
import numpy as np

np.random.seed(42)

# 模拟三类日志的行为特征: [请求频率, 响应码404比例, 路径多样性]
cluster1 = np.random.normal([5, 0.1, 3], [1, 0.05, 0.5], (100, 3))   # 正常用户
cluster2 = np.random.normal([50, 0.7, 10], [10, 0.1, 2], (50, 3))    # 扫描器
cluster3 = np.random.normal([2, 0.05, 1], [0.5, 0.02, 0.3], (80, 3)) # 静态爬虫

X = np.vstack([cluster1, cluster2, cluster3])

# KMeans 聚类（分成 3 类）
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
labels = kmeans.fit_predict(X)

# 查看每类的中心
print("聚类中心:")
print(kmeans.cluster_centers_)

# 统计每类数量
import pandas as pd
print(pd.Series(labels).value_counts())
```

聚类帮你把大量日志自动分组，发现"扫描器"这类行为模式，无需人工标注。

---

## 21.5 特征工程与预处理

### 21.5.1 标准化

很多算法对特征尺度敏感，需要标准化：

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)   # 转成均值0、标准差1
```

> **重要**：`fit` 只能在训练集上做，然后用同一个 scaler 转换测试集，避免数据泄露：
> ```python
> scaler.fit(X_train)
> X_train_scaled = scaler.transform(X_train)
> X_test_scaled = scaler.transform(X_test)
> ```

### 21.5.2 处理文本特征

安全数据里常有文本（文件路径、URL），需要转成数字：

```python
from sklearn.feature_extraction.text import TfidfVectorizer

paths = ["/admin", "/index.html", "/wp-admin", "/.env", ...]
vectorizer = TfidfVectorizer()
X_text = vectorizer.fit_transform(paths)   # 转成数值矩阵
```

### 21.5.3 Pipeline：把流程串起来

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("classifier", SVC()),
])

pipeline.fit(X_train, y_train)
print(pipeline.score(X_test, y_test))
```

Pipeline 让预处理和模型训练成为一个整体，代码更整洁，也避免数据泄露。

---

## 21.6 常用算法速查

| 算法 | sklearn 类 | 适用任务 | 特点 |
|------|-----------|---------|------|
| 线性回归 | `LinearRegression` | 回归 | 简单、可解释 |
| 逻辑回归 | `LogisticRegression` | 分类 | 简单、输出概率 |
| 决策树 | `DecisionTreeClassifier` | 分类 | 可解释、可视化 |
| 随机森林 | `RandomForestClassifier` | 分类 | 准确、抗过拟合 |
| 支持向量机 | `SVC` | 分类 | 适合小样本 |
| K近邻 | `KNeighborsClassifier` | 分类 | 简单、惰性学习 |
| KMeans | `KMeans` | 聚类 | 经典聚类 |
| 孤立森林 | `IsolationForest` | 异常检测 | 高效、无需标签 |

> **选择建议**：不确定用什么时，先试**随机森林**（分类）和 **Isolation Forest**（异常检测），它们通常表现不错且不容易出错。

---

## 21.7 本章总结

| 知识点 | 核心内容 |
|--------|---------|
| sklearn 流程 | `fit` 训练 → `predict` 预测 → `score` 评估 |
| 数据划分 | `train_test_split`，通常 8:2 |
| 分类 | RandomForestClassifier；恶意软件检测 |
| 异常检测 | IsolationForest；异常流量检测（无需标签） |
| 聚类 | KMeans；日志分组 |
| 评估 | `confusion_matrix`、`classification_report`、特征重要性 |
| 预处理 | StandardScaler、TfidfVectorizer、Pipeline |

---

## 本章练习

1. 用决策树替换随机森林，重新做恶意软件检测，对比效果。
2. 用 Isolation Forest 检测第 16 章的访问日志数据中的异常 IP。
3. 用 KMeans 对你的日志数据聚类，观察每类中心的含义。
4. 用 Pipeline 把标准化 + 分类模型串起来。
5. 思考：为什么异常检测在安全领域比分类更实用？（提示：考虑标签获取的难度）

---

**下一章预告**：我们将深入学习模型评估、调优和部署——让你的模型从"能用"变成"好用"，并学会把它部署成真正的应用。
