# 第 1 章 从 malloc 到 _int_malloc：一次分配的完整旅程

> 基础版告诉你 malloc 会依次检查 tcache、fastbin、unsorted bin……这一章我们打开 glibc 源码，看看这些步骤在代码里究竟长什么样。

---

## 1.1 源码准备

本章基于 glibc 2.31 的源码（2.35 的差异会单独标注）。相关文件：

- `malloc/malloc.c` —— malloc/free 的核心实现
- `malloc/arena.c` —— arena 管理
- `include/malloc.h` —— 结构体定义

获取源码：

```bash
# 下载 glibc 2.31 源码
wget https://ftp.gnu.org/gnu/glibc/glibc-2.31.tar.gz
tar xf glibc-2.31.tar.gz
# 关键文件：glibc-2.31/malloc/malloc.c
```

> 💡 **提示**：也可以在线看：https://sourceware.org/git/?p=glibc.git;a=blob;f=malloc/malloc.c

---

## 1.2 __libc_malloc：入口做了什么

我们调用的 `malloc(n)` 实际上是 `__libc_malloc(n)` 的宏：

```c
void *__libc_malloc (size_t bytes) {
    mstate ar_ptr;
    void *victim;

    // 1. 先检查 hook（2.34 之前）
    void *(*hook) (size_t, const void *) =
        atomic_forced_read (__malloc_hook);
    if (__builtin_expect (hook != NULL, 0)) {
        return (*hook)(bytes, RETURN_ADDRESS (0));
    }

    // 2. 尝试从 tcache 分配（快速路径）
    tcache_entry *e = tcache_get(0);   // 简化：实际是按 size 索引
    if (e != NULL) {
        return e;
    }

    // 3. 获取 arena（多线程支持）
    ar_ptr = arena_get_retry (NULL, bytes);
    
    // 4. 调用核心分配函数
    victim = _int_malloc (ar_ptr, bytes);
    
    // 5. 处理分配结果
    if (victim != NULL) {
        return victim;
    }
    return NULL;
}
```

关键观察：

1. **hook 在最前面**：这就是为什么 `__malloc_hook` 劫持有效——它在所有分配逻辑之前被调用（2.34 前）。
2. **tcache 在 arena 锁之前**：tcache 是 per-thread 的，无需加锁，这是它快的原因。
3. **`_int_malloc` 是真正的分配器**。

### 1.2.1 tcache_get 的源码（2.31）

```c
static void *tcache_get (size_t tc_idx) {
    tcache_entry *e = tcache->entries[tc_idx];
    assert (tc_idx < TCACHE_MAX_BINS);
    assert (e && e->next);
    tcache->entries[tc_idx] = e->next;   // 链表头后移
    --(tcache->counts[tc_idx]);
    e->key = NULL;                        // 清空 key（2.29+）
    return (void *) e;
}
```

注意 `e->key = NULL`——取出时会清空 key。这就是为什么 double free 时第二次 free 能通过 key 检查（因为 key 被清了）。

---

## 1.3 _int_malloc：核心分配逻辑

`_int_malloc` 有 400 多行，我们按流程拆解：

```c
static void *_int_malloc (mstate av, size_t bytes) {
    INTERNAL_SIZE_T nb;               // 标准化后的 size
    mchunkptr victim;
    ...
    
    // 第一步：标准化请求大小
    if (!checked_request2size (bytes, &nb)) {
        return NULL;
    }

    // 第二步：检查 fastbin
    if ((unsigned long) (nb) <= (unsigned long) (get_max_fast ())) {
        idx = fastbin_index (nb);
        mfastbinptr *fb = &fastbin (av, idx);
        victim = *fb;
        if (victim != NULL) {
            // 从 fastbin 取，检查 size 是否匹配
            ...
        }
    }

    // 第三步：检查 smallbin
    if (in_smallbin_range (nb)) {
        idx = smallbin_index (nb);
        bin = bin_at (av, idx);
        if ((victim = last (bin)) != bin) {
            // 取 smallbin 最后一个（FIFO）
            ...
        }
    }

    // 第四步：遍历 unsorted bin
    for (;;) {
        victim = unsorted_chunks (av)->bk;
        ...
        // 找到合适的就返回，不合适的归类到 smallbin/largebin
    }

    // 第五步：从 largebin 找
    ...

    // 第六步：从 top chunk 切
    ...
}
```

### 1.3.1 request2size 的细节

```c
#define request2size(req) \
    (((req) + SIZE_SZ + MALLOC_ALIGN_MASK < MINSIZE) ? MINSIZE : \
     ((req) + SIZE_SZ + MALLOC_ALIGN_MASK) & ~MALLOC_ALIGN_MASK)
```

在 64 位系统：`SIZE_SZ = 8`，`MALLOC_ALIGN_MASK = 15`。

计算过程：

```text
malloc(0x18) → 0x18 + 8 + 15 = 0x2f → & ~15 → 0x30
malloc(0x28) → 0x28 + 8 + 15 = 0x3f → & ~15 → 0x40
```

用户可用空间 = `size - 8`（因为下一个 chunk 的 prev_size 被借用）。

> ⚠️ **关键点**：`checked_request2size` 会检查 `bytes` 是否过大（溢出）。如果传入一个接近 `SIZE_MAX` 的值，会返回 NULL。这在某些利用中要考虑。

### 1.3.2 fastbin 分配的检查

```c
if (victim != 0) {
    if (__builtin_expect (fastbin_index (chunksize (victim)) != idx, 0)) {
        malloc_printerr ("malloc(): memory corruption (fast)");
    }
    // 检查对齐（2.27+）
    if (__builtin_expect ((uintptr_t) victim & 0xf, 0)) {
        malloc_printerr ("malloc(): unaligned fastbin chunk detected");
    }
    // 取出
    *fb = REVEAL_PTR (victim->fd);   // 2.32+ 使用 REVEAL_PTR 解码
    ...
}
```

**2.31 的检查**：只检查 size 是否匹配 fastbin 索引，不检查对齐。
**2.32+ 的检查**：加了对齐检查（地址必须 0x10 对齐），并使用 `REVEAL_PTR` 解码 safe-linking 的指针。

> 💡 **这就是 fastbin attack 在 2.32+ 失效的原因之一**：伪造的 chunk 地址必须 0x10 对齐，且 fd 要经过 safe-linking 编码。

### 1.3.3 unsorted bin 的遍历

这是最复杂的部分，也是 unsorted bin attack 的舞台：

```c
while ((victim = unsorted_chunks (av)->bk) != unsorted_chunks (av)) {
    bck = victim->bk;
    size = chunksize (victim);

    // 检查 1：size 合法性
    if (__glibc_unlikely (size <= 2 * SIZE_SZ) ||
        __glibc_unlikely (size > av->system_mem)) {
        malloc_printerr ("malloc(): invalid size (unsorted)");
    }
    
    // 检查 2：bk 的 fd 是否指回 victim（2.29+ 的检查！）
    if (__glibc_unlikely (bck->fd != victim)) {
        malloc_printerr ("malloc(): corrupted unsorted chunks");
    }

    // last_remainder 优化：如果 victim 是最后一个剩余块且够大，切一块返回
    if (in_smallbin_range (nb) &&
        bck == unsorted_chunks (av) &&
        victim == av->last_remainder &&
        (unsigned long) (size) > (unsigned long) (nb + MINSIZE)) {
        // 切割
        remainder_size = size - nb;
        remainder = chunk_at_offset (victim, nb);
        ...
        return p;
    }

    // 移除 victim（unlink）
    unsorted_chunks (av)->bk = bck;
    bck->fd = unsorted_chunks (av);

    // 如果大小刚好，直接返回
    if (size == nb) {
        ...
        return victim;
    }

    // 否则放到对应的 smallbin/largebin
    if (in_smallbin_range (size)) {
        victim_index = smallbin_index (size);
        bck = bin_at (av, victim_index);
        fwd = bck->fd;
    } else {
        // largebin 的插入（复杂）
        ...
    }
    // 插入操作
    victim->fd = fwd;
    victim->bk = bck;
    fwd->bk = victim;
    bck->fd = victim;
}
```

**关键检查**：

```c
if (bck->fd != victim) {
    malloc_printerr ("malloc(): corrupted unsorted chunks");
}
```

这就是为什么 unsorted bin attack 在 **glibc 2.29+ 失效**——我们伪造 `victim->bk = target - 0x10` 时，`bck->fd`（即 `target`）不会等于 victim，触发检查。

> ⚠️ **版本对照**：基础版讲的 unsorted bin attack（改 global_max_fast）只在 2.28 及之前有效。2.29+ 需要改用 largebin attack。

### 1.3.4 从 top chunk 分配

```c
use_top:
    victim = av->top;
    size = chunksize (victim);

    if ((unsigned long) (size) >= (unsigned long) (nb + MINSIZE)) {
        remainder_size = size - nb;
        remainder = chunk_at_offset (victim, nb);
        av->top = remainder;
        set_head (victim, nb | PREV_INUSE);
        set_head (remainder, remainder_size | PREV_INUSE);
        return p;
    }
    
    // top chunk 不够，扩展或 mmap
    ...
```

**House of Force 的原理就在这里**：如果能把 `av->top` 的 size 改成超大值，`size >= nb + MINSIZE` 永远成立，`chunk_at_offset(victim, nb)` 可以指向任意地址（通过整数溢出），从而返回任意地址。

**2.29+ 的检查**：

```c
if (__glibc_unlikely (size <= 2 * SIZE_SZ)) {
    malloc_printerr ("malloc(): corrupted top size");
}
```

top chunk 的 size 必须大于 `2 * SIZE_SZ`（16 字节），改成 `-1` 虽然很大但 certain 检查会绕过？实际上 2.29+ 主要检查 top chunk 的 size 不能太小，House of Force 的核心失效是因为后来的对齐检查增强。具体实现因版本而异，需要实际测试。

---

## 1.4 一次完整分配的调试验证

写一个程序，跟踪每次分配：

```c
// trace_malloc.c
#include <stdlib.h>
#include <stdio.h>

int main() {
    char *a = malloc(0x10);
    char *b = malloc(0x20);
    char *c = malloc(0x500);
    printf("a=%p b=%p c=%p\n", a, b, c);
    free(a);
    free(b);
    free(c);
    return 0;
}
```

用 gdb 在 `_int_malloc` 下断点：

```gdb
b _int_malloc
run
# 每次 malloc 都会停在这里
# 查看参数
p/x bytes
# 单步跟踪，观察它走了哪条路径
```

用 `info source` 和 `list` 查看源码（如果 glibc 有调试符号）：

```gdb
info source
list _int_malloc
```

---

## 1.5 小结

这一章我们读完了 malloc 的核心源码：

- `__libc_malloc` → hook → tcache → arena → `_int_malloc`
- `_int_malloc` 的路径：fastbin → smallbin → unsorted bin → largebin → top chunk
- **unsorted bin 的 `bck->fd != victim` 检查**（2.29+）让 unsorted bin attack 失效
- **fastbin 的对齐检查**（2.32+）和 safe-linking 让 fastbin attack 更困难
- **top chunk 的检查**让 House of Force 失效

理解源码的最大价值是：**当某个攻击失效时，你能立刻知道是哪一行检查拦住了你，从而有的放矢地找绕过。**

下一章我们读 free 的源码，看看 chunk 回收时的检查和逻辑。

---

**下一章**：[free 的真相：_int_free 与 chunk 回收路径](./ch02-free源码.md)
