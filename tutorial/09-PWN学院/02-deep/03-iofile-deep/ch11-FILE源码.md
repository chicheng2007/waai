# 第 11 章 FILE 结构体源码全解析

> 要玩转 IO_FILE 利用，必须把 FILE 结构体的每个字段刻在脑子里。这一章逐字段解析。

---

## 11.1 struct _IO_FILE 完整定义

glibc 2.35（`libio/bits/types/struct_FILE.h`）：

```c
struct _IO_FILE {
    int _flags;                /* 0x00: 标志位，_IO_MAGIC = 0xFBAD0000 */
    
    char *_IO_read_ptr;        /* 0x08: 当前读位置 */
    char *_IO_read_end;        /* 0x10: 读结束位置 */
    char *_IO_read_base;       /* 0x18: 读缓冲区起始 */
    
    char *_IO_write_base;      /* 0x20: 写缓冲区起始 */
    char *_IO_write_ptr;       /* 0x28: 当前写位置 */
    char *_IO_write_end;       /* 0x30: 写结束位置 */
    
    char *_IO_buf_base;        /* 0x38: 缓冲区起始 */
    char *_IO_buf_end;         /* 0x40: 缓冲区结束 */
    
    char *_IO_save_base;       /* 0x48 */
    char *_IO_backup_base;     /* 0x50 */
    char *_IO_save_end;        /* 0x58 */
    
    struct _IO_marker *_markers;  /* 0x60 */
    struct _IO_FILE *_chain;      /* 0x68: 链表指针 */
    
    int _fileno;               /* 0x70: 文件描述符 */
    int _flags2;               /* 0x74 */
    
    __off_t _old_offset;       /* 0x78 */
    
    unsigned short _cur_column;  /* 0x80 */
    signed char _vtable_offset;  /* 0x82 */
    char _shortbuf[1];           /* 0x83 */
    
    _IO_lock_t *_lock;         /* 0x88 */
    
    __off64_t _offset;         /* 0x90 */
    
    struct _IO_codecvt *_codecvt;          /* 0x98 */
    struct _IO_wide_data *_wide_data;      /* 0xa0（2.35）/ 0x88（2.31） */
    struct _IO_FILE *_freeres_list;        /* 0xa8 */
    void *_freeres_buf;                    /* 0xb0 */
    size_t __pad5;                         /* 0xb8 */
    
    int _mode;                 /* 0xc0 */
    char _unused2[20];         /* 0xc4 */
};
```

> ⚠️ **重要**：`_wide_data` 的偏移在不同版本不同！2.31 是 0x88，2.35 是 0xa0。构造 House of Apple 时必须确认。

### 11.1.1 _IO_FILE_plus 与 vtable

```c
struct _IO_FILE_plus {
    FILE file;
    const struct _IO_jump_t *vtable;   /* 紧跟在 FILE 后面 */
};
```

vtable 指针在 `0xd8`（2.31/2.35 相同，因为 FILE 本身是 0xd8 字节）。

---

## 11.2 关键字段的利用价值

| 字段 | 偏移 | 利用价值 |
| --- | --- | --- |
| `_flags` | 0x00 | 控制 FILE 行为；作为 system 参数 |
| `_IO_write_base` | 0x20 | stdout 泄露：起始地址 |
| `_IO_write_ptr` | 0x28 | stdout 泄露：结束地址；触发 overflow 条件 |
| `_IO_buf_base` | 0x38 | 读写缓冲区 |
| `_chain` | 0x68 | FSOP 链表 |
| `_fileno` | 0x70 | 文件描述符 |
| `_wide_data` | 0xa0 | House of Apple 的关键 |
| `vtable` | 0xd8 | 控制流劫持 |

---

## 11.3 用 gdb 查看 FILE 结构

```gdb
# 查看 stdout 的 FILE 结构
p _IO_2_1_stdout_
p *(struct _IO_FILE_plus*)&_IO_2_1_stdout_

# 查看特定字段
p/x _IO_2_1_stdout_._flags
p _IO_2_1_stdout_._chain
p/x _IO_2_1_stdout_.vtable

# 查看 vtable 内容
p _IO_file_jumps
p _IO_wfile_jumps
```

---

## 11.4 flags 的构造

常见的合法 flags：

```c
#define _IO_MAGIC         0xFBAD0000
#define _IO_NO_READS      0x0004
#define _IO_NO_WRITES     0x0008
#define _IO_CURRENTLY_PUTTING 0x0800
#define _IO_LINE_BUF      0x0200
#define _IO_UNBUFFERED    0x0002
```

stdout 的典型 flags：`0xfbad2084` 或 `0xfbad2887`。

构造伪造 FILE 时常用的 flags：

```python
flags = 0xfbad0000 | 0x1880   # magic + currently_putting + line_buf
```

---

## 11.5 小结

这一章我们逐字段解析了 FILE 结构体：

- FILE 结构约 0xd8 字节，vtable 在 0xd8
- 关键字段：write_base/write_ptr（泄露）、_chain（FSOP）、_wide_data（House of Apple）
- `_wide_data` 偏移在 2.31 和 2.35 不同（0x88 vs 0xa0）

下一章我们梳理 vtable 检查的演化史，理解 House of Apple 为什么能绕过。

---

**下一章**：[vtable 检查的演化与绕过](./ch12-vtable演化.md)
