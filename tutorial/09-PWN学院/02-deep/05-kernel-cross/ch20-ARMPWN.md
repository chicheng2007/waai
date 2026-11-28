# 第 20 章 ARM/AArch64 PWN 简介

> 移动端和 IoT 设备多用 ARM 架构。这一章简要介绍 ARM PWN 的特点。

---

## 20.1 ARM 架构基础

### 32 位 ARM (ARMv7)

- 寄存器：r0~r15（r13=sp, r14=lr, r15=pc）
- 参数传递：r0~r3，其余走栈
- 指令集：ARM（定长 4 字节）、Thumb（2 或 4 字节）
- 返回地址存在 **lr** 寄存器（不是栈上！）

### 64 位 ARM (AArch64 / ARMv8)

- 寄存器：x0~x30（x29=fp, x30=lr），w0~w30（32 位）
- 参数传递：x0~x7
- 指令定长 4 字节

---

## 20.2 与 x86 的关键差异

| 特性 | x86-64 | ARM64 |
| --- | --- | --- |
| 返回地址 | 栈上 | lr 寄存器（需 spill 到栈） |
| 参数寄存器 | rdi, rsi, rdx... | x0, x1, x2... |
| 栈帧 | rbp/rsp | x29/fp, x30/lr |
| 指令长度 | 变长 | 定长 4 字节 |
| 跳转 | call/ret | bl/ret（lr 保存返回地址） |

---

## 20.3 ARM 栈溢出

因为返回地址存在 lr 寄存器，函数序言会把 lr 保存到栈上：

```asm
stp x29, x30, [sp, #-16]!    ; 保存 fp 和 lr
mov x29, sp
```

栈溢出时覆盖栈上保存的 lr，函数返回（`ret`，即 `br x30`）时跳转到我们的目标。

---

## 20.4 工具

```bash
# 交叉编译
sudo apt install gcc-aarch64-linux-gnu
aarch64-linux-gnu-gcc -o vuln_arm vuln.c

# qemu 用户态模拟
qemu-aarch64 ./vuln_arm

# 调试
qemu-aarch64 -g 1234 ./vuln_arm
aarch64-linux-gnu-gdb
target remote :1234

# ROPgadget 支持 ARM
ROPgadget --binary ./vuln_arm --only 'pop|ret'
```

pwntools 也支持 ARM：

```python
context.arch = 'aarch64'
shellcraft.aarch64.linux.sh()
```

---

## 20.5 shellcode

x86 的 shellcode 不能直接用在 ARM 上。ARM 需要专门的 shellcode：

```python
context.arch = 'aarch64'
sc = asm(shellcraft.aarch64.linux.sh())
```

注意 ARM 的流水线效应和指令对齐要求。

---

## 20.6 移动端 PWN 的特殊性

- Android 上的 PWN 涉及 SELinux、seccomp
- iOS 上有代码签名、PAC（指针认证）
- 这些是移动端安全的专门领域

---

## 20.7 小结

这一章简要介绍了 ARM PWN：

- ARM 的寄存器和调用约定
- 返回地址存在 lr，函数序言 spill 到栈
- 用 qemu 模拟和调试
- shellcode 需要针对架构生成

---

## 全书结语

恭喜你走完了进阶版的全部 20 章。

从 glibc 源码到 House of Apple，从 angr 到内核提权，你已经站在了 PWN 进阶的起点上。但请记住：

> 真正的高手不是记住了多少 exp 模板，而是理解每一行检查背后的设计意图，并能在新的环境里重新推导出来。

**技术之路没有终点。保持好奇，持续动手。Happy Hacking!**

---

**正文完**

**附录**：[源码索引](../appendix/source-index.md) · [绕过速查表](../appendix/bypass-table.md) · [调试技巧](../appendix/debug-tips.md) · [环境配置](../appendix/environment.md)
