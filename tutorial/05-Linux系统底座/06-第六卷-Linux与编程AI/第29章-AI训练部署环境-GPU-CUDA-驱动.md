# 第 29 章 AI 训练部署环境：GPU / CUDA / 驱动

## 本章目标

读完这一章，你将能够：

- 理解 GPU 为什么是 AI 训练的核心
- 理解 NVIDIA 驱动、CUDA、cuDNN 的关系
- 在 Linux 上安装和验证 GPU 环境
- 用 nvidia-smi 监控 GPU
- 配置 Python AI 框架（PyTorch/TensorFlow）的 GPU 支持
- 理解容器化 GPU 环境（nvidia-docker）
- 了解 CPU/其他 GPU 方案与常见坑

---

## 29.1 为什么 AI 需要 GPU

### 29.1.1 CPU vs GPU

| 对比 | CPU | GPU |
|------|-----|-----|
| 核心数 | 几个到几十个（复杂） | 数千个（简单） |
| 擅长 | 复杂逻辑、串行任务 | 大规模并行计算 |
| AI 用途 | 数据预处理、控制 | 矩阵运算（训练/推理） |

神经网络训练的本质是海量矩阵乘法——这正好是 GPU 擅长的并行任务。所以训练一个大模型，GPU 比 CPU 快几十到几百倍。

> **小白问**：推理一定要 GPU 吗？
>
> 不一定。小模型推理 CPU 就够；大模型推理通常用 GPU（或专用芯片）。训练几乎必须 GPU。

### 29.1.2 软件栈层次

```
┌─────────────────────────────┐
│  应用层：PyTorch / TensorFlow │
├─────────────────────────────┤
│  库层：cuDNN、BLAS           │  深度学习加速库
├─────────────────────────────┤
│  计算平台：CUDA              │  GPU 并行计算框架
├─────────────────────────────┤
│  驱动层：NVIDIA Driver       │  硬件驱动
├─────────────────────────────┤
│  硬件：NVIDIA GPU            │
└─────────────────────────────┘
```

要装的东西：驱动 → CUDA →（cuDNN）→ AI 框架。**顺序不能乱，版本要匹配**。

---

## 29.2 安装 NVIDIA 驱动

### 29.2.1 准备工作

```bash
# 查看是否有 NVIDIA 显卡
lspci | grep -i nvidia

# 查看当前驱动（可能没有）
nvidia-smi
```

### 29.2.2 安装驱动（Ubuntu）

```bash
# 方法一：图形界面"附加驱动"（最简单）
# 系统设置 → 软件和更新 → 附加驱动 → 选择 NVIDIA 驱动

# 方法二：命令行
sudo ubuntu-drivers autoinstall
sudo reboot
```

验证：

```bash
nvidia-smi
```

输出显示显卡型号、驱动版本、显存使用——说明驱动装好了。

> ⚠️ **常见坑**：
> 1. 装驱动后重启黑屏——可能是 Secure Boot 阻断了驱动模块，需要在 BIOS 关闭 Secure Boot 或给模块签名。
> 2. 双显卡（Intel + NVIDIA）笔记本需要用 prime 或 `prime-select nvidia` 切换。
> 3. 云服务器通常用"GPU 实例"镜像，驱动已预装，不要重复装。

---

## 29.3 CUDA Toolkit

### 29.3.1 安装

CUDA 是 NVIDIA 的并行计算平台。PyTorch 等框架自带 CUDA 运行时，通常**不用单独装完整 CUDA Toolkit**——只需驱动即可。但如果要用 nvcc 编译 CUDA 代码，需要装 Toolkit。

```bash
# 从 NVIDIA 官网下载对应版本的 CUDA Toolkit（.deb 或 runfile）
# 或 apt（版本可能较旧）
sudo apt install nvidia-cuda-toolkit

nvcc --version          # 验证
```

### 29.3.2 版本匹配

关键原则：

- **驱动版本 ≥ CUDA 版本要求的最低驱动**（向下兼容：`nvidia-smi` 显示的 CUDA Version 是驱动支持的最高版本）
- **AI 框架版本 ↔ CUDA 版本**：PyTorch 不同版本绑定不同 CUDA（如 cu118、cu121）

查看驱动支持的最高 CUDA：

```bash
nvidia-smi    # 右上角 "CUDA Version: xx.x"
```

> **大白话**：`nvidia-smi` 显示的 CUDA 版本是"驱动最高支持到这"，不代表你装了那个版本的 CUDA。真正给框架用的是框架自带的 CUDA 运行时。

---

## 29.4 cuDNN

cuDNN 是深度学习加速库（卷积、RNN 等优化）。PyTorch/TensorFlow 的 pip 包通常已内置对应 cuDNN，**一般不用单独装**。手动安装需从 NVIDIA 官网下载（需账号），把文件复制到 CUDA 目录。

---

## 29.5 配置 Python AI 框架

### 29.5.1 PyTorch（推荐）

```bash
# 创建虚拟环境
python3 -m venv ai-env
source ai-env/bin/activate

# 从 PyTorch 官网选对应 CUDA 版本安装（以 cu121 为例）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

验证 GPU 可用：

```python
import torch
print(torch.__version__)
print(torch.cuda.is_available())      # True 表示 GPU 可用
print(torch.cuda.get_device_name(0))  # 显卡型号
```

### 29.5.2 TensorFlow

```bash
pip install tensorflow[and-cuda]      # TF 2.10+ Linux 支持 GPU
```

验证：

```python
import tensorflow as tf
print(tf.config.list_physical_devices('GPU'))
```

### 29.5.3 常见坑

| 问题 | 原因 | 解决 |
|------|------|------|
| `cuda.is_available()` 是 False | 驱动/版本不匹配、装了 CPU 版 PyTorch | 重装对应 CUDA 版的 torch |
| 显存不足 OOM | batch 太大/模型太大 | 减小 batch、混合精度、梯度累积 |
| 多卡识别不全 | 环境变量、PCIe 问题 | 设置 CUDA_VISIBLE_DEVICES |
| 驱动装了但 nvidia-smi 无输出 | 驱动没加载 | reboot、检查 dmesg |

---

## 29.6 用 nvidia-smi 监控 GPU

```bash
nvidia-smi                          # 当前状态
nvidia-smi -l 1                     # 每秒刷新
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv
```

监控要点：

- **GPU 利用率**：如果长期很低，说明 GPU 在等数据（IO/预处理瓶颈，呼应第 28 章）
- **显存占用**：看是否接近上限（OOM 风险）
- **温度**：过高会降频（80°C+ 要注意散热）

> **实战关联**：AI 训练慢时，先看 `nvidia-smi`。如果 GPU 利用率忽高忽低，多半是数据加载瓶颈（用更多 DataLoader workers、SSD、预加载）；如果显存满，减 batch 或用混合精度。

---

## 29.7 容器化 GPU 环境

要在 Docker 容器里用 GPU，需要 NVIDIA Container Toolkit：

```bash
# 安装
sudo apt install nvidia-container-toolkit
sudo systemctl restart docker

# 运行带 GPU 的容器
docker run --gpus all -it pytorch/pytorch:latest

# 指定 GPU
docker run --gpus '"device=0"' -it pytorch/pytorch:latest
```

这样容器里就能用 `nvidia-smi` 和 CUDA 了。AI 服务部署常用这种方式。

> **呼应第 24 章**：容器共享宿主内核，GPU 通过工具包把设备暴露给容器。这是 AI 工程化的标准做法。

---

## 29.8 其他方案

| 方案 | 说明 |
|------|------|
| AMD GPU | 用 ROCm，PyTorch 有 ROCm 版本 |
| Apple Silicon | M 系列芯片用 Metal（PyTorch mps 后端） |
| CPU 训练 | 小模型可行，用 OpenBLAS/MKL 优化 |
| 专用芯片 | TPU（Google）、NPU（华为昇腾）、推理芯片 |

> **国产化提示**：华为昇腾（Ascend）用 CANN + MindSpore，是国产 AI 算力方案。在信创场景中越来越常见。

---

## 29.9 本章总结

| 知识点 | 内容 |
|--------|------|
| GPU 价值 | 大规模并行矩阵运算，训练快几十上百倍 |
| 软件栈 | 硬件 → 驱动 → CUDA → cuDNN → AI 框架 |
| 驱动安装 | ubuntu-drivers/reboot；Secure Boot 坑 |
| CUDA | 框架自带运行时；版本匹配；nvcc 编译 CUDA 代码 |
| PyTorch | pip 装对应 CUDA 版；`torch.cuda.is_available()` 验证 |
| nvidia-smi | 监控利用率、显存、温度；诊断训练瓶颈 |
| 容器 GPU | nvidia-container-toolkit；`docker run --gpus all` |
| 其他 | ROCm、mps、CPU、昇腾 CANN |

---

## 本章练习

1. 用 `lspci | grep -i nvidia` 查看是否有 NVIDIA 显卡（无显卡可跳过实操，理解概念）。
2. 理解驱动、CUDA、cuDNN、AI 框架的层次关系，画一张图。
3. 用 `nvidia-smi` 查看 GPU 信息（有显卡时），记录驱动版本和支持的 CUDA 版本。
4. 在虚拟环境安装 PyTorch，用 `torch.cuda.is_available()` 验证。
5. 用 `nvidia-smi -l 1` 实时监控 GPU 状态。
6. 安装 nvidia-container-toolkit，在容器里运行 `nvidia-smi`（有 GPU 环境时）。
7. 思考：AI 训练时 GPU 利用率忽高忽低说明什么？如何排查？（结合第 28 章）
8. 思考：为什么容器里用 GPU 需要额外的 toolkit？容器不是共享宿主内核吗？

---

**下一章预告**：我们将学习 Linux 安全工具链——把前面所有知识用于实际的安全工作，介绍常用工具的分类、安装与使用，以及搭建自己的安全实验室。这是第六卷的收官。
