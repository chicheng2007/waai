# 第 24 章 PyTorch 入门

## 本章目标

- 理解张量（Tensor）
- 掌握自动微分
- 用 PyTorch 搭建和训练神经网络
- 训练一个恶意软件分类器
- 理解数据加载和训练循环

PyTorch 是目前最流行的深度学习框架，动态图、易用、Pythonic。这一章带你完成第一个真正的深度学习训练。

---

## 24.1 安装 PyTorch

```bash
# CPU 版本（先学这个就够）
pip install torch torchvision

# GPU 版本需要去官网 https://pytorch.org 根据你的 CUDA 版本选择命令
```

验证：

```python
import torch
print(torch.__version__)
print(torch.cuda.is_available())   # 是否有 GPU
```

---

## 24.2 张量（Tensor）

Tensor 就是可以跑在 GPU 上的 NumPy 数组，API 几乎一样：

```python
import torch

# 创建张量
x = torch.tensor([1, 2, 3])
print(x)

# 各种创建方式
torch.zeros(2, 3)
torch.ones(2, 3)
torch.randn(2, 3)        # 标准正态分布随机
torch.arange(0, 10, 2)   # [0,2,4,6,8]

# 运算（和 NumPy 类似）
a = torch.tensor([1, 2, 3])
b = torch.tensor([4, 5, 6])
print(a + b)   # [5 7 9]
print(a @ b)   # 点积 32

# 和 NumPy 互转
np_array = a.numpy()
tensor = torch.from_numpy(np_array)
```

**GPU 加速**：

```python
if torch.cuda.is_available():
    x = x.cuda()   # 把数据移到 GPU
```

---

## 24.3 自动微分（Autograd）

PyTorch 最强大的功能：自动计算梯度。

```python
import torch

# 创建一个需要追踪梯度的张量
x = torch.tensor(3.0, requires_grad=True)

# 定义计算
y = x ** 2

# 反向传播（自动算梯度）
y.backward()

# 查看梯度 dy/dx = 2x = 6
print(x.grad)   # tensor(6.)
```

你不需要手动推导导数，PyTorch 自动算！这就是深度学习框架的核心价值。

---

## 24.4 搭建神经网络

### 24.4.1 用 nn.Module 定义网络

```python
import torch
import torch.nn as nn

class MalwareNet(nn.Module):
    def __init__(self):
        super().__init__()
        # 定义层
        self.layer1 = nn.Linear(5, 16)   # 输入5个特征 → 隐藏层16个神经元
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(16, 8)
        self.layer3 = nn.Linear(8, 2)    # 输出2个类别（正常/恶意）
    
    def forward(self, x):
        # 定义前向传播
        x = self.relu(self.layer1(x))
        x = self.relu(self.layer2(x))
        x = self.layer3(x)
        return x

model = MalwareNet()
print(model)
```

### 24.4.2 训练要素

训练神经网络需要三样东西：

```python
import torch.optim as optim

# 1. 损失函数：衡量预测和真实的差距
criterion = nn.CrossEntropyLoss()

# 2. 优化器：更新权重（Adam 是默认好选择）
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 3. 数据
# X_train, y_train（Tensor 格式）
```

---

## 24.5 完整实战：训练恶意软件分类器

```python
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

np.random.seed(42)
torch.manual_seed(42)

# ===== 1. 准备数据 =====
# 特征: [文件大小, 熵值, 敏感API数, 是否加壳, 签名]
normal = np.column_stack([
    np.random.normal(5000, 2000, 800),
    np.random.normal(5.5, 0.5, 800),
    np.random.poisson(2, 800),
    np.random.binomial(1, 0.1, 800),
    np.random.binomial(1, 0.7, 800),
])
malicious = np.column_stack([
    np.random.normal(2000, 800, 200),
    np.random.normal(7.5, 0.3, 200),
    np.random.poisson(15, 200),
    np.random.binomial(1, 0.8, 200),
    np.random.binomial(1, 0.05, 200),
])
X = np.vstack([normal, malicious]).astype(np.float32)
y = np.array([0]*800 + [1]*200)

# 标准化
X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-8)

# 转成 Tensor
X_tensor = torch.from_numpy(X)
y_tensor = torch.from_numpy(y).long()

# 划分训练/测试
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X_tensor, y_tensor, test_size=0.2, random_state=42
)

# ===== 2. 定义模型 =====
class MalwareNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(5, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 2),
        )
    
    def forward(self, x):
        return self.net(x)

model = MalwareNet()

# ===== 3. 训练配置 =====
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

# ===== 4. 训练循环 =====
epochs = 100
batch_size = 32

for epoch in range(epochs):
    # 简化的批量训练（打乱数据）
    indices = torch.randperm(len(X_train))
    for i in range(0, len(indices), batch_size):
        batch_idx = indices[i:i+batch_size]
        batch_X = X_train[batch_idx]
        batch_y = y_train[batch_idx]
        
        # 前向
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        
        # 反向 + 更新
        optimizer.zero_grad()   # 清空上次的梯度
        loss.backward()         # 反向传播
        optimizer.step()        # 更新参数
    
    if (epoch + 1) % 20 == 0:
        print(f"第 {epoch+1} 轮, 损失: {loss.item():.4f}")

# ===== 5. 评估 =====
model.eval()   # 切换到评估模式
with torch.no_grad():   # 不计算梯度
    outputs = model(X_test)
    _, predicted = torch.max(outputs, 1)
    accuracy = (predicted == y_test).float().mean()
    print(f"\n测试集准确率: {accuracy.item()*100:.2f}%")
```

**观察训练过程**：损失不断下降，准确率达到 95%+。你刚刚用 PyTorch 训练了一个真正的神经网络！

### 训练循环的关键步骤（记住这个模式）

```
for epoch in range(epochs):
    for batch in data:
        1. outputs = model(X)        # 前向
        2. loss = criterion(...)     # 算损失
        3. optimizer.zero_grad()     # 清梯度
        4. loss.backward()           # 反向
        5. optimizer.step()          # 更新
```

所有 PyTorch 训练都是这个套路。

---

## 24.6 DataLoader：更规范的数据加载

上面的例子手动分批比较简陋，实际项目用 DataLoader：

```python
from torch.utils.data import TensorDataset, DataLoader

# 创建数据集
dataset = TensorDataset(X_tensor, y_tensor)

# 数据加载器（自动分批、打乱）
loader = DataLoader(dataset, batch_size=32, shuffle=True)

# 训练时直接遍历
for batch_X, batch_y in loader:
    outputs = model(batch_X)
    loss = criterion(outputs, batch_y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
```

DataLoader 还能并行加载数据、处理大数据集，是专业做法。

---

## 24.7 模型的保存与加载

```python
# 保存模型参数
torch.save(model.state_dict(), "malware_net.pth")

# 加载
model = MalwareNet()
model.load_state_dict(torch.load("malware_net.pth"))
model.eval()
```

---

## 24.8 本章总结

| 知识点 | 核心内容 |
|--------|---------|
| Tensor | GPU 版 NumPy；`torch.tensor`、运算、与 NumPy 互转 |
| 自动微分 | `requires_grad=True` + `backward()` 自动算梯度 |
| nn.Module | 定义网络；`nn.Sequential` 堆叠层；`forward` 前向 |
| 损失函数 | `CrossEntropyLoss`（分类）、`MSELoss`（回归） |
| 优化器 | `optim.Adam`（默认好选择） |
| 训练循环 | 前向→损失→清零梯度→反向→更新（五步） |
| 评估 | `model.eval()` + `torch.no_grad()` |
| DataLoader | 规范的数据加载和分批 |

---

## 本章练习

1. 把隐藏层改成 32 个神经元，观察准确率变化。
2. 尝试不同的学习率（0.001、0.01、0.1），观察训练稳定性。
3. 用 DataLoader 重写训练循环。
4. 保存训练好的模型，重新加载后做预测。
5. 思考：`optimizer.zero_grad()` 为什么要调用？不调用会怎样？

---

**下一章预告**：我们将进入大模型应用开发——学习 RAG（检索增强生成）和 Agent，让大模型结合你的私有数据（如安全知识库），构建智能安全助手。
