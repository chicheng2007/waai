# 第 19 章 Windows PWN 入门

> 前面都是 Linux，这一章简单看看 Windows 平台的 PWN 有什么不同。

---

## 19.1 PE 格式

Windows 可执行文件是 **PE（Portable Executable）** 格式，对应 Linux 的 ELF。

关键结构：

- **DOS Header** → **PE Header** → **Section Headers**
- 导入表（IAT）：类似 ELF 的 GOT
- 基址重定位表：类似 PIE

工具：

```bash
# 查看 PE 信息
objdump -x ./vuln.exe
pefile（Python 库）
```

---

## 19.2 Windows 堆

Windows 的堆管理器（Heap Manager）与 glibc 完全不同：

- 前端堆（LFH, Low Fragmentation Heap）
- 后端堆
- 没有 tcache/fastbin 的概念

Windows 堆利用的经典技术：

- Heap Spray（堆喷射）
- Lookaside List 攻击
- FreeList 攻击

---

## 19.3 调用约定

Windows x64 的调用约定与 Linux System V 不同：

| 参数 | Linux | Windows |
| --- | --- | --- |
| 1~4 | rdi, rsi, rdx, rcx | rcx, rdx, r8, r9 |
| 影子空间 | 无 | 32 字节（调用者分配） |

构造 ROP 时要注意参数寄存器的差异。

---

## 19.4 保护机制

- **GS**：类似 Canary
- **DEP**：类似 NX
- **ASLR**：类似 ASLR
- **CFG**（Control Flow Guard）：类似 CET 的间接跳转保护
- **SEH**：结构化异常处理，可作为攻击目标

---

## 19.5 利用特点

- Windows CTF PWN 题较少（环境复杂）
- 常用 ROP 调用 `WinExec`/`system`
- SEH 覆盖是经典手法

---

## 19.6 小结

这一章简要介绍了 Windows PWN：

- PE 格式、IAT
- Windows 堆管理器
- 调用约定差异（rcx, rdx, r8, r9）
- GS/DEP/ASLR/CFG 保护

下一章我们看 ARM 架构的 PWN。

---

**下一章**：[ARM/AArch64 PWN 简介](./ch20-ARMPWN.md)
