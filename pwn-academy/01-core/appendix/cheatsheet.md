# 附录 A：常用命令速查

## 信息收集

```bash
file ./vuln                          # 文件类型与架构
checksec --file=./vuln               # 保护机制
strings -a -t x ./vuln               # 字符串
nm ./vuln                            # 符号表
readelf -h/-S/-l/-d/-r ./vuln        # ELF 各类信息
objdump -d -M intel ./vuln           # 反汇编
ldd --version                        # 查看 glibc 版本
```

## 找 gadget 与地址

```bash
ROPgadget --binary ./vuln --only 'pop|ret'
ropper --file ./vuln --search 'pop rdi'
one_gadget ./libc.so.6
seccomp-tools dump ./vuln
```

## gdb / pwndbg

```gdb
b main / b *0x401234          # 断点
run / c / n / s / ni / si     # 执行控制
x/20gx $rsp                   # 查内存
info registers                # 查寄存器
stack / retaddr               # pwndbg 栈
heap / vis_heap_chunks        # pwndbg 堆
bins / tcache / fastbins      # pwndbg bin
find_fake_fast 地址 size       # 找 fake chunk
```

## pwntools

```python
from pwn import *
context.arch = 'amd64'
p = process('./vuln') / remote('ip', port)
p.sendlineafter(b'Input: ', payload)
p.interactive()
elf.sym['main'] / elf.plt['puts'] / elf.got['puts'] / elf.bss()
p64(x) / p32(x) / u64(b) / u32(b)
cyclic(200) / cyclic_find(0x6161616c)
fmtstr_payload(offset, {addr: value})
asm(shellcraft.amd64.linux.sh())
ROP(elf).call('system', [addr])
```

## 编译选项

```bash
# 新手村（全关保护）
gcc -g -O0 -no-pie -fno-stack-protector -z execstack -o vuln vuln.c

# 32 位
gcc -m32 -g -O0 -no-pie -fno-stack-protector -z execstack -o vuln32 vuln.c

# Full RELRO + Canary + NX + PIE（全开）
gcc -O2 -fstack-protector-all -z noexecstack -Wl,-z,relro,-z,now -o vuln vuln.c
```

## 系统设置

```bash
cat /proc/sys/kernel/randomize_va_space    # 查看 ASLR
sudo sysctl -w kernel.randomize_va_space=0 # 关闭 ASLR（学习用）
ulimit -c unlimited                        # 开启 core dump
```
