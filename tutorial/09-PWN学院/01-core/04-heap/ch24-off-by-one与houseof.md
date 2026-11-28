# 第 24 章 off-by-one 与 House of 系列

> 只多写了一 1 字节，却可能撬动整个堆。off-by-one 是堆漏洞中最「小」的漏洞，也是最能体现「四两拨千斤」的一类。

---

## 24.1 off-by-one 漏洞

**off-by-one** 指写入数据时比目标缓冲区多写了 1 字节（off by one）。虽然只多 1 字节，但在堆里，这 1 字节往往正好落在下一个 chunk 的 size 字段上。

### 24.1.1 常见成因

```c
// 错误 1：循环条件用 <=
for (int i = 0; i <= size; i++) {
    buf[i] = data[i];   // 多写 1 字节
}

// 错误 2：字符串拷贝时把 \0 也算进去
strncpy(dst, src, sizeof(dst));  // 如果 src 长度 == sizeof(dst)，\0 会写到下一个 chunk
dst[sizeof(dst)] = '\0';

// 错误 3：用户输入长度计算错误
read(0, buf, size + 1);
```

### 24.1.2 null byte poisoning

如果 off-by-one 写入的是 `\x00`，会覆盖下一个 chunk 的 size 字段的最低字节：

```text
修改前：下一个 chunk 的 size = 0x91（PREV_INUSE=1）
修改后：size = 0x00（低字节被清零）

后果：
- 原本 0x91 → 0x00：size 变得极小
- 或者 0x101 → 0x100：size 变小，PREV_INUSE 位丢失
```

更经典的场景：off-by-one 把下一个 chunk 的 `PREV_INUSE` 位清零，让 glibc 误以为前一个 chunk 是空闲的，从而在 free 时触发**向后合并**（backward consolidate），把两个 chunk 合并成一个——即使前一个 chunk 其实还在用。

---

## 24.2 经典利用：shrink free chunk

off-by-one 的一个经典玩法是**缩小 chunk 的 size**，制造「堆块重叠」：

```text
1. 分配 chunk A（0x100）和 chunk B（0x100）
2. 通过 off-by-one 修改 A → B 的 size 字段，把 B 的 size 改小（比如 0x91 → 0x81）
3. free B → B 进入 bin，但只释放了较小的空间
4. 再 malloc 一个稍小的 chunk C → C 落在 B 原来的空间内
5. 但 B 的指针还在 → B 和 C 重叠 → 可以读写彼此的数据
```

这种「chunk 重叠」可以实现类似 UAF 的效果。

---

## 24.3 House of 系列概览

「House of XXX」是堆利用中一类经典技术的命名传统（源自一篇叫《The Malloc Maleficarum》的文章）。下面介绍几个重要的：

### 24.3.1 House of Force

**条件**：能修改 top chunk 的 size 字段。

**原理**：malloc 从 top chunk 分配内存时，会用 `request_size` 从 top chunk 的 size 里减去。如果把 top chunk 的 size 改成一个巨大的值（如 -1 或 0xffffffffffffffff），malloc 就能「分配」到任意地址（包括负数偏移）。

```python
# 1. 溢出修改 top chunk 的 size 为 -1
# 2. malloc 一个特定大小，使 top chunk 移动到目标地址附近
# 3. 再从目标地址分配 → 返回目标地址
```

**现状**：glibc 2.29+ 加入了对 top chunk size 的检查，House of Force 在 2.31 之后基本失效。

### 24.3.2 House of Einherjar

**条件**：off-by-one（null byte）+ 能控制一个 fake chunk。

**原理**：利用 off-by-one 清除下一个 chunk 的 PREV_INUSE 位，让 glibc 在 free 时认为前一个 chunk 空闲，触发向后合并。合并时会读取前一个 chunk（伪造的）的 `prev_size` 来决定合并后 chunk 的起始位置——如果伪造得当，合并后的 chunk 可以指向任意地址。

**效果**：制造一个指向任意地址的空闲 chunk，配合后续分配实现任意地址写。

### 24.3.3 House of Spirit

第 21 章讲过：伪造 chunk 让 free 收进 fastbin。

### 24.3.4 House of Orange

**条件**：能修改 top chunk 的 size 为一个较小的值（且不满足 mmap 条件）。

**原理**：当 top chunk 的 size 小于要分配的 size 时，glibc 会调用 `sysmalloc` 扩展堆。如果伪造 top chunk 的 size，可以触发特定的内存布局，最终让 unsorted bin 里出现一个 chunk（通常配合 FSOP 利用 `_IO_list_all`）。

House of Orange 是 FSOP 的经典前置技术。

### 24.3.5 House of Lore / Apple

- **House of Lore**：伪造 smallbin 的 bk 链表，实现任意地址分配
- **House of Apple**：glibc 2.35+ 下利用 IO_FILE 结构的新技术（第 27 章详讲）

---

## 24.4 off-by-one 实战示例

### 题目描述

一个程序用 `strncpy` 拷贝字符串，存在一个字节的溢出：

```c
void copy_data(char *dst, char *src) {
    strncpy(dst, src, 0x20);   // dst 只有 0x20 字节，但 strncpy 会写满 0x20
    // 如果 src 长度 >= 0x20，dst[0x20] 不会被写
    // 但常见的错误写法：dst[0x20] = '\0' → off-by-one null byte
}
```

### 利用思路

1. 分配 chunk A (0x28) 和 chunk B (0x28)
2. 通过 off-by-one 把 B 的 size 从 0x31 改成 0x00（null byte poisoning）
3. free B 时，glibc 会向上合并（认为 A 是空闲的，因为 size 被改了）
4. 制造堆块重叠，实现任意读写

实际利用需要根据程序的具体逻辑设计，这里给出思路框架：

```python
# 1. 布局堆
add(0, 0x28, b'A' * 0x28)   # chunk A
add(1, 0x28, b'B' * 0x28)   # chunk B

# 2. 触发 off-by-one，覆盖 B 的 size 低字节
trigger_off_by_one(0, b'\x00')

# 3. free B → 触发合并
delete(1)

# 4. 重新分配，制造重叠
add(2, 0x??, payload)
# ...
```

---

## 24.5 常见坑

1. **null byte 的位置**：off-by-one 写的位置必须精确落在下一个 chunk 的 size 字段上。如果 chunk 大小计算错误，写的位置就不对。
2. **glibc 的检查**：现代 glibc 对 chunk 的合并、size 都有严格检查，伪造时要满足这些条件。
3. **tcache 干扰**：小块 free 后进 tcache，不会触发合并。用大块或耗尽 tcache。

---

## 24.6 小结

这一章我们学了 off-by-one 和 House 系列：

- **off-by-one**：多写 1 字节，覆盖下一个 chunk 的 size 字段
- **null byte poisoning**：清零 PREV_INUSE 位，触发向后合并
- **House of Force**：修改 top chunk size 实现任意分配（2.29+ 失效）
- **House of Einherjar**：利用 off-by-one + 向后合并制造任意地址 chunk
- **House of Orange / Apple**：FSOP 的前置技术（后面详讲）

至此，堆利用的主要技术都讲完了。下一章我们做一个综合的堆风水实战，把这些技术串起来。

---

**下一章**：[堆风水实战](./ch25-堆风水实战.md)
