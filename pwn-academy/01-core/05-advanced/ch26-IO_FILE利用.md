# 第 26 章 IO_FILE 利用：Stream 的黑暗面

> 当 glibc 移除了 malloc_hook 和 free_hook，攻击者把目光投向了另一个几乎每个程序都会用到的结构：IO_FILE。一切从 `printf`、`puts`、`fread` 背后的那个 FILE 结构体开始。

---

## 26.1 为什么需要 IO_FILE 利用

从 glibc 2.34 开始，`__malloc_hook`、`__free_hook`、`__realloc_hook` 被全部移除。堆利用的「终点站」消失了。

但程序总要输出信息——`puts`、`printf`、`puts` 背后都依赖 **FILE 结构体**。如果能控制一个 FILE 结构，就能在程序进行 IO 操作时劫持控制流。这就是 IO_FILE 利用。

**IO_FILE 利用的两大用途**：

1. **信息泄露**：伪造 `_IO_2_1_stdout_`，让程序输出任意地址的内存
2. **控制流劫持**：通过 vtable 或 `_IO_list_all` 触发任意代码执行

---

## 26.2 FILE 结构体

glibc 用 `struct _IO_FILE` 表示一个 IO 流（在 `libio/bits/types/struct_FILE.h` 中定义）：

```c
struct _IO_FILE {
    int _flags;               // 标志位（0x0 - 0x4）
    char *_IO_read_ptr;       // 读指针（0x8）
    char *_IO_read_end;
    char *_IO_read_base;
    char *_IO_write_base;     // 写缓冲区起始（0x20）
    char *_IO_write_ptr;      // 写缓冲区当前位置（0x28）
    char *_IO_write_end;
    char *_IO_buf_base;       // 缓冲区起始（0x38）
    char *_IO_buf_end;        // 缓冲区结束（0x40）
    ...
    struct _IO_FILE *_chain;  // 链表指针（0x68），指向下一个 FILE
    int _fileno;              // 文件描述符（0x70）
    ...
};
```

关键的几个字段：

| 偏移 | 字段 | 作用 |
| --- | --- | --- |
| 0x0 | `_flags` | 控制 FILE 的行为模式 |
| 0x20 | `_IO_write_base` | 输出缓冲区起始地址 |
| 0x28 | `_IO_write_ptr` | 输出缓冲区当前位置 |
| 0x38 | `_IO_buf_base` | 缓冲区基址 |
| 0x40 | `_IO_buf_end` | 缓冲区结束地址 |
| 0x68 | `_chain` | FILE 链表指针 |
| 0x70 | `_fileno` | 文件描述符 |

程序中的 `stdout`、`stdin`、`stderr` 分别对应全局的 `_IO_2_1_stdout_`、`_IO_2_1_stdin_`、`_IO_2_1_stderr_` 结构，它们通过 `_chain` 串成链表，链表头是 `_IO_list_all`。

---

## 26.3 泄露任意地址：伪造 stdout

### 26.3.1 原理

`puts` 输出数据时，会调用 `_IO_new_file_xsputn`，它根据 `_IO_write_base` 和 `_IO_write_ptr` 决定输出多少数据：

```c
// 简化逻辑
to_do = write_ptr - write_base;  // 要输出的字节数
write(fd, write_base, to_do);     // 从 write_base 开始输出
```

如果我们能控制 `_IO_2_1_stdout_` 的 `_IO_write_base` 和 `_IO_write_ptr`，让它们分别指向「目标地址」和「目标地址 + N」，那么下次调用 `puts` 时，程序就会**输出目标地址的 N 字节数据**——这就是任意地址读！

### 26.3.2 构造伪造的 stdout

经典的伪造技巧是把 `_flags` 设置为 `0xfbad0000 | 0x1800`（绕过检查的关键位），然后设置：

```text
_flags        = 0xfbad1800    （让 puts 认为这是一个可写的 stdout）
_IO_write_base = target_addr  （要泄露的地址）
_IO_write_ptr  = target_addr + length
_IO_buf_base   = target_addr
_IO_buf_end    = target_addr + length
```

用 pwntools 构造：

```python
fake_stdout = flat({
    0x00: 0xfbad1800,            # flags
    0x18: target_addr,           # _IO_write_base（注意偏移调整）
    0x20: target_addr + 8,       # _IO_write_ptr
    0x38: target_addr,           # _IO_buf_base
})
```

> ⚠️ **注意**：不同 glibc 版本的 `_IO_FILE` 结构体布局略有不同（glibc 2.35 有 `_IO_FILE_plus` 和 `_wide_data` 的变化），构造时必须对照目标 libc 的结构体定义。

### 26.3.3 利用步骤

```text
1. 通过 tcache poisoning 分配到 _IO_2_1_stdout_ 附近
2. 写入伪造的 FILE 结构（控制 write_base/write_ptr）
3. 程序下次调用 puts/printf 时，输出目标地址的内存
4. 泄露 libc 地址或栈地址
```

---

## 26.4 FSOP：控制流劫持

**FSOP（File Structure Oriented Programming）** 是 IO_FILE 利用的核心思想：操控 `_IO_list_all` 链表，让程序在 exit 或 IO 操作时执行我们伪造的 FILE 结构里的函数。

### 26.4.1 _IO_list_all 与 _chain

`_IO_list_all` 指向 FILE 链表的头（通常是 `stderr`）。每个 FILE 结构通过 `_chain` 字段指向下一个。

程序退出时会调用 `_IO_flush_all_lockp`，它遍历 `_IO_list_all`，对每个 FILE 调用 `_IO_OVERFLOW`（通过 vtable 间接调用）。

**漏洞**：如果伪造一个 FILE 结构，把它的 vtable 指针指向我们控制的内存（里面放 one_gadget 或 system），就能在 exit 时执行任意代码。

### 26.4.2 vtable 检查与绕过

glibc 2.24+ 加入了 vtable 检查：vtable 指针必须位于 `__libc_IO_vtables` 段内，不能直接指向堆或 bss。

绕过方法：

- **覆盖 vtable 指针为 `__libc_IO_vtables` 里的合法地址**，但让该地址处的函数指针指向我们控制的逻辑
- **House of Apple**：利用 `_IO_wfile_overflow` 等函数内部的二次跳转，绕过 vtable 检查（glibc 2.35 主流技术）

### 26.4.3 简化版利用（glibc 2.31）

```python
# 1. 伪造 FILE 结构
fake_file = b'/bin/sh\x00'           # _flags
fake_file += p64(0) * 12             # 填充到 vtable 位置
fake_file += p64(fake_vtable_addr)   # vtable 指针（需指向合法 vtable 附近）

# 2. 通过 largebin attack 修改 _IO_list_all 指向 fake_file
# 3. 触发 exit 或 abort → _IO_flush_all_lockp → 调用我们的 vtable 函数
```

---

## 26.5 IO_FILE 利用的学习路径

IO_FILE 利用是 PWN 中最复杂的主题之一，建议按以下顺序学习：

1. **理解 FILE 结构体**：用 gdb 查看 `_IO_2_1_stdout_`，观察每个字段的含义
2. **掌握 stdout 泄露**：伪造 write_base/write_ptr，实现任意地址读
3. **理解 vtable 机制**：看 `_IO_FILE_plus` 和 `_IO_jump_t` 结构
4. **学习 FSOP**：理解 `_IO_flush_all_lockp` 的执行流程
5. **House of Apple**：glibc 2.35 下的现代利用技术

> 💡 **提示**：IO_FILE 利用涉及大量 libc 源码阅读。建议边读教程边看 glibc 源码（https://sourceware.org/git/?p=glibc.git），尤其是 `libio/` 目录下的文件。

---

## 26.6 小结

这一章我们初步了解了 IO_FILE 利用：

- **背景**：glibc 2.34+ 移除了 hooks，IO_FILE 成为新的利用目标
- **FILE 结构体**：包含 flags、读写缓冲区指针、_chain、vtable 等关键字段
- **泄露任意地址**：伪造 stdout 的 write_base/write_ptr
- **FSOP**：通过 `_IO_list_all` 和 vtable 劫持控制流
- **vtable 检查**：glibc 2.24+ 引入，需要 House of Apple 等技术绕过

下一章我们学习 House of 系列进阶（House of Orange、House of Apple 等），把 IO_FILE 利用讲得更深入。

---

**下一章**：[House of 系列进阶](./ch27-House系列进阶.md)
