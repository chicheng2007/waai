# 第 18 章 chunk 结构与 bin 体系

> 这一章是堆利用的理论核心。搞懂 chunk 的结构和各种 bin 的链表组织方式，后面所有的 attack 都只是「利用这些结构的漏洞」而已。

---

## 18.1 malloc_chunk 全解

回顾上一章的结构体：

```c
struct malloc_chunk {
    INTERNAL_SIZE_T      prev_size;   /* 前一个 chunk 的大小（仅前一块空闲时有效） */
    INTERNAL_SIZE_T      size;        /* 本 chunk 大小 + 标志位 */
    struct malloc_chunk* fd;          /* 空闲时用：指向后一个 chunk */
    struct malloc_chunk* bk;          /* 空闲时用：指向前一个 chunk */
    struct malloc_chunk* fd_nextsize; /* largebin 专用 */
    struct malloc_chunk* bk_nextsize; /* largebin 专用 */
};
```

### 18.1.1 已分配 chunk

```text
chunk 起始 (地址 P)
    ┌───────────────────────────────┐
P   │ prev_size (8B)                │ ← 若前块在用，这 8 字节属于前块的数据
    ├───────────────────────────────┤
P+8 │ size (8B)                     │ ← 本 chunk 大小（含头部，对齐到 16）
    ├───────────────────────────────┤
P+16│ user data                     │ ← malloc 返回的地址 = P+16
    │  (size - 8 字节可用)           │
    └───────────────────────────────┘
P+size
```

**为什么用户可用空间是 `size - 8` 而不是 `size - 16`？**

因为下一个 chunk 的 `prev_size` 字段（8 字节）在当前 chunk 被占用时**没有用途**，glibc 把它也借给当前 chunk 当数据区。只有当当前 chunk 空闲时，下一个 chunk 才会用 `prev_size` 来记录当前 chunk 的大小（用于向前合并）。

例如 `malloc(0x18)`（24 字节）：

```text
请求 0x18 = 24 字节
实际 chunk size = (24 + 8 + 15) & ~15 = 0x30 (48 字节)
用户可用空间 = 0x30 - 8 = 0x28 (40 字节)
```

> ⚠️ **注意**：用户可用空间是 40 字节，但你请求的是 24 字节。多出来的 16 字节可以写入而不破坏 chunk 结构——这就是「堆溢出」能悄悄发生而不被立即发现的原因。

### 18.1.2 空闲 chunk

当 chunk 被 free 后：

```text
    ┌───────────────────────────────┐
P   │ prev_size                     │
    ├───────────────────────────────┤
P+8 │ size                          │
    ├───────────────────────────────┤
P+16│ fd  ← 指向链表中的下一个空闲块  │  ← malloc 返回地址的位置
    ├───────────────────────────────┤    现在被 fd/bk 占用！
P+24│ bk  ← 指向链表中的上一个空闲块  │
    ├───────────────────────────────┤
    │ 剩余空间（可以放数据，但会被覆盖）│
    └───────────────────────────────┘
```

**关键点**：空闲 chunk 的 `fd` 和 `bk` 指针就写在原本是 user data 的位置（P+16、P+24）。这意味着：

- 如果 UAF（释放后继续使用）漏洞能读写一个已释放 chunk 的 user data，你实际上能控制 `fd`/`bk` 指针 → 堆利用的核心！

### 18.1.3 size 字段与标志位

```text
size = 0x21 = 0b00100001
                  │  │ │
                  │  │ └─ PREV_INUSE (0x1)：前一个 chunk 在使用中
                  │  └─── IS_MMAPPED (0x2)
                  └────── NON_MAIN_ARENA (0x4)
```

因为 chunk 大小总是 16 字节对齐（低 4 位为 0），实际上只有 bit 0 (PREV_INUSE) 最常用。计算真实大小时要用 `size & ~0x7`。

---

## 18.2 top chunk

**top chunk** 是堆顶部的「剩余空间」，它不属于任何 bin。当所有 bin 都无法满足分配请求时，malloc 会从 top chunk 里切一块出来。

```text
堆布局：
┌──────────────┐
│ chunk 1      │  已分配
├──────────────┤
│ chunk 2      │  已分配
├──────────────┤
│ chunk 3      │  已释放（在某个 bin 中）
├──────────────┤
│ top chunk    │  ← 剩余的连续空间
│ size = 0x20d01│
└──────────────┘  ← program break
```

top chunk 的 prev_inuse 位总是 1（表示前一块在用）。当 top chunk 不够大时，malloc 会通过 brk 扩展堆（增大 top chunk 的 size），或者用 mmap 分配新区域。

> 💡 **利用价值**：如果能修改 top chunk 的 size 字段（比如通过溢出），就能让 malloc 在「扩展堆」时把我们伪造的地址当作新堆的起始位置——这就是 **House of Force**（第 24 章）。

---

## 18.3 bin 体系总览

glibc 用一系列**链表**来管理空闲 chunk，这些链表叫做 **bin**。根据大小和组织方式，分为：

```text
                    空闲 chunk 管理
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
    tcache            fastbin           普通 bin
   (每线程缓存)       (快速回收)      (small/large/unsorted)
        │                 │                 │
    64 个链表         10 个链表         128 个链表
   (2.26+引入)      (≤ 0x80 字节)    (small: ≤0x200, large: >0x200)
```

### 18.3.1 tcache（Thread Cache）

glibc 2.26 引入，是**每个线程独立的缓存**，用于加速小块内存的分配/释放。

- 共 **64 个链表**，按大小分类（0x20, 0x30, 0x40, ..., 0x410）
- 每个链表最多存放 **7 个** chunk
- 使用**单向链表**（只有 fd 指针），LIFO（后进先出）
- free 时优先放入 tcache，malloc 时优先从 tcache 取
- 每个 tcache chunk 的 `fd` 指向下一个，`key` 字段（在 user data + 8 处）记录所属 tcache，用于防止 double free（2.29+）

```text
tcache[2] (0x30 大小):
   entry → chunk A → chunk B → NULL
           fd        fd
```

### 18.3.2 fastbin

用于管理**小块**空闲 chunk（默认 ≤ 0x80 字节，即 128 字节）。

- 共 **10 个链表**（0x20, 0x30, ..., 0x80）
- **单向链表**（只用 fd 指针），LIFO
- 同 size 的 chunk 才在同一个链表里
- free 时不做相邻 chunk 合并（为了速度）
- 分配时检查 chunk 的 size 是否匹配链表（防止某些攻击，但检查并不严格）

### 18.3.3 smallbin

管理 **≤ 0x200 字节**（512 字节）的空闲 chunk。

- 共 **62 个链表**，按大小精确分类（间隔 16 字节）
- **双向循环链表**（fd 和 bk 都有效）
- FIFO（先进先出）
- free 时会和相邻空闲 chunk 合并

### 18.3.4 largebin

管理 **> 0x200 字节**的空闲 chunk。

- 共 **63 个链表**，按大小范围分类（不是精确大小）
- **双向循环链表**，且多了 `fd_nextsize` / `bk_nextsize` 指针，按大小排序
- 分配时找最合适的

### 18.3.5 unsorted bin

这是一个特殊的「中转站」。

- 只有 **1 个链表**
- 双向循环链表
- free 的大多数 chunk（除 tcache/fastbin 外）**先进入 unsorted bin**
- malloc 时先遍历 unsorted bin，找合适的直接返回，不合适的归类到 smallbin/largebin

> 💡 **关键点**：unsorted bin 是一个 FIFO 链表。当有多个 chunk 时，malloc 会从头开始找，把不合适的 chunk 摘下来放到对应 bin 的末尾。这个「摘链」过程涉及 fd/bk 指针的解链操作，是 **unlink attack** 和 **unsorted bin attack** 的基础。

---

## 18.4 main_arena

所有 bin 的链表头都存储在一个叫 **main_arena** 的结构体里，位于 libc 的数据段：

```c
struct malloc_state {
    mutex_t mutex;              // 互斥锁
    int flags;
    mchunkptr top;              // 指向 top chunk
    mchunkptr last_remainder;
    mchunkptr bins[NBINS * 2 - 2];  // 所有 bin 的链表头（fd/bk）
    unsigned int binmap[BINMAPSIZE];
    ...
};
```

**main_arena 的地址 = libc 基址 + 固定偏移**。这个偏移可以通过调试得到，也可以通过一些技巧（如 `__malloc_hook - 0x10`）间接定位。

> ⚠️ **重要**：unsorted bin 的链表头在 main_arena 里。当一个 chunk 被放入 unsorted bin 且它是链表中唯一的 chunk 时，它的 fd 和 bk 都会指向 main_arena 里的某个地址（即 `main_arena + 96` 附近）。**这 leaking 出来就是 libc 地址**——unsorted bin leak 是堆利用中最常用的信息泄露手段！

---

## 18.5 用 gdb 观察 bins

pwndbg 提供了直观的命令：

```gdb
# 显示所有 bins 的链表头和内容
bins

# 只看 tcache
tcache

# 只看 fastbin
fastbins

# 查看 arena 结构（含 top chunk 地址）
arena

# 查看某个地址处的 chunk 详情
p *(struct malloc_chunk*)0x555555559010
```

### 实战：观察 free 后 chunk 的去向

```c
// bins_demo.c
#include <stdlib.h>
#include <stdio.h>

int main() {
    char *a = malloc(0x20);   // chunk size 0x30（进 tcache/fastbin 范围）
    char *b = malloc(0x20);
    char *c = malloc(0x500);  // 大块
    
    printf("a=%p b=%p c=%p\n", a, b, c);
    
    free(a);   // 进 tcache（2.31）
    free(b);   // 进 tcache
    free(c);   // 进 unsorted bin
    
    return 0;
}
```

用 gdb 在每个 free 后暂停，用 `bins` 和 `vis_heap_chunks` 观察：

- `a` 和 `b` 进入 tcache[2]（0x30 大小），它们user data 的前 8 字节被写入 fd 指针
- `c` 进入 unsorted bin，因为它是链表中唯一的 chunk，fd 和 bk 都指向 main_arena

> 🔥 **实战**：在 freed chunk 的 user data 处用 `x/8gx 地址` 观察 fd/bk 的值。你会发现 unsorted bin 里的 chunk 的 fd/bk 指向 `0x7f...` 开头的地址（libc 的 main_arena）——这就是泄露 libc 的关键。

---

## 18.6 小结

这一章是堆利用最核心的理论基础：

- **chunk 头部**：prev_size、size（低 3 位是标志位）+ user data
- **用户可用空间** = size - 8（借用了下一个 chunk 的 prev_size）
- **空闲 chunk** 的 fd/bk 写在 user data 的位置 → UAF 能控制它们
- **top chunk**：堆顶剩余空间，不够时扩展
- **bin 体系**：
  - tcache（64 条，单向，LIFO，≤7 个，2.26+）
  - fastbin（10 条，单向，LIFO，小块）
  - smallbin（62 条，双向循环，FIFO，小中块）
  - largebin（63 条，双向循环 + nextsize 指针，大块）
  - unsorted bin（1 条，双向循环，中转站）
- **main_arena** 在 libc 里，存放所有 bin 的链表头
- **unsorted bin 的 fd/bk 指向 main_arena** → 泄露 libc 地址

从下一章开始，我们进入真正的堆利用技术。第一站是 UAF——最直观、最容易理解的堆漏洞。

---

**下一章**：[UAF：释放后的幽灵](./ch19-UAF.md)
