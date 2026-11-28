# 第 4 章 bins 的维护：解链与入链的源码细节

> unlink 是 glibc 堆管理中最精妙也最容易出错的操作。所有「链表攻击」的本质，都是让 unlink 在伪造的指针上执行。

---

## 4.1 unlink 宏

glibc 的 unlink 宏（2.31 之前）：

```c
#define unlink(P, BK, FD) {                                            
    FD = P->fd;                                                        
    BK = P->bk;                                                        
    // 检查 1（2.29+ 加入）
    if (__builtin_expect (FD->bk != P || BK->fd != P, 0))             
        malloc_printerr ("corrupted double-linked list");              
    FD->bk = BK;                                                       
    BK->fd = FD;                                                       
    ...
}
```

**操作本质**：把 P 从双向链表中摘除，让 P 的前后节点直接相连。

```text
摘除前:  FD  <-->  P  <-->  BK
摘除后:  FD  <---------->  BK
```

### 4.1.1 检查的意义

```c
if (FD->bk != P || BK->fd != P) {
    malloc_printerr ("corrupted double-linked list");
}
```

这个检查验证「P 确实在 FD 和 BK 之间」。2.29 之前没有这个检查，所以经典的 **unlink attack**（伪造 fd/bk 让 `FD->bk = BK` 写入任意地址）很容易成功。

### 4.1.2 经典 unlink attack（已失效）

攻击者控制一个空闲 chunk P 的 fd 和 bk：

```text
P->fd = target_addr - 0x18
P->bk = fake_value

unlink 时：
FD = P->fd = target_addr - 0x18
BK = P->bk = fake_value
检查：FD->bk = (target_addr - 0x18 + 0x18) = target_addr 应该 == P
      → 需要 target_addr 处存放 P 的地址（可控时可满足）
      BK->fd = fake_value + 0x10 应该 == P
      → 需要 fake_value + 0x10 = P（即 fake_value = P - 0x10）

通过检查后：
FD->bk = BK → *(target_addr) = fake_value
BK->fd = FD → *(P) = target_addr - 0x18
```

**效果**：往 `target_addr` 写入了 `P - 0x10`（一个可控值）。

2.29+ 的检查让这变得困难，但并非完全不可能——如果能构造一个「合法的假链表」（让检查通过），仍然可以。这就是很多高级利用（largebin attack）的基础。

---

## 4.2 unsorted bin 的遍历

`_int_malloc` 中遍历 unsorted bin 的代码：

```c
while ((victim = unsorted_chunks (av)->bk) != unsorted_chunks (av)) {
    bck = victim->bk;
    size = chunksize (victim);

    // 检查 1：size 范围
    if (__glibc_unlikely (size <= 2 * SIZE_SZ) ||
        __glibc_unlikely (size > av->system_mem)) {
        malloc_printerr ("malloc(): invalid size (unsorted)");
    }
    
    // 检查 2：双链表完整性（2.29+）
    if (__glibc_unlikely (bck->fd != victim)) {
        malloc_printerr ("malloc(): corrupted unsorted chunks");
    }

    // last_remainder 优化
    if (in_smallbin_range (nb) &&
        bck == unsorted_chunks (av) &&
        victim == av->last_remainder &&
        size > nb + MINSIZE) {
        // 切割返回
        ...
    }

    // unlink
    unsorted_chunks (av)->bk = bck;
    bck->fd = unsorted_chunks (av);

    // 大小匹配则直接返回
    if (size == nb) {
        ...
        return p;
    }

    // 不匹配：归类到 smallbin 或 largebin
    ...
}
```

**unsorted bin attack 的失效原因**：

2.29+ 的 `bck->fd != victim` 检查。我们伪造 `victim->bk = target - 0x10`，则 `bck->fd = *(target)`，不等于 victim → 报错。

**绕过可能性**：如果 `*(target)` 恰好等于 victim 的地址（通过 prior 控制），检查可能通过。但这需要额外的写原语，通常不如直接用 largebin attack。

---

## 4.3 largebin 的插入逻辑

当 unsorted bin 中的 chunk 大小不属于 smallbin 范围时，会被放入 largebin：

```c
else {
    victim_index = largebin_index (size);
    bck = bin_at (av, victim_index);
    fwd = bck->fd;

    // 如果 largebin 不为空
    if (fwd != bck) {
        size_t vsize = size;
        
        // 从链表头开始找插入位置（按大小降序）
        while ((victim = victim->fd_nextsize) != NULL &&
               chunksize(victim) > vsize) {
            bck = victim;
        }
        
        if (__glibc_unlikely (size == chunksize(victim))) {
            // 大小相同：插入到 nextsize 链表中
            victim = bck;
            fwd = bck->fd;
        } else {
            // 大小不同：需要更新 fd_nextsize/bk_nextsize
            victim->fd_nextsize = ...;
            victim->bk_nextsize = ...;
            
            // 关键写入点（2.30 之前）
            fwd->bk_nextsize->fd_nextsize = victim;
            fwd->bk_nextsize = victim;
        }
    }
    
    // 双向链表插入
    victim->bk = bck;
    victim->fd = fwd;
    fwd->bk = victim;
    bck->fd = victim;
}
```

### 4.3.1 largebin attack 的原理

关键行：

```c
fwd->bk_nextsize->fd_nextsize = victim;  // 往 *(&bk_nextsize + 0x18) 写 victim 地址
```

如果控制 `fwd->bk_nextsize = target - 0x18`，就能往 `target` 写入 victim 的地址（堆地址）。

**glibc 2.31 还有一个写入点**：

```c
bck->fd = victim;  // 往 *(bck + 0x10) 写 victim 地址
```

控制 `bck = target - 0x10` 即可。

> ⚠️ **版本变化**：glibc 2.32+ 对 largebin 的插入检查更严格，部分写入点被加上了完整性检查。做题时必须针对具体版本调试。

---

## 4.4 House of Lore 的源码基础

House of Lore 利用 smallbin 的 bk 指针：

```c
// malloc 从 smallbin 取 chunk 时的代码
if ((victim = last (bin)) != bin) {
    if (victim == 0) {
        malloc_consolidate (av);
    } else {
        bck = victim->bk;
        // 2.29+ 的检查
        if (__glibc_unlikely (bck->fd != victim)) {
            malloc_printerr ("malloc(): smallbin double linked list corrupted");
        }
        set_inuse_bit_at_offset (victim, nb);
        bin->bk = bck;
        bck->fd = bin;
        return p;
    }
}
```

如果伪造 `victim->bk = fake_chunk - 0x10`，且能让 `bck->fd == victim` 检查通过（构造假链表），就能让 smallbin 的链表头指向 fake_chunk，下次 malloc 返回 fake_chunk。

---

## 4.5 源码中的「信任假设」总结

glibc 的堆管理信任以下假设：

1. **chunk 的 size 字段没被改** → off-by-one 打破
2. **fd/bk 指针指向合法的 chunk** → UAF/double free 打破
3. **链表结构完整** → 伪造 fd/bk 打破
4. **用户不会释放未分配的 chunk** → House of Spirit 打破
5. **用户不会改 top chunk 的 size** → House of Force 打破

每一代 glibc 的更新，都是在加强这些假设的检查。而每一代利用技术，都是在寻找检查的盲点。

---

## 4.6 小结

这一章我们深入分析了 bins 的源码：

- **unlink 宏**：双向链表摘除，2.29+ 加入 `FD->bk == P && BK->fd == P` 检查
- **unsorted bin 遍历**：`bck->fd != victim` 检查让 unsorted bin attack 失效
- **largebin 插入**：`fd_nextsize/bk_nextsize` 的写入点是 largebin attack 的基础
- **smallbin 取块**：`bck->fd != victim` 检查是 House of Lore 的障碍
- 所有攻击的本质都是**打破 glibc 的信任假设**

下一章我们总览检查机制的演化，梳理「猫鼠游戏」的规律。

---

**下一章**：[堆检查机制与绕过思路总览](./ch05-检查与绕过.md)
