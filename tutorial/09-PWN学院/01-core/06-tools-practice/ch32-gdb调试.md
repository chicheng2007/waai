# 第 32 章 gdb 与 pwndbg 调试技巧

> 调试器是 PWN 选手的眼睛。这一章我们系统学习 gdb 和 pwndbg 的使用，让你能看到程序运行的每一个细节。

---

## 32.1 gdb 基础

### 32.1.1 启动

```bash
gdb ./vuln                    # 启动调试
gdb -q ./vuln                 # 静默模式（不显示版本信息）
gdb ./vuln core dumped        # 分析 core dump
gdb -p PID                    # 附加到运行中的进程
```

### 32.1.2 断点

```gdb
break main                    # 在函数入口下断点（简写 b）
b *0x401234                   # 在具体地址下断点
break *main+20                # 在偏移处下断点
tbreak main                   # 临时断点（触发一次后删除）
watch *(int*)0x404000         # 观察点：值改变时中断

info breakpoints              # 查看所有断点
delete 1                      # 删除断点 1
disable 1                     # 禁用断点 1
```

### 32.1.3 执行控制

```gdb
run                           # 运行程序（简写 r）
run < input.txt               # 带输入运行
continue                      # 继续执行（简写 c）
next                          # 单步跳过（不进入函数，简写 n）
step                          # 单步进入（进入函数，简写 s）
nexti                         # 单条指令跳过（简写 ni）
stepi                         # 单条指令进入（简写 si）
finish                        # 执行到当前函数返回
until                         # 执行到指定位置
```

---

## 32.2 查看内存与寄存器

### 32.2.1 查看内存（x 命令）

```gdb
x/20gx $rsp                   # 从 rsp 开始，以 8 字节为单位显示 20 个值（十六进制）
x/20i $rip                    # 反汇编 rip 开始的 20 条指令
x/s 0x401000                  # 以字符串形式显示
x/100cb $rsp                  # 以字符形式显示 100 字节

# 格式说明：x /数量 格式 单位 地址
# 格式：x(十六进制) d(十进制) s(字符串) c(字符) i(指令) o(八进制)
# 单位：b(1字节) h(2字节) w(4字节) g(8字节)
```

### 32.2.2 查看寄存器

```gdb
info registers                # 查看所有寄存器
p $rax                        # 查看单个寄存器
p/x $rsp                      # 十六进制显示
set $rax = 0x1234              # 修改寄存器
```

### 32.2.3 查看栈

pwndbg 提供了更直观的命令：

```gdb
stack                         # 查看栈内容（pwndbg）
stack 50                      # 查看 50 条
retaddr                       # 查看返回地址
```

---

## 32.3 pwndbg 常用命令

pwndbg 是 gdb 的增强插件，PWN 调试必备：

```gdb
# 程序信息
checksec                      # 查看保护机制
elf                           # ELF 信息

# 堆调试（超重要）
heap                          # 显示所有 chunk
vis_heap_chunks               # 可视化 chunk 布局
bins                          # 显示所有 bin 的链表
tcache                        # 查看 tcache
fastbins                      # 查看 fastbin
arena                         # 查看 arena 信息
find_fake_fast 地址 size       # 找 fake chunk

# 栈与内存
stack                         # 栈内容
retaddr                       # 返回地址
x/20gx 地址                    # 内存查看

# 搜索
search '/bin/sh'              # 在内存中搜索字符串
find 地址, 地址+0x100, 'AAAA'  # 在指定范围搜索

# ROP
rop                           # 显示当前栈上的 ROP 链

# 其他
disassemble                   # 反汇编当前函数
context                       # 显示完整上下文（寄存器、栈、汇编）
```

---

## 32.4 高级调试技巧

### 32.4.1 调试 PIE 程序

PIE 程序每次加载地址不同，需要找到基址：

```gdb
# pwndbg 自动计算基址
piebase                       # 显示 PIE 基址

# 手动方法
info proc mappings            # 查看内存映射，找到程序的加载地址
```

### 32.4.2 调试剥离符号的程序

```bash
# 用 stripped 的程序
gdb ./vuln_stripped
```

pwndbg 会自动识别函数边界。也可以手动分析：

```gdb
# 在 main 附近断点（通过入口点找）
starti                        # 停在程序入口
# 逐步找到 main
```

### 32.4.3 core dump 分析

程序崩溃后生成 core 文件，可以事后分析：

```bash
# 开启 core dump
ulimit -c unlimited
# 运行程序崩溃后生成 core

# 分析
gdb ./vuln core
```

查看崩溃位置：

```gdb
bt                            # backtrace，查看调用栈
info registers                # 查看崩溃时的寄存器
x/20gx $rsp                   # 查看崩溃时的栈
```

### 32.4.4 条件断点

```gdb
# 当变量等于特定值时中断
break vuln.c:15 if x == 42

# 当某个地址被写入特定值时中断
watch *(int*)0x404000 if *(int*)0x404000 == 0x1234
```

### 32.4.5 脚本化调试

```gdb
# 在 gdb 启动时自动执行命令
gdb -q ./vuln -ex 'b main' -ex 'run' -ex 'info reg'

# 使用命令文件
gdb -q ./vuln -x commands.gdb
```

---

## 32.5 用 gdb 调试 exp

pwntools 的 `gdb.debug()` 可以在 exp 中启动 gdb：

```python
from pwn import *

p = gdb.debug('./vuln', '''
    b *0x401234
    b vulnerable
    continue
''')

p.sendline(payload)
p.interactive()
```

或者在程序运行时附加：

```python
p = process('./vuln')
gdb.attach(p, 'b main')
p.sendline(payload)
```

---

## 32.6 调试实例：追踪栈溢出

```gdb
# 1. 下断点
b vulnerable
run

# 2. 单步到 gets 调用之后
ni
ni
# ... 直到执行完 gets

# 3. 查看 buf 和返回地址
p &buf
p $rbp+8

# 4. 观察溢出后的栈
x/30gx $rsp

# 5. 单步执行到 ret
si
# 观察 rip 的变化
```

---

## 32.7 小结

这一章我们系统学习了 gdb 和 pwndbg：

- **基础命令**：break、run、next、step、continue
- **查看内存**：x 命令、info registers、stack
- **pwndbg 增强**：heap、bins、tcache、vis_heap_chunks、checksec
- **高级技巧**：调试 PIE、core dump、条件断点、pwntools 集成

下一章我们学习二进制审计方法论——如何快速定位程序中的漏洞。

---

**下一章**：[二进制审计方法论](./ch33-二进制审计.md)
