# 第 5 章 ELF 文件与程序加载

> 编译出来的二进制文件不是一团乱码，而是一份结构严谨的「施工图纸」。读懂这份图纸，你才能知道代码在哪里、数据在哪里、程序的控制权会经过哪些地方。

---

## 5.1 什么是 ELF

**ELF（Executable and Linkable Format）** 是 Linux 下可执行文件的标准格式。你在 CTF 里遇到的绝大多数题目，都是 ELF 文件（也有 Windows 的 PE 文件，本教程暂不展开）。

ELF 文件有三种主要类型：

- **可执行文件（ET_EXEC）**：可以直接运行的程序（比如 `/bin/ls`）
- **可重定位文件（ET_REL）**：编译产生的 `.o` 文件，需要链接才能运行
- **共享目标文件（ET_DYN）**：动态链接库（`.so`）以及开启 PIE 的可执行文件

> 💡 **提示**：开启 PIE 的程序在 ELF 头里也是 ET_DYN 类型，因为它和共享库一样，可以被加载到任意地址。这在后面判断 PIE 是否开启时有用。

---

## 5.2 ELF 文件的整体结构

一个 ELF 文件由三部分组成：

```text
+------------------------+
|      ELF Header        |  ← 文件头，描述整体信息
+------------------------+
|   Program Headers      |  ← 程序头表，描述如何加载到内存（段）
+------------------------+
|                        |
|   Section Data         |  ← 各个节的实际内容（.text, .data ...）
|   (.text, .data, ...)  |
|                        |
+------------------------+
|   Section Headers      |  ← 节头表，描述每个节的信息（链接/调试用）
+------------------------+
```

从两个视角来看同一个文件：

- **链接视角**：关心 Section（节）——编译器和链接器按节组织代码和数据
- **运行视角**：关心 Segment（段）——操作系统按段把文件映射到内存

简单说：**节是给链接器看的，段是给操作系统看的**。一个段通常包含多个节。

---

## 5.3 重要的节（Section）

用 `readelf -S 程序名` 可以看到所有节。对 PWN 来说，最重要的是这几个：

| 节名 | 内容 | 权限 | PWN 中的意义 |
| --- | --- | --- | --- |
| `.text` | 程序代码（机器指令） | R-X | 找 gadget、找后门函数 |
| `.rodata` | 只读数据（字符串常量） | R-- | `/bin/sh` 通常在这里 |
| `.data` | 已初始化的全局变量 | RW- | 可写的全局变量 |
| `.bss` | 未初始化的全局变量 | RW- | 常作为栈迁移的目标 |
| `.got` | 全局偏移表 | RW- | 存放外部函数的真实地址 |
| `.got.plt` | PLT 用的 GOT | RW- | GOT 覆写的目标 |
| `.plt` | 过程链接表 | R-X | 调用外部函数的跳板 |
| `.plt.sec` | （新版）带 CET 的 PLT | R-X | 同上 |
| `.dynsym` | 动态符号表 | R-- | 函数名和地址的对应关系 |
| `.dynstr` | 动态字符串表 | R-- | 函数名字符串 |
| `.init` / `.fini` | 初始化/收尾代码 | R-X | 程序启动/退出时执行 |

### 5.3.1 .bss 段为什么特殊

`.bss` 段存放未初始化的全局变量。它在 ELF 文件里**不占实际磁盘空间**（只记录大小），加载时由操作系统清零。

```c
int global_var;      // 在 .bss
char buffer[1024];   // 在 .bss
int initialized = 5; // 在 .data
```

因为 `.bss` 在进程启动时是可写的、大小固定、地址已知（关闭 PIE 时），所以它常常是**栈迁移**（第 13 章）和**假 chunk 布置**（堆篇）的首选场地。

---

## 5.4 静态链接与动态链接

### 5.4.1 静态链接

```bash
gcc -static -o hello_static hello.c
```

静态链接会把所有用到的库函数代码**复制**到可执行文件里。结果是：文件很大，但运行时不依赖外部库。

静态链接的程序在 PWN 中很受欢迎，因为：

- 所有函数地址固定（如果没开 PIE）
- 有丰富的 gadget 可用（整个 libc 都被链接进来了）
- 不需要泄露 libc 基址

### 5.4.2 动态链接

```bash
gcc -o hello_dynamic hello.c
```

动态链接的程序只记录「我需要 printf 这个函数」，运行时由动态链接器（`/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2`）加载 libc，并把函数地址填好。

动态链接的好处是文件小、多个程序共享同一份 libc。但对 PWN 来说，它带来了一个挑战：**libc 的地址是运行时才确定的（而且有 ASLR）**，所以你需要先泄露 libc 基址，才能调用 `system` 等函数。这就是 ret2libc 的核心思路（第 10 章）。

---

## 5.5 PLT 与 GOT：动态链接的核心

这是本章最重要的一节。理解 PLT/GOT 的工作机制，是理解 GOT 覆写、ret2libc、Fake linkmap 等技术的前提。

### 5.5.1 为什么需要 PLT 和 GOT

程序调用 `printf` 时，编译出来的代码不能写死 `printf` 的地址（因为 libc 每次加载地址不同）。解决方案是加一层「间接跳转」：

- **GOT（Global Offset Table）**：一张表，每个外部函数占一项，里面存放函数的真实地址
- **PLT（Procedure Linkage Table）**：一段跳板代码，负责跳转到 GOT 里的地址

### 5.5.2 延迟绑定（Lazy Binding）机制

程序第一次调用某个函数时，GOT 里还没有真实地址。这时会触发一次「解析」过程：

```text
程序调用 puts@plt
       │
       ▼
┌─────────────────────────┐
│  puts@plt:              │
│  jmp [puts@got.plt]     │  ← GOT 里初始存放的是 "puts@plt+6"
│  push index             │  ← 压入函数索引
│  jmp plt0               │  ← 跳到解析器
└─────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│  _dl_runtime_resolve    │  ← 动态链接器：找到 puts 的真实地址
│  把真实地址写回 GOT      │
│  跳转到 puts 执行        │
└─────────────────────────┘
```

第二次调用 `puts` 时：

```text
程序调用 puts@plt
       │
       ▼
┌─────────────────────────┐
│  puts@plt:              │
│  jmp [puts@got.plt]     │  ← GOT 里现在是 puts 的真实地址！
│  → 直接跳到 puts 执行    │
└─────────────────────────┘
```

这就是「延迟绑定」——只在第一次调用时解析，之后直接跳。

### 5.5.3 这对 PWN 意味着什么

**GOT 表是可写的（在 Partial RELRO 下）**。如果你能把 `puts@got` 的内容改成 `system` 的地址，那么下次程序调用 `puts("something")` 时，实际执行的就是 `system("something")`——这就是 **GOT 覆写攻击**。

此外，因为 PLT 里的地址是固定的（在关闭 PIE 时），我们可以直接调用 `puts@plt` 来泄露 GOT 里的内容——这就是 **ret2libc 中泄露 libc 地址** 的常用手法：

```python
# 调用 puts(puts@got) 来打印 puts 的真实地址
payload = b'A' * offset + p32(puts_plt) + p32(main_addr) + p32(puts_got)
```

> ⚠️ **注意**：如果程序开启了 Full RELRO，GOT 表会被设为只读，GOT 覆写就失效了。这就是保护机制章节要讲的内容。

### 5.5.4 用 objdump 看 PLT/GOT

```bash
objdump -d -j .plt ./vuln64
objdump -R ./vuln64        # 查看重定位表，间接看出 GOT 项
```

你会看到类似：

```asm
0000000000001040 <puts@plt>:
    1040:  ff 25 d2 2f 00 00    jmp QWORD PTR [rip+0x2fd2]  # 401018 <puts@GOT>
    1046:  68 00 00 00 00       push 0x0
    104b:  e9 e0 ff ff ff       jmp 1030 <_init+0x30>
```

第一行 `jmp QWORD PTR [rip+0x2fd2]` 就是跳到 GOT 表里的puts 项。

---

## 5.6 程序加载：从 execve 到 main

当你在 shell 里输入 `./vuln` 时，发生了什么？

```text
1. shell 调用 execve("./vuln", argv, envp)
         │
         ▼
2. 内核读取 ELF 头，检查文件格式
         │
         ▼
3. 内核根据 Program Headers 把各段映射到内存
   - .text → 可执行、只读
   - .data/.bss → 可读写
   - 分配栈空间，把 argv/envp 放到栈上
         │
         ▼
4. 如果是动态链接程序，内核启动动态链接器 ld.so
         │
         ▼
5. ld.so 加载 libc 等依赖库，完成重定位（填写 GOT）
         │
         ▼
6. 执行 .init 段的初始化代码（构造函数等）
         │
         ▼
7. 跳转到 main 函数
         │
         ▼
8. main 返回后，执行 .fini 代码，调用 exit 退出
```

几个对 PWN 有用的细节：

- **栈的初始内容**：栈顶是 argc，接着是 argv 指针数组、envp 指针数组，然后是 auxiliary vector（auxv）。`environ` 全局变量指向环境变量数组，常用来**泄露栈地址**。
- **libc 的加载位置**：通常在栈的高地址方向，地址形如 `0x7f...`
- **堆的位置**：在 BSS 段之后（通过 brk 扩展），地址紧跟着程序的数据段

---

## 5.7 常用 ELF 分析命令

把这几个命令记熟，它们是你的日常工具：

```bash
# 查看 ELF 头（入口点、程序头位置等）
readelf -h ./vuln

# 查看程序头（段信息、权限）
readelf -l ./vuln

# 查看节头
readelf -S ./vuln

# 查看动态链接信息（依赖哪些库）
readelf -d ./vuln

# 查看重定位表（GOT 项）
readelf -r ./vuln

# 查看符号表
nm ./vuln
nm -D ./vuln          # 动态符号表

# 反汇编
objdump -d -M intel ./vuln

# 查看字符串
strings -a -t x ./vuln

# 查看所有函数用到了哪些库函数（快速找危险函数）
objdump -T ./vuln | grep -E 'gets|read|printf|strcpy'
```

> 🔥 **实战**：拿第二章编译的 `vuln64` 试试这些命令。回答下面的问题：
> 1. 程序用到了哪些外部函数？（`readelf -d` 或 `objdump -T`）
> 2. `printf` 的 PLT 地址是多少？
> 3. `.bss` 段的地址范围是什么？
> 4. GOT 表里有哪些项？

---

## 5.8 小结

这一章我们搞清了 ELF 的世界：

- **ELF 文件**由 ELF 头、程序头、节数据、节头组成
- **段（Segment）**给操作系统看，用于加载；**节（Section）**给链接器看，用于组织
- **.text** 存代码，**.data/.bss** 存全局变量，**.rodata** 存字符串常量
- **.bss** 不占磁盘空间、可写、地址已知（关闭 PIE 时），是栈迁移的常用目标
- **静态链接**把库函数打包进程序，**动态链接**运行时加载 libc
- **PLT/GOT** 实现延迟绑定：第一次调用函数时解析地址并写入 GOT，之后直接跳转
- **GOT 可写**（Partial RELRO 时）→ 可以覆写 GOT 来劫持控制流
- 程序从 execve 到 main 经历内核加载、动态链接器重定位、初始化代码等步骤

下一章我们把视角聚焦到栈上，详细剖析函数调用时栈帧的建立与销毁过程——这是理解栈溢出的最后一块拼图。

---

**下一章**：[栈与函数调用的真相](./ch06-栈与函数调用.md)
