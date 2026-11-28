# 第 2 章 free 的真相：_int_free 与 chunk 回收路径

> free 不是简单地「把内存标记为可用」。它要检查合法性、尝试合并、决定放入哪个 bin——每一步都有检查，每一步都有可利用的空间。

---

## 2.1 __libc_free 的入口

```c
void __libc_free (void *mem) {
    mstate ar_ptr;
    mchunkptr p;

    // 1. hook（2.34 之前）
    void (*hook) (void *, const void *) = atomic_forced_read (__free_hook);
    if (__builtin_expect (hook != NULL, 0)) {
        (*hook)(mem, RETURN_ADDRESS (0));
        return;
    }

    // 2. NULL 直接返回
    if (mem == 0) return;

    // 3. 转换用户指针为 chunk 指针
    p = mem2chunk (mem);

    // 4. mmap 分配的 chunk 单独处理
    if (chunk_is_mmapped (p)) {
        munmap_chunk (p);
        return;
    }

    // 5. 获取 arena
    ar_ptr = arena_for_chunk (p);

    // 6. 核心释放
    _int_free (ar_ptr, p, 0);
}
```

关键点：`mem2chunk(mem)` 就是 `mem - 16`（64 位），即用户指针往前退 16 字节找到 chunk 头。

---

## 2.2 _int_free 的核心逻辑

`_int_free` 的流程（glibc 2.31）：

```c
static void _int_free (mstate av, mchunkptr p, int have_lock) {
    INTERNAL_SIZE_T size;
    mchunkptr nextchunk;
    
    size = chunksize (p);

    // ====== 检查 1：基本合法性 ======
    if (__builtin_expect ((uintptr_t) p > (uintptr_t) -size, 0) ||
        __builtin_expect ((uintptr_t) p & 0xf, 0) ||
        __builtin_expect (misaligned_chunk (p), 0)) {
        malloc_printerr ("free(): invalid pointer");
    }
    if (__glibc_unlikely (size < MINSIZE || !aligned_OK (size))) {
        malloc_printerr ("free(): invalid size");
    }

    // ====== 2. tcache 优先处理 ======
    tcache_free_entry (av, p, size);
    // 伪代码：如果 size 在 tcache 范围内且 tcache 未满：
    //   进行 double free 检查（key 检查）
    //   放入 tcache，设置 key
    //   return

    // ====== 3. fastbin 处理 ======
    if ((unsigned long) (size) <= get_max_fast ()) {
        // 检查下一个 chunk 的 size
        nextchunk = chunk_at_offset (p, size);
        if (__glibc_unlikely (p == av->top)) {
            malloc_printerr ("double free or corruption (top)");
        }
        if (__glibc_unlikely (nextchunk == av->top)) {
            // 相邻 top chunk 检查
        }
        // 检查 nextchunk 的 size
        if (__glibc_unlikely (chunksize (nextchunk) <= 2 * SIZE_SZ)) {
            malloc_printerr ("free(): invalid next size (fast)");
        }
        
        // 检查 fastbin 链表头是否是同一个 chunk（double free 检查）
        if (__glibc_unlikely (old == p)) {
            malloc_printerr ("double free or corruption (fasttop)");
        }

        // 放入 fastbin
        p->fd = *fb;
        *fb = p;
        return;
    }

    // ====== 4. 合并与放入 bins ======
    // 检查 nextchunk 的 PREV_INUSE 位
    if (!prev_inuse(p)) {
        // 向前合并：前一个 chunk 是空闲的
        prevsize = p->prev_size;
        p = chunk_at_offset (p, -prevsize);   // 回退到前一个 chunk
        unlink (p, bck, fwd);                 // 从 bin 中摘除
    }

    // 检查下一个 chunk 是否空闲
    nextchunk = chunk_at_offset (p, size);
    if (!nextinuse) {
        // 向后合并
        unlink (nextchunk, bck, fwd);
        size += nextsize;
    }

    // 放入 unsorted bin
    bck = unsorted_chunks (av);
    fwd = bck->fd;
    p->fd = fwd;
    p->bk = bck;
    fwd->bk = p;
    bck->fd = p;
    
    // 检查
    if (__glibc_unlikely (fwd->bk != bck)) {
        malloc_printerr ("free(): corrupted unsorted chunks");
    }
}
```

---

## 2.3 tcache_free 的源码（2.31）

tcache 的释放逻辑是最常被利用的地方：

```c
static void tcache_put (mchunkptr chunk, size_t tc_idx) {
    tcache_entry *e = (tcache_entry *) chunk2mem (chunk);

    // 检查 tcache 是否已满
    if (tcache->counts[tc_idx] >= mp_.tcache_count) return;  // 满了就不放

    // 设置 key
    e->key = tcache;
    
    // 链接到链表头
    e->next = tcache->entries[tc_idx];
    tcache->entries[tc_idx] = e;
    ++(tcache->counts[tc_idx]);
}
```

在 `__libc_free` 中的 tcache 处理：

```c
// 检查 key，防止 double free
if (__glibc_unlikely (e->key == tcache)) {
    tcache_entry *tmp;
    // 遍历链表，确认是否真的在链表中
    for (tmp = tcache->entries[tc_idx]; tmp; tmp = tmp->next) {
        if (tmp == e) {
            malloc_printerr ("free(): double free detected in tcache 2");
        }
    }
}
```

**2.31 的 key 检查**：不只是比较 key，还**遍历链表**确认。所以即使把 key 清零，如果 chunk 真的在链表里，第二次 free 还是会被检测到！

> ⚠️ **这与 2.29 不同**：2.29 只检查 key，清零即可绕过；2.31 会遍历链表，所以经典的「清 key → 再次 free」在 2.31 的某些实现下可能失效。实际做题时需要测试。不过在 2.31 的 Ubuntu 发行版中，遍历检查通常存在，需要更复杂的方法（比如先 malloc 出来再从 tcache 移除，或者用其他 chunk 的 fd 伪造）。

### 2.3.1 safe-linking（2.32+）

从 glibc 2.32 开始，tcache 和 fastbin 的 fd/next 指针被编码：

```c
// PROTECT_PTR：把 next 指针编码
#define PROTECT_PTR(pos, ptr) \
    ((__typeof (ptr)) ((((size_t) pos) >> 12) ^ ((size_t) ptr)))

// REVEAL_PTR：解码
#define REVEAL_PTR(ptr) PROTECT_PTR (&ptr, ptr)
```

`tcache_put` 中：

```c
e->next = PROTECT_PTR (&e->next, tcache->entries[tc_idx]);
```

`tcache_get` 中：

```c
tcache->entries[tc_idx] = REVEAL_PTR (e->next);
```

**意义**：攻击者不知道 chunk 自身的地址，就无法伪造出正确的编码后的 fd。这大幅提高了 tcache poisoning 的难度——你需要先泄露堆地址。

---

## 2.4 合并（consolidate）的源码

向前合并（backward consolidate）：

```c
if (!prev_inuse(p)) {
    prevsize = prev_size (p);
    size += prevsize;
    p = chunk_at_offset (p, -prevsize);
    
    // 检查 prev_size 是否合法
    if (__glibc_unlikely (chunksize(p) != prevsize)) {
        malloc_printerr ("corrupted size vs. prev_size");
    }
    
    // 从 bin 中摘除前一个 chunk
    unlink (p, bck, fwd);
}
```

**House of Einherjar 的原理**：通过 off-by-one 清除 `PREV_INUSE` 位，并伪造 `prev_size`，让 free 时合并不存在的「前一个空闲 chunk」，从而把 chunk 指针移动到伪造的位置。

**2.29+ 的检查**：

```c
if (chunksize(p) != prevsize) {
    malloc_printerr ("corrupted size vs. prev_size");
}
```

伪造的 prev_size 必须和前一个位置的 size 字段一致——这让 House of Einherjar 更难，但并非不可绕过（如果能控制伪造位置的 size）。

---

## 2.5 从源码看常见漏洞的本质

| 漏洞 | 源码中的根源 |
| --- | --- |
| tcache dup | `tcache_put` 只检查 key，不清空就重复 put |
| tcache poisoning | `tcache_get` 直接信任 `e->next` 作为下一个链表头 |
| fastbin attack | `p->fd` 直接作为下一个 fastbin 的指针（2.32 前） |
| UAF | free 后 chunk 的 fd/bk 字段被写入，但用户指针还在 |
| House of Force | `_int_malloc` 从 top chunk 切时不检查目标地址合法性 |
| off-by-one | `prev_size` 和 `PREV_INUSE` 被 nextchunk 的 size 字段解释 |

---

## 2.6 调试验证

用 gdb 跟踪 `_int_free` 的执行路径：

```gdb
b _int_free
run
# 查看参数
p/x p
p/x chunksize(p)

# 单步，观察它走进哪个分支
# 查看 tcache 状态
tcache

# 查看 bins
bins
```

> 🔥 **实战**：编译一个简单的程序，分别 free 一个 0x20 的 chunk（进 tcache）、一个 0x500 的 chunk（进 unsorted bin）、两个相邻的 chunk（触发合并），用 gdb 单步跟踪 `_int_free`，对照源码看它走了哪条路径。

---

## 2.7 小结

这一章我们读完了 free 的源码：

- `__libc_free` → hook → NULL 检查 → mmap 检查 → `_int_free`
- `_int_free` 的路径：tcache → fastbin → 合并 → unsorted bin
- **tcache 的 key 检查**（2.29+）和 **safe-linking**（2.32+）让 tcache 利用更难
- **合并时的 prev_size 检查**（2.29+）让 House of Einherjar 更难
- 每个漏洞都能在源码中找到对应的「信任假设」

下一章我们专门深入 tcache 的源码，把 key 和 safe-linking 讲透。

---

**下一章**：[tcache 源码全解：从 key 到 safe-linking](./ch03-tcache源码.md)
