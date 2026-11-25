# 02 · 阶段 1：传统机器学习入门（软考后 1~2 个月）

> 这一阶段正式进入 AI。先传统 ML，不碰深度学习——原理简单、见效快、网安领域大量使用。

**导航**：[00 总览](00-overview.md) · [01 软考期](01-soft-exam.md) · **02 传统机器学习** · [03 深度学习](03-deep-learning.md) · [04 大模型/Agent](04-llm-agent.md) · [书单](../reference/booklist.md) · [链接](../reference/links.md)

---

## 5.1 为什么先学传统 ML，不直接上深度学习？
- 原理简单、训练快、可解释性强
- 在网安领域**大量使用**（恶意代码检测、流量分类主要用它）
- 打好这个概念基础，学深度学习会顺很多

---

## 5.2 学习步骤

**第 1 步：看课建立框架（2~3 周）**
- 吴恩达《Machine Learning》（Coursera，B站有搬运）
- 先只看前 5 周：线性回归、逻辑回归、代价函数、梯度下降、决策树、SVM
- 目标：理解"模型 = 从数据里学规律"

**第 2 步：sklearn 动手（2~3 周）**
- 安装：`pip install scikit-learn`
- 跟着官方文档 Getting Started 敲一遍鸢尾花分类
- 掌握标准流程：**加载数据 → 划分训练/测试集 → 选模型 → 训练 → 评估**

```python
# 最小可运行示例：感受一下机器学习流程
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

data = load_iris()
X_train, X_test, y_train, y_test = train_test_split(
    data.data, data.target, test_size=0.2, random_state=42
)
model = RandomForestClassifier()
model.fit(X_train, y_train)
print("准确率:", accuracy_score(y_test, model.predict(X_test)))
```

**第 3 步：网安小项目（2~3 周）**
- 数据集：Kaggle 搜 `KDD Cup 1999`（经典网络入侵检测数据集）
- 任务：用随机森林 / 决策树判断一条网络连接是不是攻击
- 目标：跑通全流程，写出一个简单的分析报告
- 注意：这时候你的软考网络知识就派上用场了——理解每条连接记录的特征含义

---

## 5.3 阶段 1 自测清单
- [ ] 能解释训练集 / 测试集为什么要分开
- [ ] 能解释过拟合是什么、怎么避免
- [ ] 能独立用 sklearn 跑通一个分类任务
- [ ] 完成了 KDD99 入侵检测小项目

---

*本阶段完事后，进入 [03 深度学习](03-deep-learning.md)。*
