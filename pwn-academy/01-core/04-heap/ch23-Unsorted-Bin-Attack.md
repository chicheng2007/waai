# 第 23 章 Unsorted Bin Attack

> unsorted bin 是一个双向循环链表。当 malloc 从里面摘下一个 chunk 时，会修改它前后 chunk 的指针。如果我们能控制这些指针，就能往任意地址写入一个 libc 地址。

---

## 23.1 unsorted bin 的解链过程

unsorted bin 是双向循环链表。当 malloc 遍历 unsorted bin 时，会执行「解链」操作：

```c
// 把 victim 从链表中摘下来（简化）
bck = victim->bk;
fwd = victim->fd;
bck->fd = fwd;      // ← 关键！往 bck->fd 写入 fwd
fwd->bk = bck;
```

或者 glibc 的实际代码（unlink 宏）：

```c
#define unlink(P, BK, FD) {
    FD = P->fd;
    BK = P->bk;
    FD->bk = BK;
    BK->fd = FD;
}
```

**关键洞察**：解链时会执行 `BK->fd = FD`。如果我们可以控制 `P->bk`（即 BK），就能让 glibc 往 `BK->fd` 这个地址写入 `FD` 的值（一个堆地址或 libc 地址）。这就是 **任意地址写**！

---

## 23.2 unsorted bin attack 原理

条件：

1. 能控制 unsorted bin 中某个 chunk 的 `bk` 指针
2. 能触发 malloc 遍历 unsorted bin（分配一个适当大小的 chunk）

步骤：

```text
1. 有一个 chunk P 在 unsorted bin 中
2. UAF 修改 P->bk = target_addr - 0x10
   （因为解链时会往 BK->fd 写，BK->fd 就是 target_addr）
3. malloc 触发解链：
   FD = P->fd  （一个堆地址）
   BK = P->bk  （我们伪造的 target_addr - 0x10）
   BK->fd = FD → *(target_addr - 0x10 + 0x10) = FD
   → *target_addr = FD（一个堆地址）
```

**效果**：`target_addr` 被写入了一个**堆地址**（unsorted bin 中另一个 chunk 的地址）。

### 23.2.1 写的值是什么

写入的值是 `FD`，即 `P->fd`。在 unsorted bin 里，`fd` 通常指向链表中的另一个 chunk（也是堆地址），或者当链表中只有 P 一个 chunk 时，`fd` 指向 main_arena（libc 地址）。

所以 unsorted bin attack 能写入的值有两种：

- **堆地址**（链表有多个 chunk 时）
- **libc 地址**（链表只有一个 chunk 时，fd 指向 main_arena）

---

## 23.3 经典目标：global_max_fast

unsorted bin attack 最经典的目标是 **`global_max_fast`**——一个全局变量，记录 fastbin 的最大大小（默认 0x80）。

如果把 `global_max_fast` 改成一个很大的值（通过 unsorted bin attack 写入一个堆地址，堆地址很大），那么所有大小的 chunk 都会被当作 fastbin 处理。这会导致：

- free 任何大小的 chunk 都进入 fastbin
- 可以配合 fastbin attack 分配任意地址
- 引发更多可利用的状态

```python
# 伪代码
global_max_fast_addr = libc_base + libc.sym['global_max_fast']

# 通过 UAF 修改 unsorted bin 中 chunk 的 bk
chunk_bk = global_max_fast_addr - 0x10
edit(victim_chunk, b'...' + p64(chunk_bk))

# 触发 malloc 解链
malloc(appropriate_size)
# global_max_fast 现在被写入了一个堆地址（很大的值）
```

> ⚠️ **注意**：unsorted bin attack 只能写入一次，而且写入的是一个地址值（不可控具体数值）。它通常不是最终的 getshell 手段，而是「打开局面」的一步——比如让 global_max_fast 变大，为后续 fastbin attack 创造条件。

---

## 23.4 Largebin Attack

Largebin attack 是 unsorted bin attack 的「升级版」，利用 largebin 的 `fd_nextsize` / `bk_nextsize` 指针。

### 23.4.1 largebin 的插入过程

当一个 chunk 被放入 largebin 时，glibc 会根据大小排序，修改链表指针：

```c
// 简化版
bck = ...;  // 找到插入位置
fwd = bck->fd;
bck->fd = P;
fwd->bk = P;
P->fd = fwd;
P->bk = bck;

// 如果大小不同，还要处理 nextsize 链：
P->fd_nextsize = fwd;
P->bk_nextsize = fwd->bk_nextsize;
fwd->bk_nextsize->fd_nextsize = P;   // ← 关键！
fwd->bk_nextsize = P;
```

**关键洞察**：`fwd->bk_nextsize->fd_nextsize = P` 这行会往 `fwd->bk_nextsize + 0x18` 处写入 P 的地址（堆地址）。如果控制 `fwd->bk_nextsize`，就能实现任意地址写。

（glibc 2.31 及之前还有另一个写：`bck->fd = P`，写入位置是 `bck+0x10`。glibc 2.32+ 修复了部分检查，需要调整技巧。）

### 23.4.2 Largebin attack 的效果

- 往任意地址写入一个**堆地址**（被插入 largebin 的 chunk 的地址）
- 常用于修改 `_IO_list_all`（IO_FILE 利用的前置步骤）
- 在 House of Storm 等组合利用中扮演关键角色

---

## 23.5 实战思路

unsorted bin attack 和 largebin attack 通常不是最后一击，而是组合利用的一环：

```text
典型利用链：
1. 泄露 libc（unsorted bin leak）
2. unsorted bin attack → 修改 global_max_fast
3. fastbin attack → 分配任意地址
4. 写入 hook 或 IO_FILE → getshell

或：
1. Largebin attack → 修改 _IO_list_all
2. FSOP → 触发 IO_FILE 利用 → getshell
```

由于这两种攻击的「写值不可控」，它们更多是「改变程序状态」而非直接 getshell。具体例题会在后面的 IO_FILE 章节（第 26 章）中讲解。

---

## 23.6 常见坑

1. **解链检查**：glibc 对 unsorted bin 的解链有检查（如 `bck->fd != victim`），伪造时需要满足这些条件，否则会报 "corrupted unsorted chunks"。
2. **写入值的不可控性**：写入的是地址值，不能直接写 system 的地址。需要配合其他技术。
3. **版本差异**：largebin attack 在 glibc 2.32+ 有变化，做题时要确认版本。
4. **tcache 干扰**：小块 free 后先进 tcache，不会进 unsorted bin。需要分配足够大的块（> 0x410）或耗尽 tcache。

---

## 23.7 小结

这一章我们学了 Unsorted Bin Attack 和 Largebin Attack：

- **unsorted bin attack**：控制 chunk 的 bk 指针，利用解链时的 `BK->fd = FD` 往任意地址写入一个地址值
- **经典目标**：`global_max_fast`，扩大 fastbin 范围
- **largebin attack**：利用 `fd_nextsize/bk_nextsize` 的插入逻辑实现任意地址写
- **特点**：写入值不可控（是地址），通常作为组合利用的一环，而非最终一击

堆篇还剩两章：off-by-one 与 House of 系列（第 24 章）、堆风水实战（第 25 章）。下一章我们学习堆利用中非常重要的一类漏洞——off-by-one。

---

**下一章**：[off-by-one 与 House of 系列](./ch24-off-by-one与houseof.md)
