# 第 2 章 FFI 与 ABI 底层原理

## 本章目标

读完这一章，你将能够：

- 说清楚「调用一个函数」在机器层面到底发生了什么
- 理解 ABI（应用程序二进制接口）为什么是跨语言调用的通用契约
- 掌握调用约定、符号导出、名称修饰这些高频概念
- 理解基本数据类型、结构体、字符串、指针在跨语言时如何映射
- 建立「内存边界」的直觉，知道为什么这里是漏洞高发区

> 这一章偏底层，但**不需要你懂汇编**。我们用类比和图解把原理讲清楚。理解了这些，后面所有方案（ctypes、pybind11、PyO3）你都能看透本质。

---

## 2.1 从「调用函数」说起：机器层面发生了什么

当你写下这行 Python：

```python
result = lib.add(3, 5)
```

看起来只是一行代码，但计算机内部经历了一连串动作。理解这个过程，是理解 FFI 的关键。

### 2.1.1 函数调用的本质：跳转 + 传参

在机器层面，一个「函数」就是内存里的一段指令序列。调用函数，本质上是：

1. **把参数放到约定好的位置**（寄存器或栈上）
2. **记录返回地址**（函数执行完后该回到哪里）
3. **跳转到函数入口地址**开始执行
4. 函数执行完，**取回返回地址，跳回来**
5. **从约定好的位置读取返回值**

关键问题来了：**调用者和被调者必须事先约定好**——

- 参数放在哪个寄存器/栈的哪个位置？
- 返回值放在哪里？
- 谁负责清理栈？
- 哪些寄存器调用函数后必须保持不变？

这套约定，就是 **ABI（Application Binary Interface，应用程序二进制接口）**。

> **小白问：ABI 和 API 有什么区别？**
> - **API**（Application Programming Interface）是**源代码层面**的约定：函数名、参数类型、返回值。比如 `int add(int a, int b);`。
> - **ABI**是**二进制层面**的约定：参数在寄存器还是栈、返回值放哪、结构体如何布局、符号名如何编码。
>
> API 相同，ABI 不一定相同。这就是「为什么同一个 C 源码在不同编译器/平台上编译出的库不一定能通用」的原因。

### 2.1.2 栈帧：函数调用的「工作台」

每次函数调用，都会在**栈（stack）**上分配一块空间，叫**栈帧（stack frame）**。它存放：

- 参数（如果寄存器放不下）
- 局部变量
- 返回地址
- 保存的寄存器

```
高地址
┌─────────────────┐
│   调用者的栈帧    │
├─────────────────┤
│ 参数 2 (b=5)     │  ← 参数按约定压栈
│ 参数 1 (a=3)     │
│ 返回地址         │  ← 函数执行完回到这里
├─────────────────┤
│ 局部变量         │  ← 被调函数的空间
│ 保存的寄存器     │
└─────────────────┘
低地址
```

理解栈帧非常重要，因为**栈溢出漏洞**就是往这块空间写入超出边界的数据，覆盖了「返回地址」，从而劫持程序执行流程。后面第 10 章（安全卷）和第 19 章会用到这个知识。

---

## 2.2 调用约定（Calling Convention）

调用约定是 ABI 最核心的部分。不同平台/编译器有不同的约定，常见的有：

| 约定 | 平台 | 参数传递 | 栈清理方 |
|------|------|---------|---------|
| **cdecl** | x86（32位）C 默认 | 全部压栈 | 调用者 |
| **stdcall** | Windows API | 全部压栈 | 被调者 |
| **fastcall** | x86 | 前两个参数放寄存器 | 被调者 |
| **System V AMD64** | Linux/macOS x86-64 | 前 6 个整数参数放寄存器 | 调用者 |
| **Microsoft x64** | Windows x86-64 | 前 4 个参数放寄存器 | 调用者 |

### 2.2.1 x86-64 的寄存器传参（最重要）

现代系统（Linux/macOS/Windows 的 64 位）主要用寄存器传参，速度更快。

**System V ABI（Linux/macOS）**，整数/指针参数依次放入：

```
rdi, rsi, rdx, rcx, r8, r9
第1  第2  第3  第4  第5  第6
```

返回值放 `rax`。浮点数参数用 `xmm0` ~ `xmm7`。

**Microsoft x64（Windows）**：

```
rcx, rdx, r8, r9
第1  第2  第3  第4
```

返回值同样放 `rax`。浮点数用 `xmm0`~`xmm3`。

> **这对你意味着什么？**
> 你几乎不需要手动操作这些寄存器——ctypes、pybind11、PyO3 等工具会自动按正确的 ABI 生成代码。但如果调用约定不匹配（比如用 32 位的约定去调 64 位的库），程序会**崩溃或产生诡异结果**。这是混合编程的经典坑之一。

### 2.2.2 一个直观例子

C 函数：

```c
int add(int a, int b) { return a + b; }
```

编译成 x86-64 汇编（System V ABI）大致是：

```asm
add:
    mov  eax, edi      ; 第1个参数 a 在 edi
    add  eax, esi      ; 第2个参数 b 在 esi
    ret                ; 返回值在 eax
```

调用方只需要把 3 和 5 放进 `edi` 和 `esi`，然后 `call add`，从 `eax` 取结果。**这就是 ABI 约定的力量**：调用方和被调方不需要知道对方怎么实现，只要遵守同一套约定即可协作。

---

## 2.3 符号（Symbol）与名称修饰（Name Mangling）

### 2.3.1 符号是什么

编译后的目标文件/共享库里，每个函数和全局变量都有一个**符号名**，链接器靠符号名找到函数地址。

用 `nm` 命令可以看一个库里的符号：

```bash
$ nm -D libfast.so
0000000000001149 T add
0000000000001150 T multiply
```

`T` 表示代码段（Text）中的函数。

### 2.3.2 C 的名称：简单直接

C 语言的函数符号名就是函数名本身（可能加个下划线前缀，看平台）。所以 `add` 的符号就是 `add`。这让 C 成为跨语言的「通用货币」——任何语言都能按名字找到它。

### 2.3.3 C++ 的名称修饰：复杂但必要

C++ 支持函数重载、命名空间、类方法，光靠函数名无法唯一标识一个函数。所以编译器会把函数名「修饰」（mangle）成一个复杂的符号名：

```cpp
int add(int a, int b);        // 符号：_Z3addii
double add(double a, double b); // 符号：_Z3adddd
```

`_Z3addii` 的含义：`_Z`（C++ 修饰前缀）+ `3add`（函数名长度3，名add）+ `ii`（两个 int 参数）。

> **小白问：这对混合编程有什么影响？**
> 如果 Python 想直接调用一个 C++ 函数，它得知道修饰后的符号名，这非常麻烦。解决办法：用 `extern "C"` 告诉编译器按 C 的方式导出符号：
>
> ```cpp
> extern "C" int add(int a, int b) { return a + b; }
> ```
>
> 这样符号就是干净的 `add`。这是 pybind11、cffi 等工具在底层做的事之一。
>
> 查看修饰后符号名的工具：`c++filt`（反修饰），或 `nm -C`。

---

## 2.4 静态库与动态库：链接的两种方式

跨语言调用通常要用到「库」。库分两种：

### 2.4.1 静态库（Static Library）

- 扩展名：Linux/macOS `.a`，Windows `.lib`
- 链接时把库代码**完整复制**进可执行文件
- 优点：运行时无依赖，部署简单
- 缺点：体积大，多个程序重复包含，库更新要重新编译整个程序

### 2.4.2 动态库 / 共享库（Shared Library）

- 扩展名：Linux `.so`，macOS `.dylib`，Windows `.dll`
- 编译时只记录「依赖这个库」，运行时才加载
- 优点：多个程序共享一份，更新库不用重编译程序，支持运行时加载（`dlopen`）
- 缺点：部署时要带上库（依赖管理问题）

**混合编程几乎都用动态库**，因为 Python 需要在运行时加载它：

```python
import ctypes
lib = ctypes.CDLL("./libfast.so")   # 运行时加载动态库
```

### 2.4.3 动态库加载的本质

`dlopen`（ctypes 底层调用的就是它）做的事：

1. 把 `.so` 文件映射到进程的地址空间
2. 解析它的依赖（可能还依赖其他 `.so`）
3. 执行初始化代码
4. 返回一个句柄，之后可以按符号名查找函数（`dlsym`）

这也解释了为什么跨语言调用有一个固定开销：查符号、切换上下文。**这就是为什么不能把跨语言调用放在高频循环里**（心法一）。

---

## 2.5 数据类型映射：跨语言的「翻译表」

数据在边界上必须翻译。这是最容易出 bug 的地方。

### 2.5.1 基本类型

| C 类型 | 典型大小 | Python (ctypes) | Rust | Go |
|--------|---------|----------------|------|-----|
| `int` | 4 字节 | `c_int` | `i32` | `int32` |
| `long` | 8(Linux)/4(Win) | `c_long` | `i64` | `int64` |
| `unsigned int` | 4 | `c_uint` | `u32` | `uint32` |
| `float` | 4 | `c_float` | `f32` | `float32` |
| `double` | 8 | `c_double` | `f64` | `float64` |
| `char` | 1 | `c_char` | `i8`/`u8` | `byte` |
| `void*` | 8(64位) | `c_void_p` | `*mut c_void` | `unsafe.Pointer` |
| `size_t` | 8(64位) | `c_size_t` | `usize` | `uintptr` |

**最大的坑**：`int` 和 `long` 的大小依赖平台和编译器！在 64 位 Linux 上 `long` 是 8 字节，在 64 位 Windows 上 `long` 还是 4 字节（Windows 用 LLP64 模型）。**永远不要假设大小**，用 `sizeof` 或固定宽度类型（`int32_t`、`int64_t`）来明确。

### 2.5.2 结构体布局与内存对齐

C 结构体在内存中的布局不是简单的字段相加，因为有**内存对齐（alignment）**：

```c
struct Packet {
    char  type;    // 1 字节
    int   length;  // 4 字节
    char  flag;    // 1 字节
};
```

你以为它占 6 字节？实际是 **12 字节**：

```
偏移 0: type    (1 字节)
偏移 1-3: 填充  (3 字节，为了对齐 int)
偏移 4-7: length (4 字节)
偏移 8:   flag   (1 字节)
偏移 9-11: 填充  (3 字节，为了结构体整体对齐到 4 的倍数)
```

**为什么对齐？** CPU 访问对齐的数据更快，某些架构甚至要求必须对齐。编译器自动插入填充字节。

这对跨语言调用的意义：**两种语言对同一结构体的布局必须完全一致**，否则字段会错位，读出错值甚至崩溃。ctypes 的 `Structure`、cffi 的 `cdef`、pybind11 都会按 C 规则处理对齐，但如果你自己定义结构体，必须小心。

> 查看结构体大小的 C 代码：
> ```c
> printf("%zu\n", sizeof(struct Packet));  // 输出 12
> printf("%zu\n", offsetof(struct Packet, length));  // 输出 4
> ```

### 2.5.3 字符串：最经典的坑

C 字符串是「以 `\0` 结尾的字节数组」；Python 字符串是 Unicode 对象；Rust 的 `String` 是 UTF-8 + 长度。三者完全不同。

跨语言传递字符串时要注意：

1. **编码/解码**：Python `str` 传给 C 前要编码成字节（通常 UTF-8），C 返回的字节要解码
2. **所有权**：谁分配的内存谁释放。C 用 `malloc` 分配并返回给 Python，Python 用完必须调用 C 的 `free`（不能用 Python 的 `free`！），否则内存泄漏或崩溃
3. **长度**：C 字符串靠 `\0` 判断结尾，如果数据里含 `\0`（比如二进制数据），会被截断。安全工具处理网络包时经常踩这个坑

```python
# ctypes 中字符串的正确处理
lib.process.argtypes = [ctypes.c_char_p]  # 声明参数类型
lib.process( "hello".encode('utf-8') )     # 编码成字节

# C 返回 malloc 分配的字符串
lib.get_message.restype = ctypes.c_void_p
ptr = lib.get_message()
msg = ctypes.string_at(ptr).decode('utf-8')  # 读取
lib.free_string(ptr)  # 必须调用 C 的释放函数！
```

### 2.5.4 指针与数组

C 里数组就是「指向首元素的指针 + 长度信息（另传）」：

```c
int sum(int *arr, int len);
```

Python 侧要传递数组，需要构造对应类型的数组：

```python
ArrType = ctypes.c_int * 5
arr = ArrType(1, 2, 3, 4, 5)
lib.sum(arr, 5)
```

**指针是安全漏洞的根源**。跨语言传递指针时，必须确保：
- 指针指向的内存有效（没被释放）
- 长度正确（不越界）
- 生命周期覆盖整个调用过程

---

## 2.6 内存边界：漏洞高发区

现在把上面的知识串起来，理解为什么「内存边界」是混合编程最关键也最危险的部分。

### 2.6.1 两个世界，两种内存管理

```
┌──────────────────┐   边界   ┌──────────────────┐
│  Python 世界      │  ═════  │  C/Rust 世界      │
│  GC 自动管理      │         │  手动/所有权管理   │
│  对象是 Python 对象│         │  裸内存/指针       │
└──────────────────┘         └──────────────────┘
```

- Python 侧：对象由引用计数 + GC 管理，你不用管释放
- C 侧：`malloc` 的必须 `free`，忘记就泄漏，重复就崩溃
- Rust 侧：所有权系统保证自动释放，但跨边界时要手动交接所有权

**边界规则（记住它）**：

> **谁分配，谁释放；跨边界传递时，明确所有权归属。**

### 2.6.2 典型漏洞场景

**场景一：Use-After-Free（UAF）**

```python
# 假设 C 函数返回一个指向内部缓冲区的指针
ptr = lib.get_buffer()
lib.clear_buffer()      # C 侧把这个缓冲区释放了
data = ctypes.string_at(ptr)  # 危险！ptr 已成悬垂指针
```

**场景二：缓冲区溢出**

```python
# C 函数期望一个 16 字节的缓冲区
buf = (ctypes.c_char * 8)()   # 只分配了 8 字节
lib.copy_data(buf, 16)        # C 写入 16 字节 → 溢出！
```

在安全工具开发中，这类 bug 会被攻击者利用。**用 Rust 做边界模块的价值就在这里**：它的类型系统和借用检查能在编译期阻止大部分此类错误。

### 2.6.3 GIL：Python 特有的边界问题

GIL（Global Interpreter Lock，全局解释器锁）保证同一时刻只有一个线程执行 Python 字节码。当 Python 调用 C/C++ 函数时：

- ctypes 默认：**释放 GIL**（调用期间其他 Python 线程可运行）
- pybind11/Cython/PyO3：需要**手动声明释放 GIL**（`py::gil_scoped_release`、`with nogil`、`py.allow_threads`）

为什么要释放？因为如果 C 函数跑很久还占着 GIL，其他 Python 线程全部卡住。为什么要手动？因为释放 GIL 后**不能碰 Python 对象**（可能被其他线程改），必须小心。第 12 章会专门讲这块。

---

## 2.7 动手实验：亲眼看 ABI

理论讲完了，动手验证一下。

### 实验一：查看符号和名称修饰

创建 `mangle.cpp`：

```cpp
int add(int a, int b) { return a + b; }
double add(double a, double b) { return a + b; }
extern "C" int c_add(int a, int b) { return a + b; }
```

用 g++ 编译并查看符号：

```bash
g++ -c mangle.cpp -o mangle.o
nm mangle.o | grep add
```

你会看到类似：

```
0000000000000000 T _Z3addii       # int add(int,int)
0000000000000007 T _Z3adddd       # double add(double,double)
0000000000000010 T c_add          # extern "C"，干净的名字
```

用 `c++filt` 反修饰：

```bash
$ c++filt _Z3addii
add(int, int)
```

### 实验二：验证结构体对齐

创建 `align.c`：

```c
#include <stdio.h>
#include <stddef.h>

struct Packet {
    char  type;
    int   length;
    char  flag;
};

int main() {
    printf("sizeof = %zu\n", sizeof(struct Packet));
    printf("offset of length = %zu\n", offsetof(struct Packet, length));
    printf("offset of flag = %zu\n", offsetof(struct Packet, flag));
    return 0;
}
```

```bash
gcc align.c -o align && ./align
# 输出：sizeof = 12, offset of length = 4, offset of flag = 8
```

### 实验三：用 ctypes 验证类型大小

```python
import ctypes
for name in ['c_int', 'c_long', 'c_double', 'c_void_p', 'c_size_t']:
    t = getattr(ctypes, name)
    print(f"{name}: {ctypes.sizeof(t)} bytes")
```

---

## 2.8 本章总结

| 概念 | 核心要点 |
|------|---------|
| ABI | 二进制层面的调用约定，跨语言的通用契约 |
| API vs ABI | API 是源码约定，ABI 是二进制约定；API 同不代表 ABI 同 |
| 函数调用 | 传参 → 跳函数 → 返回；靠 ABI 约定参数/返回值位置 |
| 调用约定 | x86-64 Linux/macOS 用 rdi/rsi/rdx...；Windows 用 rcx/rdx/r8/r9 |
| 栈帧 | 参数、返回地址、局部变量；栈溢出就是覆盖返回地址 |
| 符号 | 链接器找函数的名字；C 简单，C++ 名称修饰，`extern "C"` 导出干净名 |
| 静态库 vs 动态库 | `.a`/`.lib` 静态链接；`.so`/`.dll`/`.dylib` 运行时加载，混合编程用动态库 |
| 类型映射 | 注意 int/long 平台差异、结构体对齐、字符串编码、指针生命周期 |
| 内存边界 | 谁分配谁释放；UAF/溢出/GIL 是三大坑 |

---

## 本章练习

1. 用 `nm -D` 查看系统的某个 `.so` 库（如 `libc`），找出几个函数符号。
2. 写一个 C++ 函数重载，编译后用 `nm` 看两个版本的修饰名，再用 `c++filt` 还原。
3. 写几个不同字段顺序的结构体，用 `sizeof` 和 `offsetof` 验证对齐规则。
4. 用 ctypes 打印 `c_int`、`c_long` 的大小，确认你机器的模型（LP64 还是 LLP64）。
5. 思考：为什么字符串是跨语言最经典的坑？结合编码和所有权两方面回答。
6. 思考：如果一个 C 函数运行 10 秒，Python 主线程调用它时会发生什么？GIL 该不该释放？

---

**下一章预告**：学习开发环境与工具链——编译器、共享库的编译与链接、头文件的作用、跨语言构建全景图。我们会亲手编译一个 `.so` 并用 Python 调用它，把本章的 ABI 知识变成可运行的代码。
