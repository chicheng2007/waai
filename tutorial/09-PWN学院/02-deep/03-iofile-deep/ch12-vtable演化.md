# 第 12 章 vtable 检查的演化与绕过

> 理解 vtable 检查的历史，就理解了为什么现代 IO_FILE 利用长成现在这个样子。

---

## 12.1 时间线

### glibc 2.23 及之前：无检查

vtable 指针可以指向任意内存。攻击者伪造一个 vtable，把 `_overflow` 设为 system 地址，就能在 exit 时 getshell。

```python
fake_vtable = p64(0) * 1 + p64(system)   # _overflow 在 vtable 偏移 0x18
# 实际上 vtable 结构：
# 0x00: _dummy
# 0x08: _dummy
# 0x10: _dummy
# 0x18: _overflow
```

### glibc 2.24：引入 IO_validate_vtable

```c
static inline const struct _IO_jump_t *
IO_validate_vtable (const struct _IO_jump_t *vtable) {
    uintptr_t section_length = __stop___libc_IO_vtables - __start___libc_IO_vtables;
    uintptr_t ptr = (uintptr_t) vtable;
    uintptr_t offset = ptr - (uintptr_t) __start___libc_IO_vtables;
    if (__glibc_unlikely (offset >= section_length)) {
        return _IO_vtable_check ();
    }
    return vtable;
}
```

**检查**：vtable 指针必须位于 `__libc_IO_vtables` 段内（libc 数据段的一块只读区域）。

**第一 bypass**：把 vtable 指向 libc 内合法的 vtable，但修改它们的**内容**（如果可写）——通常不可写，所以失效。

### glibc 2.27：新的思路

攻击者发现：`_IO_str_jumps` vtable 里的 `_IO_str_overflow` 函数内部有 hack 空间。通过构造特定的 FILE，可以让 `_IO_str_overflow` 调用 `_IO_str_finish`，后者调用 `fp->_s._free_buffer(fp->_s._buffer)` —— 一个可控的函数指针。

```python
# 伪造 FILE，vtable 指向 _IO_str_jumps
# 设置 _s._free_buffer = system
# 设置 _s._buffer = "/bin/sh"
```

### glibc 2.28+：FSOP 的成熟

House of Orange + largebin attack 修改 `_IO_list_all` + 伪造 FILE + `_IO_str_jumps` 成为标准套路。

### glibc 2.34+：hooks 移除

hook 没了，但 IO_FILE 利用更成熟了。

### glibc 2.35：House of Apple

利用 `_IO_wfile_jumps` 和 `_wide_data` 的二次跳转，绕过 vtable 检查。

---

## 12.2 House of Apple 为什么能绕过

核心洞察：

```text
vtable 检查只检查 vtable 指针是否在 __libc_IO_vtables 段内
→ 指向 _IO_wfile_jumps（合法）通过检查
→ 但 _IO_wfile_overflow 内部会调用 _IO_WDOALLOCATE
→ 后者通过 _wide_data->_wide_vtable 间接调用
→ 这个间接调用不受 vtable 检查保护！
```

这是「二次跳转」的思想：第一层 vtable 检查通过，第二层跳转由我们控制。

```text
exit()
  → _IO_flush_all_lockp
  → vtable->_overflow = _IO_wfile_overflow  (合法 vtable，通过检查)
  → _IO_wdoallocbuf
  → _IO_WDOALLOCATE(fp)
  → fp->_wide_data->_wide_vtable->_doallocate(fp)
  → system(fp) 或 one_gadget  (我们的目标，无检查)
```

---

## 12.3 各版本绕过手法速查

| glibc 版本 | 主流绕过手法 |
| --- | --- |
| 2.23 | 任意 vtable 指针 |
| 2.24~2.27 | _IO_str_jumps + _IO_str_finish |
| 2.28~2.31 | House of Orange + FSOP + _IO_str_jumps |
| 2.32~2.33 | FSOP + _IO_str_jumps（safe-linking 增加难度） |
| 2.34 | hooks 移除，FSOP 成主流 |
| 2.35 | House of Apple（_IO_wfile_jumps + _wide_data） |

---

## 12.4 小结

这一章我们梳理了 vtable 检查的演化史：

- 2.23：无检查
- 2.24：vtable 必须在 libc 段内
- 2.27~2.31：利用 `_IO_str_jumps` 的内部调用
- 2.35：House of Apple 的二次跳转

**核心规律**：检查加在第一层，攻击者就找第二层；第二层被检查，就找第三层。攻防的螺旋上升。

下一章我们讲 stdout 泄露的多种姿势。

---

**下一章**：[stdout 泄露的多种姿势](./ch13-stdout泄露.md)
