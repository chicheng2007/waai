# 从零开始的 Pwner 生活

> 一本面向完全零基础读者的 CTF PWN 方向系统性教程。从「什么是 pwn」讲到「堆利用与 IO_FILE」，目标是让每一名认真读完的读者，都能独立拿下主流 CTF 比赛中的中低难度 PWN 题目。

<p align="center">
  <img src="https://img.shields.io/badge/status-in%20progress-orange?style=flat-square" alt="status">
  <img src="https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-blue?style=flat-square" alt="license">
  <img src="https://img.shields.io/badge/language-中文-green?style=flat-square" alt="language">
</p>

---

## 写在前面

如果你点开了这个仓库，说明你大概率听说过 CTF，也大概率在某个深夜刷到别人「一发 getshell」的操作，心里冒出过一句话：

> 「这玩意儿到底是怎么做到的？」

这个教程就是写给你的。

PWN 是 CTF 中最硬核、也最有魅力的方向之一。它要求你同时理解高级语言、汇编、操作系统和编译原理，能够在脑海中还原程序运行的每一个细节，然后用一个看似不起眼的漏洞，撬动整个进程的控制权。很多人第一次接触时会被 NX、Canary、PIE、RELRO 这些名词劝退，也会因为调不通一个 ROP 链而怀疑自己。

但真相是：**PWN 不靠天赋，靠的是正确的学习路径和足够多的动手练习。** 这个教程试图提供前者，而后者需要你自己去敲。

本教程的三个承诺：

1. **零基础友好**：不假设你学过汇编、不假设你编译过 C 程序。所有前置知识都会在用到时讲清楚。
2. **原理优先**：不教你死记 payload 模板，而是解释「为什么这样构造」，让你面对变形题也能自己推导。
3. **循序渐进**：每一章都建立在前一章的基础上，概念从最简单处引入，逐步堆叠难度。

---

## 你将学到什么

完成这本教程后，你将能够：

- 独立搭建一套稳定的 PWN 学习与调试环境
- 读懂 x86-64 汇编，理解函数调用约定与栈帧结构
- 理解 ELF 文件格式、程序加载过程与动态链接机制
- 说清楚 NX、Canary、PIE、RELRO、FORTIFY 每种保护机制的原理与绕过思路
- 掌握栈溢出、ROP、ret2libc、栈迁移等经典栈利用技术
- 掌握格式化字符串漏洞的泄露与任意地址写
- 理解 glibc malloc/free 的底层实现（ptmalloc），并掌握 UAF、Double Free、Fastbin/Tcache/Unsorted Bin Attack 等主流堆利用手法
- 掌握 IO_FILE 利用、沙箱绕过、ORW 等进阶主题
- 熟练使用 pwntools、gdb/pwndbg 等工具完成漏洞挖掘与利用

---

## 学习路线

| 阶段 | 篇目 | 核心内容 | 建议时长 |
| --- | --- | --- | --- |
| 第一阶段 | [筑基篇](./01-foundation/README.md) | C 语言、汇编、ELF、内存布局、保护机制 | 2~3 周 |
| 第二阶段 | [栈利用篇](./02-stack/README.md) | 栈溢出、ROP、Canary 绕过、栈迁移 | 3~4 周 |
| 第三阶段 | [格式化字符串篇](./03-format-string/README.md) | 格式化字符串原理、泄露与任意写 | 1~2 周 |
| 第四阶段 | [堆利用篇](./04-heap/README.md) | ptmalloc、UAF、各种 Bin Attack | 4~6 周 |
| 第五阶段 | [高级主题篇](./05-advanced/README.md) | IO_FILE、沙箱、ORW、内核 PWN | 3~4 周 |
| 第六阶段 | [工具与实战篇](./06-tools-practice/README.md) | pwntools、gdb、真题复盘 | 贯穿全程 |

> **一句话路线**：先把 C 和汇编搞明白，再玩栈，玩透栈再碰堆，堆搞不动就回头补基础。不要跳级。

---

## 目录

完整的章节清单见 [SUMMARY.md](./SUMMARY.md)。各篇入口：

- **第一篇 · 筑基篇：新手村** —— [进入](./01-foundation/README.md)
- **第二篇 · 栈上功夫** —— [进入](./02-stack/README.md)
- **第三篇 · 格式化字符串的魔法** —— [进入](./03-format-string/README.md)
- **第四篇 · 堆的奥秘** —— [进入](./04-heap/README.md)
- **第五篇 · 进阶之路** —— [进入](./05-advanced/README.md)
- **第六篇 · 工具与实战** —— [进入](./06-tools-practice/README.md)
- **附录** —— [常用命令速查](./appendix/cheatsheet.md) · [利用模板](./appendix/templates.md) · [名词解释](./appendix/glossary.md) · [推荐资源](./appendix/resources.md)

---

## 环境准备

教程中的实验默认基于以下环境：

- **系统**：Ubuntu 20.04 / 22.04（64 位）
- **架构**：x86-64（同时兼顾 32 位程序，会标注）
- **glibc**：2.31 / 2.35（堆章节会专门讨论版本差异）
- **核心工具**：
  - `gcc`、`gdb`（配合 `pwndbg` / `gef`）
  - `python3` + `pwntools`
  - `checksec`、`ROPgadget`、`one_gadget`
  - `objdump`、`readelf`、`nm`、`strings`

第一篇第 2 章会手把手带你完成全套环境安装，不用担心。

---

## 如何阅读

1. **不要只看不练**。每一章的示例代码都请在自己的机器上敲一遍、调一遍。PWN 是手艺活，看会了不等于会了。
2. **善用调试器**。遇到不理解的地方，打开 gdb 单步执行，观察寄存器和内存的变化，比盯着教程猜要好一百倍。
3. **接受卡壳**。卡在某个点三天是正常的，这正是大脑在建立新连接。睡一觉，第二天往往就通了。
4. **做笔记**。尤其是堆章节的 various chunk 结构和 bin 链表，画图的记忆效果远超纯文字。

---

## 免责声明

> **本教程仅用于合法的网络安全学习与 CTF 竞赛训练。**
>
> 教程中讲解的漏洞利用技术，是为了帮助你理解软件安全机制、提升防御能力。请仅在**自己拥有完全授权的靶机、CTF 比赛平台或隔离的实验环境**中使用这些技术。
>
> **严禁**将本教程中的任何技术用于攻击未经授权的计算机系统。未经授权对他人计算机系统进行渗透测试在绝大多数国家和地区都属于违法行为，由此产生的一切法律责任由行为人自行承担。
>
> 作者与贡献者不对任何滥用行为承担责任。

---

## 贡献

这是一个持续更新的项目。如果你发现：

- 错别字、技术错误或过时的内容
- 有更好的讲解方式或补充案例
- 想新增某个主题（例如 Windows PWN、ARM 架构、内核利用）

欢迎提交 Issue 或 Pull Request。提交前请先阅读章节写作规范（见 `CONTRIBUTING.md`）。

---

## Star 一下

如果这个教程帮到了你，欢迎点一个 Star ⭐。你的支持是我持续更新的最大动力。

Happy Pwning!
