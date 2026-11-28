# 附录 C：高级调试技巧

## pwndbg 高级命令

```gdb
# 堆相关
heap                          # 显示所有 chunk
vis_heap_chunks               # 可视化
bins / tcache / fastbins      # 各类 bin
find_fake_fast 地址 size       # 找 fake chunk

# IO_FILE 相关
p *(struct _IO_FILE_plus*)&_IO_2_1_stdout_
p _IO_list_all
p _IO_wfile_jumps

# 源码级调试
list                          # 显示源码（需调试符号）
info source
```

## 源码级调试 glibc

```bash
# 安装带调试符号的 glibc
sudo apt install libc6-dbg

# 下载对应版本源码并关联
# gdb 中设置源码路径
directory /path/to/glibc-2.35/malloc
```

## safe-linking 手动计算

```python
def protect(pos, ptr):
    return (pos >> 12) ^ ptr

def reveal(pos, encoded):
    return (pos >> 12) ^ encoded

# 伪造 fd
fake_fd = protect(chunk_user_addr, target_addr)
```

## 常用断点

```gdb
b _int_malloc
b _int_free
b tcache_put
b tcache_get
b _IO_flush_all_lockp
b _IO_wfile_overflow
```

## 追踪全局变量

```gdb
watch *_IO_list_all
watch *(void**)&__free_hook
```

---

**提示**：高级利用的本质是精确定位和验证。善用断点观察源码中每一步的实际执行。
