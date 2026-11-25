# 网安专业 · AI 学习路线

> 📖 **想系统学？看 [完整系统教程（9 卷 30 章）](tutorial/索引.md)** —— 从零基础到 AI+网安的完整课程，每章有可运行代码 + 逐行解释 + 练习。
>
> 🚨 **只会 print、一看 for/split 就懵？先看 [SYNTAX-BOOTCAMP.md（3 天语法急救包）](SYNTAX-BOOTCAMP.md)** —— 用"发牌/切香肠"讲懂读代码必备的 5 个零件，3 天后能读懂实战代码。
>
> 🚨 **语法没问题、想直接上实战？看 [START-HERE.md（14 天实战计划）](START-HERE.md)** —— 每天一个真任务，最后交付一个 AI 日志研判工具到 GitHub。

> 从零基础到「网安 + AI」复合人才的学习路线与资源清单。
> 起点：大二 · Python/C++ 基础语法 · 软考备考中 · AI / 攻防 / 取证均零基础。

![status](https://img.shields.io/badge/status-%E6%8C%81%E7%BB%AD%E6%9B%B4%E6%96%B0-brightgreen)
![stage](https://img.shields.io/badge/%E5%BD%93%E5%89%8D%E9%98%B6%E6%AE%B5-%E8%BD%AF%E8%80%83%E6%9C%9F-orange)
![license](https://img.shields.io/badge/license-MIT-blue)

---

## 这是什么

一份写给**网络安全专业学生**的 AI 学习路线。核心判断：

> AI 不用等网安学好了再学，它应该是你学攻防和取证的**加速器**。

整条路线按**三线并进**设计：

| 学习线 | 内容 |
|---|---|
| 主线 · 软考 | 网络工程师（网络地基） |
| 网安线 | CTF 驱动攻防 + 火眼取证 |
| AI 线 | 传统 ML → 深度学习 → 网安项目 → 大模型 / Agent |

---

## 文档导航

学习路线按阶段拆成了几篇短文，**按顺序读**即可：

**📖 完整系统教程（想系统学这个）**
- [教程索引](tutorial/索引.md) —— 两套教程的总入口
- [Python 主教程](tutorial/README.md) —— 9 卷 30 章，从零基础到 AI+网安（**大二主线**）
- [系统语言教程](tutorial/系统语言/README.md) —— C/C++ · Rust · Go 各 12 章，底层/性能/系统安全（**进阶，大三后按需**）

**🗺️ 学习路线（按顺序读）**
- [00 · 总览](roadmap/00-overview.md) —— 来不来得及、你的定位、三线路线图、大学时间线、执行纪律、今天做什么
- [01 · 软考期](roadmap/01-soft-exam.md) —— 软考复习 + CTF 攻防入门 + 火眼取证 + 每天 30min AI 底子
- [02 · 传统机器学习](roadmap/02-ml-basics.md) —— 吴恩达 ML + sklearn + KDD99 小项目
- [03 · 深度学习](roadmap/03-deep-learning.md) —— PyTorch + 4 个网安 AI 实战项目
- [04 · 大模型 / Agent](roadmap/04-llm-agent.md) —— Transformer + Agent 双重身份 + 学习路径

**📚 资源库（按需查）**
- 🗂️ **[练习用日志数据集（250 份）](datasets/README.md)** —— 带攻击特征的模拟日志 + 生成脚本，专配急救包和实战计划练手
- 🚑 **[3 天语法急救包](SYNTAX-BOOTCAMP.md)** —— 只会基础语法？用生活比喻讲懂 5 个读代码必备零件（放在开头，优先看）
- 🐍 **[Python 学习路线](resources/python-roadmap.md)** —— 从会语法到能写网安/AI 脚本，七个台阶 + 每日安排
- 💻 **[硬件与本地环境](resources/hardware-setup.md)** —— R9000P 5060 能跑什么、GPU 版 PyTorch 安装、**已实战 LM Studio + Qwen3.5-9B**
- [书籍推荐](resources/booklist.md) —— 按阶段 × 优先级，标注必读 / 选读
- [链接速查表](resources/links.md) —— 课程 / 靶场 / 工具 / 数据集 / 社区的直达链接

**✅ 记录**
- [每日打卡](checkin-log.md) —— 每天学完追加一行，记录进度

先从 [00 总览](roadmap/00-overview.md) 开始，再按阶段往下读；遇到资源对照链接速查表动手。每天打卡，让坚持看得见。

---

## 当前进度

用这个表追踪进展（把 `[ ]` 改成 `[x]` 即可）：

| 阶段 | 目标 | 状态 |
|---|---|---|
| 阶段 0 | 软考通过 | ⬜ 进行中 |
| 阶段 0 | 每天 30min Python / 数学 | ⬜ 进行中 |
| 阶段 0 | CTF 完成 10 道签到题 | ⬜ |
| 阶段 0 | 火眼独立完成一次取证分析 | ⬜ |
| 阶段 1 | 吴恩达 ML + sklearn 项目 | ⬜ |
| 阶段 2 | PyTorch + 网安 AI 项目 | ⬜ |
| 阶段 3 | 大模型 / Agent | ⬜ |

---

## 核心原则

1. **软考优先**：现阶段别因学 CTF / AI 把软考挂了。
2. **AI 当工具**：从第一天用 Cursor / Copilot 写代码，但每行都要看懂。
3. **CTF 驱动网安**：边做题边补，不要啃完书再实战。
4. **一个项目做透**：胜过多堆半吊子项目。
5. **守住法律底线**：渗透、扫描只在靶场或书面授权环境进行。

> 详见 [总览 · 执行纪律](roadmap/00-overview.md#十执行纪律这几条比计划本身更重要)

---

## 语言与工具取舍

- **语言**：大二专精 Python、保持 C++；Go / Rust 大三后按方向再学
- **Python 怎么学**：见 [Python 学习路线](resources/python-roadmap.md) —— 三条线的共同底座，优先练熟
- **取证**：以火眼证据分析为主线，不盲目堆工具
- **AI**：先传统机器学习，再深度学习，最后大模型 / Agent

---

## 法律与伦理声明

本仓库所有内容**仅用于合法学习**：

- CTF、靶场、SRC 挖洞请在授权范围内进行
- **严禁**对未授权的真实系统进行渗透、扫描、测试
- 发现漏洞应遵循负责任披露原则

技术再强，越界就是毁前程。这是网安专业学生必须守住的底线。

---

## License

[MIT](LICENSE) © 2026
