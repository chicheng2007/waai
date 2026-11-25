# 附录 A：各版本 glibc 源码索引

## 在线源码

- glibc 官方 Git：https://sourceware.org/git/?p=glibc.git
- 按版本 tag 查看：https://sourceware.org/git/?p=glibc.git;a=tags
- 下载：https://ftp.gnu.org/gnu/glibc/

## 关键文件与函数

| 文件 | 关键函数/结构 | 说明 |
| --- | --- | --- |
| `malloc/malloc.c` | `__libc_malloc`, `_int_malloc`, `__libc_free`, `_int_free` | malloc/free 核心 |
| `malloc/malloc.c` | `tcache_put`, `tcache_get` | tcache 操作 |
| `malloc/malloc.c` | `unlink` 宏 | 链表摘除 |
| `malloc/arena.c` | `arena_get`, `arena_for_chunk` | arena 管理 |
| `libio/fileops.c` | `_IO_file_xsputn`, `_IO_new_file_overflow` | 文件输出 |
| `libio/wfileops.c` | `_IO_wfile_overflow`, `_IO_wdoallocbuf` | House of Apple 关键 |
| `libio/genops.c` | `_IO_flush_all_lockp` | exit 时的 IO 刷新 |
| `libio/vtables.c` | `IO_validate_vtable` | vtable 检查 |
| `include/malloc.h` | `malloc_chunk`, `malloc_state` | 结构体定义 |

## 本地搭建源码阅读环境

```bash
# 下载源码
wget https://ftp.gnu.org/gnu/glibc/glibc-2.35.tar.gz
tar xf glibc-2.35.tar.gz
cd glibc-2.35

# 用 cscope/ctags 建立索引
sudo apt install cscope
find . -name '*.c' -o -name '*.h' > cscope.files
cscope -Rb

# 或用 VSCode + C/C++ 插件直接浏览
```

---

**提示**：读源码时，重点看检查语句（`__glibc_unlikely`、`malloc_printerr`），它们就是「攻防的边界」。
