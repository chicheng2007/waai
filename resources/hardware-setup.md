# 硬件与本地环境配置（R9000P 2025 · RTX 5060）

> 你的设备：联想拯救者 R9000P 2025 · RTX 5060（8GB 显存）+ R9 9955HX（16 核 32 线程）+ 32GB DDR5 + 1TB SSD。
> 结论先说：**这是一台很能打的 AI 学习本**，不是"够不够用"，而是"用得很好"。别再觉得需要加钱换设备。

**导航**：[00 总览](../roadmap/00-overview.md) · [03 深度学习](../roadmap/03-deep-learning.md) · [Python 路线](python-roadmap.md) · [链接速查表](links.md) · [打卡](../checkin-log.md)

---

## 一、你这台机器处在什么水平

| 部件 | 规格 | 对 AI 的意义 |
|---|---|---|
| **GPU** | RTX 5060 Laptop，8GB 显存，Blackwell 架构 | 能用 GPU 训练/推理，8GB 是本地跑模型的实用门槛 |
| **CPU** | AMD R9 9955HX，16 核 32 线程 | 数据处理、编译、跑传统 ML 绰绰有余 |
| **内存** | 32GB DDR5 | 大数据集、多任务、开虚拟机都不慌 |
| **硬盘** | 1TB SSD | 放数据集、模型权重、多个虚拟环境 |

> 对比：很多 AI 初学者用的是无独显的轻薄本或老旧机器，只能 CPU 慢跑或用免费云环境。你的配置可以直接本地 GPU 训练，起步就领先一大截。

---

## 二、8GB 显存能做什么、不能做什么

**能做（你的主战场）**：
- ✅ 传统机器学习（sklearn / XGBoost）——跟显存没关系，CPU 就够快
- ✅ 深度学习入门：MLP / CNN / LSTM / 小型 Transformer，用 PyTorch 本地训练
- ✅ 网安实战项目：流量分类、日志异常检测、钓鱼文本识别、恶意代码分类（这些都是小模型）
- ✅ 本地跑小模型推理：BERT 类（`bert-base-chinese`）、小型 LLM（7B 模型 4-bit 量化后能跑）
- ✅ Stable Diffusion 画图（8GB 显存可运行）
- ✅ 用 Ollama / LM Studio 本地跑量化大模型，做威胁情报问答实验

**别硬做（要云算力）**：
- ❌ 从头预训练大模型 / 大语言模型（那是 A100/H100 集群的活）
- ❌ 全参数微调 7B 以上大模型（显存不够，但可以用 LoRA / QLoRA 轻量微调）
- ❌ 超大图像 / 视频生成模型

> 关键点：**你整个学习路线里的项目，8GB 显存全部够用**。等真需要更强算力（比如大三做毕设微调大模型），再考虑云服务器（AutoDL 等，按小时租），不用现在升级硬件。

---

## 三、软件环境怎么配（GPU 版 PyTorch）

### 步骤 1：确认 NVIDIA 驱动
- 打开终端运行 `nvidia-smi`，能看到 GPU 信息和 CUDA 版本就说明驱动正常。
- RTX 5060 是较新的卡，建议装最新版 NVIDIA 驱动（官网或 GeForce Experience 更新）。

### 步骤 2：装 CUDA 版 PyTorch
- 去 [PyTorch 官网](https://pytorch.org/get-started/locally/) 选配置：Stable → Windows → Pip → Python → **CUDA 12.x**（选最新的 CUDA 版本），复制生成的安装命令执行。
- 例（具体版本以官网生成命令为准）：
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
  ```

### 步骤 3：验证 GPU 可用
```python
import torch
print(torch.cuda.is_available())        # 应输出 True
print(torch.cuda.get_device_name(0))    # 应显示 RTX 5060
```
输出 `True` 就说明 PyTorch 能用上你的显卡了。

### 步骤 4：用 Anaconda / Miniconda 管理环境（推荐）
- 不同项目依赖不同版本，用 conda 建虚拟环境互不干扰：
  ```bash
  conda create -n ai python=3.11
  conda activate ai
  ```
- 每个项目一个环境，配 `requirements.txt` 方便复现（见 [Python 路线 · 台阶 6](python-roadmap.md#八台阶-6工程化全程穿插)）。

> ⚠️ 常见坑：PyTorch 的 CPU 版和 CUDA 版不能混装。如果之前装过 CPU 版，先卸载干净再装 CUDA 版。`pip uninstall torch torchvision torchaudio` 后重装。

---

## 四、本地跑大模型（学有余力再玩）

你的 8GB 显存可以体验本地大模型，这对理解 LLM 很有帮助：

| 工具 | 能跑什么 | 用途 |
|---|---|---|
| **Ollama** | 7B 模型（q4 量化），如 qwen2.5:7b、llama3.1:8b | 本地问答、做 RAG 实验 |
| **LM Studio** | 图形界面，操作最简单 | 零命令行体验本地模型 |
| **llama.cpp** | CPU/GPU 混合推理 | 量化、部署研究 |

**网安玩法**（授权范围内）：把本地模型接进你的知识库，做一个"安全知识问答助手"——这是 [04 大模型/Agent](../roadmap/04-llm-agent.md) 阶段的现成练手项目。

---

## 五、设备使用建议

1. **插电用性能模式**：训练时插电源，开拯救者控制中心的性能模式，让显卡满血释放。
2. **注意散热**：16 寸游戏本长时间训练会热，垫高底部、保持通风，别堵住出风口。
3. **电池续航别指望**：80Wh 电池打游戏/训练掉电快，AI 学习基本都要插电，这是游戏本通病。
4. **硬盘空间规划**：1TB SSD 建议给数据集和模型单独分区/文件夹，模型权重动辄几个 GB。
5. **别折腾双系统**：Windows + WSL2 足够学 AI；真需要 Linux 环境用 WSL2 或虚拟机，不用装双系统。

---

## 六、一句话总结

**你不需要为硬件焦虑。** 这台 R9000P 2025 + RTX 5060 陪你走完从 Python 入门到大模型实验的全程都没问题。真正稀缺的是时间和动手——把机器用起来，比纠结配置重要一万倍。

---

*配置信息来源：联想官网产品页与京东商品页（2026-11-24 核实）。具体规格以你的实际机型为准。*
