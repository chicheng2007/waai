# 硬件与本地环境配置（R9000P 2025 · RTX 5060）

> 你的设备：联想拯救者 R9000P 2025 · RTX 5060（8GB 显存）+ R9 9955HX（16 核 32 线程）+ 32GB DDR5 + 1TB SSD。
> 结论先说：**这是一台很能打的 AI 学习本**，不是"够不够用"，而是"用得很好"。别再觉得需要加钱换设备。

**导航**：[00 总览](../roadmap/00-overview.md) · [03 深度学习](../roadmap/03-deep-learning.md) · [Python 路线](../tools/python-roadmap.md) · [链接速查表](links.md) · [打卡](../checkin-log.md)

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
- ✅ 本地跑小模型推理：BERT 类（`bert-base-chinese`）、9B 级 LLM（Q4 量化后能完整放进显存，**你已实测跑通 Qwen3.5-9B**）
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
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
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
- 每个项目一个环境，配 `requirements.txt` 方便复现（见 [Python 路线 · 台阶 6](../tools/python-roadmap.md#八台阶-6工程化全程穿插)）。

> ⚠️ 常见坑：PyTorch 的 CPU 版和 CUDA 版不能混装。如果之前装过 CPU 版，先卸载干净再装 CUDA 版。`pip uninstall torch torchvision torchaudio` 后重装。

---

## 四、本地跑大模型（你已实战：LM Studio + Qwen3.5-9B）

> **你的实战记录**：你已经在 LM Studio 上部署了 **Qwen3.5-9B**。这不是"能不能跑"的问题——你已经跑起来了，而且这套组合是 8GB 显存公认的甜点配置。下面把部署要点和进阶玩法记下来。

### 你的配置为什么合理（联网核实 2026-11-24）

| 项目 | 说明 |
|---|---|
| **模型** | Qwen3.5-9B —— 社区公认 8GB 显存的最佳本地助手，推理质量远超参数级别 |
| **量化** | Q4_K_M 是甜点：9B 压到约 5GB，保留约 95% 能力，能完整放进 8GB 显存 |
| **格式** | LM Studio 只认 **GGUF** 格式，下载模型时认准 GGUF 后缀 |
| **上下文** | 原生支持 32K；8GB 显存下 4K~8K 上下文最稳，长文本再往上调 |
| **速度** | 完整 GPU 加载可达 40~55 token/s（流畅对话级） |

### 部署要点（供你复查 / 优化）

1. **GPU offload 拉满**：模型能完整放进显存时，把 LM Studio 的 GPU 层数滑到最大（Qwen3.5-9B 约 32 层全 offload），速度最快；设太小会让 CPU 参与、风扇狂转。
2. **上下文别贪大**：4K~8K 够日常用；调太高会吃 KV Cache 显存，可能 OOM。Qwen3.5 支持 KV Cache 量化，需要长上下文时可用 8-bit/4-bit。
3. **量化选择**：Q4_K_M 默认最佳；显存有余量再上 Q5_K_M / Q6_K 提升质量。
4. **国内下载**：Hugging Face 直连慢可用 `hf-mirror.com` 镜像；LM Studio 的 Discover 里也能直接搜模型一键下。
5. **当 API 用**：LM Studio 的 Developer 标签可开一个 OpenAI 兼容的本地服务，让你的 Python 脚本 / Agent 直接调用——这是接 Agent 项目的关键（见 [04 大模型/Agent](../roadmap/04-llm-agent.md)）。

### 其他可选工具

| 工具 | 特点 |
|---|---|
| **LM Studio**（你在用） | 图形界面，操作最简单，适合探索和调参 |
| **Ollama** | 命令行优先，适合后台运行 / 给脚本提供 API |
| **llama.cpp** | 底层推理引擎，量化 / 部署研究用（LM Studio 底层就是它） |

### 网安玩法（授权范围内，把你的模型用起来）

你有本地模型了，可以直接做 [04 大模型/Agent](../roadmap/04-llm-agent.md) 阶段的练手项目：
- **安全知识问答**：把你学的 CTF Writeup、取证笔记喂给它，做个人知识助手
- **威胁情报总结**：把攻击报告贴给它，让它提取 IoC（IP / 域名 / hash）
- **日志解读**：让它解释日志字段、分析可疑记录（辅助你学取证）
- **RAG 实验**：本地模型 + 安全知识库，做检索增强问答

> 注意：本地 9B 模型的推理能力有限，复杂任务比不上云端大模型。但**用来学原理、写代码、做实验完全够**，而且数据不出本机——对网安场景反而是优势。

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

*信息来源：硬件规格来自联想官网产品页与京东商品页（2026-11-24 核实）；Qwen3.5-9B 部署参数来自 qwen-ai.com、localllm.in、LM Studio 社区指南（2026-11-24 核实）。硬件具体规格以你的实际机型为准。*
