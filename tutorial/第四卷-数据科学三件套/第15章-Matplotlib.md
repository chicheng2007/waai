# 第 15 章 Matplotlib：数据可视化

## 本章目标

- 掌握 Matplotlib 的基本绘图流程
- 熟练绘制折线图、柱状图、散点图、直方图
- 掌握图表美化（标题、标签、图例、颜色）
- 绘制子图和组合图
- 用可视化展示安全/AI 数据

一图胜千言。在 AI 里，可视化帮你理解数据分布、观察训练过程、展示模型效果；在安全里，可视化帮你发现流量异常、展示攻击趋势。

---

## 15.1 Matplotlib 简介

### 15.1.1 安装和导入

```bash
pip install matplotlib
```

```python
import matplotlib.pyplot as plt   # 约定俗成
```

### 15.1.2 第一个图表

```python
import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [2, 4, 6, 8, 10]

plt.plot(x, y)
plt.show()
```

`plt.plot()` 画折线图，`plt.show()` 显示图表。

> **中文显示问题**：Matplotlib 默认不支持中文，会显示方块。解决方法：
> ```python
> plt.rcParams["font.sans-serif"] = ["SimHei"]      # Windows 用黑体
> plt.rcParams["axes.unicode_minus"] = False         # 正常显示负号
> ```
> macOS 用 `"Arial Unicode MS"`，Linux 用 `"WenQuanYi Micro Hei"`。教程后续例子默认已加这段配置。

---

## 15.2 常见图表类型

### 15.2.1 折线图（plot）

适合展示随时间变化的趋势：

```python
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

days = ["周一", "周二", "周三", "周四", "周五"]
attacks = [12, 18, 15, 25, 30]

plt.plot(days, attacks, marker="o", color="red", linewidth=2)
plt.title("每日攻击次数趋势")
plt.xlabel("日期")
plt.ylabel("攻击次数")
plt.grid(True, alpha=0.3)
plt.show()
```

参数说明：

- `marker="o"`：数据点显示圆点
- `color="red"`：线条颜色
- `linewidth=2`：线宽
- `plt.grid(True)`：显示网格

### 15.2.2 柱状图（bar）

适合比较不同类别的数值：

```python
users = ["admin", "root", "guest", "alice"]
fails = [2, 5, 1, 0]

plt.bar(users, fails, color=["green", "red", "orange", "blue"])
plt.title("用户登录失败次数")
plt.xlabel("用户")
plt.ylabel("失败次数")
plt.show()
```

**水平柱状图**：

```python
plt.barh(users, fails, color="steelblue")
plt.show()
```

### 15.2.3 散点图（scatter）

适合展示两个变量的关系、发现异常点：

```python
import numpy as np

np.random.seed(42)
traffic = np.random.normal(50, 10, 100)
anomalies = np.random.normal(300, 50, 5)

x = list(range(len(traffic))) + list(range(len(traffic), len(traffic)+5))
y = list(traffic) + list(anomalies)
colors = ["blue"] * len(traffic) + ["red"] * len(anomalies)

plt.scatter(x, y, c=colors, alpha=0.6)
plt.axhline(y=150, color="gray", linestyle="--", label="异常阈值")
plt.title("网络流量异常检测")
plt.xlabel("样本编号")
plt.ylabel("流量 (Mbps)")
plt.legend()
plt.show()
```

### 15.2.4 直方图（hist）

适合查看数据分布：

```python
data = np.random.normal(50, 10, 1000)

plt.hist(data, bins=30, color="skyblue", edgecolor="black", alpha=0.7)
plt.title("流量数据分布")
plt.xlabel("流量 (Mbps)")
plt.ylabel("频数")
plt.show()
```

`bins=30` 表示分成 30 个区间。直方图能让你一眼看出数据是否服从正态分布。

### 15.2.5 饼图（pie）

适合展示占比：

```python
labels = ["暴力破解", "扫描探测", "恶意软件", "钓鱼", "其他"]
sizes = [35, 25, 20, 12, 8]

plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
plt.title("攻击类型分布")
plt.axis("equal")   # 保证是圆
plt.show()
```

---

## 15.3 图表美化

### 15.3.1 样式设置

```python
plt.style.use("seaborn-v0_8-darkgrid")   # 使用内置样式
```

可用样式查看：

```python
print(plt.style.available)
```

### 15.3.2 图例、标题、标签

```python
plt.plot(x, y1, label="正常流量")
plt.plot(x, y2, label="异常流量")
plt.legend()          # 显示图例
plt.title("标题", fontsize=16)
plt.xlabel("X轴", fontsize=12)
plt.ylabel("Y轴", fontsize=12)
```

### 15.3.3 多个图形叠加

```python
plt.plot(x, y1, label="线1")
plt.scatter(x, y2, label="散点2")
plt.bar(x, y3, alpha=0.3, label="柱3")
plt.legend()
plt.show()
```

### 15.3.4 设置坐标范围

```python
plt.xlim(0, 10)
plt.ylim(0, 100)
```

---

## 15.4 子图（Subplot）

一张图里放多个图表：

```python
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 左上：折线图
axes[0, 0].plot([1, 2, 3], [1, 4, 9])
axes[0, 0].set_title("折线图")

# 右上：柱状图
axes[0, 1].bar(["A", "B", "C"], [3, 7, 5])
axes[0, 1].set_title("柱状图")

# 左下：散点图
axes[1, 0].scatter([1, 2, 3], [3, 2, 1])
axes[1, 0].set_title("散点图")

# 右下：饼图
axes[1, 1].pie([1, 2, 3], labels=["A", "B", "C"], autopct="%1.0f%%")
axes[1, 1].set_title("饼图")

plt.tight_layout()   # 自动调整子图间距
plt.show()
```

---

## 15.5 保存图表

```python
plt.savefig("chart.png", dpi=300, bbox_inches="tight")
```

- `dpi=300`：高分辨率
- `bbox_inches="tight"`：去掉多余空白

> **注意**：`savefig` 要放在 `plt.show()` **之前**，否则保存的是空白图。

---

## 15.6 综合实战：安全态势可视化仪表盘

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

np.random.seed(42)

# 生成模拟数据
days = [f"11-{d}" for d in range(20, 26)]
attacks = [45, 52, 38, 67, 89, 73]
blocked = [40, 48, 35, 60, 80, 70]

# 创建 2x2 仪表盘
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("网络安全态势感知仪表盘", fontsize=18, fontweight="bold")

# 1. 攻击趋势
axes[0, 0].plot(days, attacks, marker="o", color="red", label="攻击次数")
axes[0, 0].plot(days, blocked, marker="s", color="green", label="已阻断")
axes[0, 0].set_title("每日攻击与阻断趋势")
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].tick_params(axis="x", rotation=45)

# 2. 攻击类型分布
types = ["扫描", "暴力破解", "恶意软件", "钓鱼", "其他"]
counts = [120, 85, 60, 40, 30]
axes[0, 1].barh(types, counts, color="steelblue")
axes[0, 1].set_title("攻击类型统计")

# 3. 流量异常散点
traffic = np.concatenate([np.random.normal(50, 10, 95), np.random.normal(300, 40, 5)])
axes[1, 0].scatter(range(len(traffic)), traffic, 
                   c=["red" if t > 150 else "blue" for t in traffic], alpha=0.6)
axes[1, 0].axhline(150, color="gray", linestyle="--")
axes[1, 0].set_title("流量异常检测（红点为异常）")
axes[1, 0].set_xlabel("样本编号")
axes[1, 0].set_ylabel("流量 (Mbps)")

# 4. 攻击占比饼图
axes[1, 1].pie(counts, labels=types, autopct="%1.1f%%", startangle=90)
axes[1, 1].set_title("攻击类型占比")

plt.tight_layout()
plt.savefig("security_dashboard.png", dpi=150, bbox_inches="tight")
plt.show()
```

---

## 15.7 本章总结

| 图表类型 | 函数 | 适用场景 |
|---------|------|---------|
| 折线图 | `plt.plot` | 时间趋势 |
| 柱状图 | `plt.bar` / `barh` | 类别比较 |
| 散点图 | `plt.scatter` | 关系/异常点 |
| 直方图 | `plt.hist` | 数据分布 |
| 饼图 | `plt.pie` | 占比 |

关键技巧：

- 中文显示：`plt.rcParams["font.sans-serif"] = ["SimHei"]`
- 美化：`title`、`xlabel`、`ylabel`、`legend`、`grid`
- 子图：`plt.subplots(行, 列)`
- 保存：`savefig`（在 show 之前）

---

## 本章练习

1. 用折线图画出一组数据的趋势，并加上标题、标签、网格。
2. 用柱状图比较不同用户的失败次数。
3. 用散点图展示流量数据，用红色标出异常点。
4. 用直方图查看一组随机数的分布。
5. 创建一个 2x2 的子图，分别画四种不同的图。

---

**下一章预告**：我们将做一个综合项目——用三件套分析真实的安全日志数据，把前面学的 NumPy、Pandas、Matplotlib 串联起来。
