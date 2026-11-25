# PWN 进阶实战：源码、绕过与自动化

> 这不是一本「从零开始」的教程。这是给已经能独立做出中低难度 PWN 题、想真正搞懂底层原理并突破瓶颈的人写的。

<p align="center">
  <img src="https://img.shields.io/badge/level-advanced-red?style=flat-square" alt="level">
  <img src="https://img.shields.io/badge/prerequisite-基础版教程-green?style=flat-square" alt="prerequisite">
  <img src="https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-blue?style=flat-square" alt="license">
</p>

---

## 这本书和基础版有什么不同

基础版《从零开始的 Pwner 生活》解决的是「**怎么做**」——栈溢出怎么算偏移、ret2libc 怎么泄露、tcache poisoning 怎么改 fd。

这本进阶版解决的是「**为什么**」和「**当常规手段失效时怎么办**」：

- 不只告诉你 tcache 怎么 poisoning，而是带你读 `_int_free` 源码，看清楚 key 检查在哪一行、safe-linking 的异或 happened 在哪里
- 不只教你 FSOP 的模板，而是梳理 vtable 检查从 glibc 2.24 到 2.35 的演化史，以及每一代绕过的核心洞察
- 不只手写 ROP 链，而是用 angr 做符号执行自动求解、用 AFL 挖出隐藏的漏洞
- 不只玩用户态，还带你进内核态、看 Windows 和 ARM 架构

**一句话**：基础版教你钓鱼，进阶版教你造鱼竿。

---

## 前置要求

在开始之前，你应该已经能够：

- 独立完成 stack overflow → ret2libc 的完整利用
- 理解 ELF、GOT/PLT、Canary、PIE 的原理
- 使用 pwntools 和 gdb/pwndbg 调试
- 理解堆的基础概念（chunk、bin、tcache、UAF）
- 独立写出 unsorted bin leak + tcache poisoning 的 exp

> 如果上面有任何一条做不到，请先读基础版《从零开始的 Pwner 生活》。进阶版会默认你已经掌握这些，不再从头解释。

推荐先读基础版：https://github.com/你的用户名/pwner-journey

---

## 内容结构

| 篇目 | 核心内容 |
| --- | --- |
| [第一篇 · glibc 堆源码剖析](./01-glibc-internals/README.md) | malloc/free 源码、tcache 实现、bins 维护、检查机制与绕过 |
| [第二篇 · 现代堆利用](./02-modern-heap/README.md) | House of Apple、FSOP、largebin attack、堆布局自动化、真题复盘 |
| [第三篇 · IO_FILE 深度剖析](./03-iofile-deep/README.md) | FILE 结构体源码、vtable 检查演化、stdout 泄露全姿势 |
| [第四篇 · 自动化与工具](./04-automation/README.md) | angr 符号执行、AFL 模糊测试、利用脚本工程化 |
| [第五篇 · 内核与跨平台](./05-kernel-cross/README.md) | 内核 PWN 深入、Windows PWN、ARM/AArch64 入门 |
| [附录](./appendix/) | 源码索引、绕过手法速查、调试技巧、环境配置 |

完整目录见 [SUMMARY.md](./SUMMARY.md)。

---

## 环境建议

进阶实验对 glibc 版本更敏感，建议准备多套环境：

- **Docker + 多版本 glibc**：用 `ubuntu:16.04`（2.23）、`18.04`（2.27）、`20.04`（2.31）、`22.04`（2.35）镜像
- **glibc-all-in-one**：https://github.com/matrix1001/glibc-all-in-one —— 一键下载各版本 libc 和 loader
- **pwncli / pwninit**：自动替换题目 libc 和 loader
- **qemu-system-x86_64**：内核 PWN 用

---

## 学习方法

1. **源码先行**：进阶版的每章都建议先读一遍相关 glibc 源码，再看讲解。教程会给出源码位置和关键函数。
2. **调试验证**：源码读懂了不代表理解，一定要用 gdb 单步验证你的理解。
3. **版本对照**：同一个技术在不同 glibc 版本下的差异是重点。每章都会标注版本。
4. **做笔记**：尤其是 vtable 演化、各种 House 的触发条件——这些容易混淆。

---

## 免责声明

> 本教程仅用于合法的网络安全学习与 CTF 竞赛训练。严禁将教程中的技术用于攻击未经授权的系统。详见 README 底部的说明与各章提醒。

---

Happy Hacking, and may your exploits always work on remote.
