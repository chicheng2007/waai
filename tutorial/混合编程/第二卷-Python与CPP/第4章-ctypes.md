# 第 4 章 ctypes：不用写 C 代码调用动态库

## 本章目标

读完这一章，你将能够：

- 用 ctypes 加载任意 C 共享库并调用函数
- 正确处理参数类型、返回值、结构体、指针、数组
- 理解回调函数（C 调用 Python）的用法
- 掌握 ctypes 调用 OpenSSL 等真实系统库的实战技巧
- 知道 ctypes 的性能边界和适用场景

---

## 4.1 ctypes 是什么

`ctypes` 是 Python **标准库**的一部分，能直接调用 C 共享库里的函数，无需编译任何包装代码。它是门槛最低的混合编程方案。

**优点**：
- Python 自带，零安装
- 能调用任何导出的 C 函数（系统库、第三方库）
- 适合快速原型、调用现成库

**缺点**：
- 类型转换繁琐，需要手动声明 `argtypes`/`restype`
- 复杂的 C++ 类无能为力（只能调 `extern "C"` 函数）
- 每次调用有一定开销
- 指针/内存错误只能靠自己小心

---

## 4.2 快速上手：调用系统库

### 4.2.1 调用 C 标准库

Python 自己就在用 ctypes 调用 libc。我们可以直接试试：

```python
import ctypes
import os

# 加载 C 标准库
# Linux: libc.so.6, macOS: libSystem.dylib, Windows: msvcrt
if os.name == 'nt':
    libc = ctypes.CDLL('msvcrt')
elif 'darwin' in os.sys.platform:
    libc = ctypes.CDLL('libSystem.dylib')
else:
    libc = ctypes.CDLL('libc.so.6')

# 调用 abs（求绝对值）
libc.abs.argtypes = [ctypes.c_int]
libc.abs.restype = ctypes.c_int
print(libc.abs(-42))  # 输出 42

# 调用 time（返回当前时间戳）
libc.time.restype = ctypes.c_long
print("时间戳:", libc.time(None))
```

### 4.2.2 直接调用数学库

```python
import ctypes
import math
libm = ctypes.CDLL('libm.so.6')  # Linux 的数学库

libm.sqrt.argtypes = [ctypes.c_double]
libm.sqrt.restype = ctypes.c_double
print(libm.sqrt(2.0))   # 1.4142135623730951

libm.pow.argtypes = [ctypes.c_double, ctypes.c_double]
libm.pow.restype = ctypes.c_double
print(libm.pow(2.0, 10.0))  # 1024.0
```

> **小白问：math.sqrt 不就能算吗，何必用 ctypes？**
> 这里是为了演示原理。实际中，调用**没有 Python 对应库**的 C 函数（如某些加密算法、专用硬件驱动库）才是 ctypes 的真正价值。

---

## 4.3 核心机制：argtypes 与 restype

这是 ctypes 最关键的概念，也是 90% bug 的根源。

### 4.3.1 为什么要声明类型

Python 是动态类型，C 是静态类型。当你调用 `lib.add(3, 5)` 时，ctypes 需要知道：

- 把 Python 的 `3` 转成什么 C 类型？（`int`? `long`? `double`?）
- 返回值按什么类型解读？

如果不声明，ctypes 默认按 `int` 处理参数、按 `int` 处理返回值。对于简单整数没问题，但遇到 `double`、指针、结构体就会**悄悄出错**——结果错误但不报错，极难排查。

```python
import ctypes
lib = ctypes.CDLL('./libfast.so')

# ❌ 错误示范：不声明类型
print(lib.add(3, 5))  # 可能碰巧对，因为默认就是 int

# 但如果是 double 函数：
# lib.divide.restype 默认是 int → 返回 3.14 会被读成奇怪的整数！
lib.divide.argtypes = [ctypes.c_double, ctypes.c_double]
lib.divide.restype = ctypes.c_double  # ✅ 必须声明
print(lib.divide(10.0, 3.0))  # 3.3333...
```

### 4.3.2 常用类型对照表

| C 类型 | ctypes 类型 | Python 对应 |
|--------|------------|------------|
| `int` | `c_int` | int |
| `unsigned int` | `c_uint` | int |
| `long` | `c_long` | int |
| `long long` | `c_longlong` | int |
| `float` | `c_float` | float |
| `double` | `c_double` | float |
| `char` | `c_char` | bytes (1) |
| `char*` | `c_char_p` | bytes |
| `wchar_t*` | `c_wchar_p` | str |
| `void*` | `c_void_p` | int/None |
| `size_t` | `c_size_t` | int |
| `bool` (C++) | `c_bool` | bool |

### 4.3.3 参数自动转换

声明 `argtypes` 后，ctypes 会自动把 Python 值转成 C 值：

```python
lib.add.argtypes = [ctypes.c_int, ctypes.c_int]
lib.add(3, 5)         # Python int → c_int ✅
lib.add(3.0, 5.0)     # float → int？会转换但可能警告
```

但反过来（C 返回 → Python）有时需要手动转换，比如指针要用 `string_at`、`cast`。

---

## 4.4 处理指针和数组

### 4.4.1 指针基础

C 函数经常接收指针参数。ctypes 用 `POINTER()` 表示指针类型：

```python
# C: void increment(int *p) { (*p)++; }
lib.increment.argtypes = [ctypes.POINTER(ctypes.c_int)]
lib.increment.restype = None

x = ctypes.c_int(10)      # 创建一个 C int 变量
lib.increment(ctypes.byref(x))  # 传它的地址
print(x.value)  # 11
```

`byref()` 获取变量地址，等价于 C 的 `&`。也可以先创建指针再传：

```python
p = ctypes.pointer(ctypes.c_int(10))
lib.increment(p)
print(p.contents.value)  # 用 .contents 访问指针指向的值
```

### 4.4.2 数组

ctypes 用 `类型 * 长度` 创建数组：

```python
# C: int sum(int *arr, int len)
lib.sum.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
lib.sum.restype = ctypes.c_int

IntArray5 = ctypes.c_int * 5
arr = IntArray5(1, 2, 3, 4, 5)
print(lib.sum(arr, 5))  # 15

# 从 Python list 构造数组
data = [10, 20, 30, 40]
arr = (ctypes.c_int * len(data))(*data)
print(lib.sum(arr, len(data)))  # 100
```

数组作为指针参数传入时，ctypes 会自动转换（数组名退化为指针）。

### 4.4.3 输出参数（函数通过指针返回结果）

C 常用「输出参数」返回结果：

```c
// C: void get_version(int *major, int *minor)
void get_version(int *major, int *minor) {
    *major = 3;
    *minor = 11;
}
```

Python 侧：

```python
lib.get_version.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
lib.get_version.restype = None

major = ctypes.c_int()
minor = ctypes.c_int()
lib.get_version(ctypes.byref(major), ctypes.byref(minor))
print(f"Python {major.value}.{minor.value}")  # Python 3.11
```

---

## 4.5 处理结构体

结构体是网络协议、系统 API 的常见数据格式（比如 IP 头、文件信息）。ctypes 用 `Structure` 类对应 C 的 `struct`。

### 4.5.1 定义结构体

假设有 C 结构体（回顾第 2 章的对齐知识）：

```c
struct Packet {
    char  type;
    int   length;
    char  flag;
};
```

Python 对应：

```python
import ctypes

class Packet(ctypes.Structure):
    _fields_ = [
        ('type',   ctypes.c_char),
        ('length', ctypes.c_int),
        ('flag',   ctypes.c_char),
    ]

# 验证大小和对齐（应和 C 一致：12 字节）
print(ctypes.sizeof(Packet))  # 12
p = Packet(b'T', 1024, b'1')
print(p.type, p.length, p.flag)  # b'T' 1024 b'1'
```

**字段顺序和类型必须和 C 完全一致**，否则对齐错位，读写全乱。

### 4.5.2 结构体指针

```python
# C: void process_packet(struct Packet *p)
lib.process_packet.argtypes = [ctypes.POINTER(Packet)]
lib.process_packet.restype = None

p = Packet(b'T', 100, b'0')
lib.process_packet(ctypes.byref(p))
```

### 4.5.3 嵌套结构体与数组字段

```c
struct Header {
    int version;
    char src_ip[16];
    char dst_ip[16];
};
```

```python
class Header(ctypes.Structure):
    _fields_ = [
        ('version', ctypes.c_int),
        ('src_ip',  ctypes.c_char * 16),
        ('dst_ip',  ctypes.c_char * 16),
    ]

h = Header()
h.version = 4
h.src_ip = b"192.168.1.1"
print(h.src_ip)  # b'192.168.1.1'
```

### 4.5.4 位域（Bit Field）

网络协议常用位域：

```c
struct Flags {
    unsigned int syn : 1;
    unsigned int ack : 1;
    unsigned int fin : 1;
};
```

```python
class Flags(ctypes.Structure):
    _fields_ = [
        ('syn', ctypes.c_uint, 1),
        ('ack', ctypes.c_uint, 1),
        ('fin', ctypes.c_uint, 1),
    ]

f = Flags()
f.syn = 1
f.ack = 0
```

---

## 4.6 回调函数：让 C 调用 Python

有时需要把 Python 函数作为回调传给 C（比如事件通知、自定义比较器）。ctypes 用 `CFUNCTYPE` 定义回调类型。

### 4.6.1 基本用法

假设 C 函数：

```c
// C: void for_each(int *arr, int len, void (*callback)(int))
void for_each(int *arr, int len, void (*callback)(int)) {
    for (int i = 0; i < len; i++) callback(arr[i]);
}
```

Python 侧：

```python
# 定义回调类型：返回 void，接收一个 int
CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_int)

lib.for_each.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, CALLBACK]
lib.for_each.restype = None

# 用装饰器把 Python 函数包装成 C 回调
@CALLBACK
def my_callback(value):
    print(f"收到值: {value}")

arr = (ctypes.c_int * 3)(1, 2, 3)
lib.for_each(arr, 3, my_callback)
```

输出：

```
收到值: 1
收到值: 2
收到值: 3
```

### 4.6.2 回调的坑

1. **必须保持引用**：回调对象必须一直存在（用全局变量或保存引用），否则被 GC 回收后 C 调用会崩溃
2. **异常不能传播**：Python 回调里抛异常不会传到 C，只会打印到 stderr，要自己捕获处理
3. **GIL**：C 调用 Python 回调时会获取 GIL，注意不要死锁

---

## 4.7 实战：用 ctypes 调用 OpenSSL 计算哈希

现在做一个真实有用的例子——用 Python 调用系统 OpenSSL 库计算 MD5/SHA256（不依赖 hashlib，演示 ctypes 调真实库）。

> **说明**：OpenSSL 1.1 和 3.0 的 API 有差异，下面以常见的 3.0 为例（用 EVP 高层 API）。1.1 环境的接口类似但函数名不同。

```python
import ctypes
import ctypes.util

# 找到并加载 OpenSSL 的 crypto 库
lib_path = ctypes.util.find_library('crypto')
print(f"OpenSSL crypto 库: {lib_path}")
crypto = ctypes.CDLL(lib_path)

# --- 定义 EVP 相关类型和函数 ---
# EVP_MD_CTX_new: 创建上下文
crypto.EVP_MD_CTX_new.restype = ctypes.c_void_p

# EVP_sha256: 获取 SHA256 算法对象
crypto.EVP_sha256.restype = ctypes.c_void_p

# EVP_DigestInit_ex(ctx, type, impl)
crypto.EVP_DigestInit_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
crypto.EVP_DigestInit_ex.restype = ctypes.c_int

# EVP_DigestUpdate(ctx, data, count)
crypto.EVP_DigestUpdate.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
crypto.EVP_DigestUpdate.restype = ctypes.c_int

# EVP_DigestFinal_ex(ctx, md, sizeptr)
crypto.EVP_DigestFinal_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
crypto.EVP_DigestFinal_ex.restype = ctypes.c_int

# EVP_MD_CTX_free: 释放上下文
crypto.EVP_MD_CTX_free.argtypes = [ctypes.c_void_p]


def sha256_ctypes(data: bytes) -> str:
    """用 ctypes 调 OpenSSL 计算 SHA256"""
    ctx = crypto.EVP_MD_CTX_new()
    crypto.EVP_DigestInit_ex(ctx, crypto.EVP_sha256(), None)
    crypto.EVP_DigestUpdate(ctx, data, len(data))

    digest = (ctypes.c_ubyte * 32)()
    length = ctypes.c_uint()
    crypto.EVP_DigestFinal_ex(ctx, digest, ctypes.byref(length))
    crypto.EVP_MD_CTX_free(ctx)

    return bytes(digest).hex()


if __name__ == '__main__':
    msg = b"hello mixed programming"
    print(f"ctypes SHA256: {sha256_ctypes(msg)}")

    # 用标准库验证
    import hashlib
    print(f"hashlib SHA256: {hashlib.sha256(msg).hexdigest()}")
```

两个结果一致，说明我们成功调用了系统 OpenSSL！

> **安全场景**：恶意软件分析中常用哈希比对病毒库。这个例子展示了如何用 ctypes 直接调底层加密库——在需要特定算法/硬件加速时非常有用。

---

## 4.8 ctypes 的性能真相

ctypes 有调用开销，到底有多大？做个基准测试。

```python
import ctypes
import time

lib = ctypes.CDLL('./libfast.so')
lib.add.argtypes = [ctypes.c_int, ctypes.c_int]
lib.add.restype = ctypes.c_int

N = 1_000_000

# 纯 Python 加法
def python_add(a, b):
    return a + b

start = time.time()
for i in range(N):
    python_add(i, 1)
py_time = time.time() - start

# ctypes 调用 C 加法（每次跨边界）
start = time.time()
for i in range(N):
    lib.add(i, 1)
ctypes_time = time.time() - start

print(f"纯 Python: {py_time:.3f}s")
print(f"ctypes 逐次调用: {ctypes_time:.3f}s")
print(f"开销倍数: {ctypes_time/py_time:.1f}x")
```

你会发现 **ctypes 逐次调用比纯 Python 还慢**！因为每次跨语言调用有类型转换、GIL 处理、上下文切换的开销。

**结论（重要）**：

> **不要把 ctypes 调用放在高频循环里。** 正确做法是把整个循环搬到 C 里，Python 只调用一次。

```c
// 错误思路：Python 循环 100 万次，每次调 C 的 add
// 正确思路：Python 调用一次 C 的 batch_add，C 内部循环 100 万次
int batch_add(int *arr, int len) {
    int sum = 0;
    for (int i = 0; i < len; i++) sum += arr[i];
    return sum;
}
```

```python
# 一次调用完成
arr = (ctypes.c_int * N)(*range(N))
result = lib.batch_add(arr, N)  # 只跨一次边界
```

这就是第 1 章「心法一：边界是有成本的」的实证。

---

## 4.9 本章总结

| 知识点 | 内容 |
|--------|------|
| ctypes 定位 | Python 标准库，零安装，调用 C 共享库 |
| 核心机制 | `argtypes`（参数类型）+ `restype`（返回类型）——必须声明 |
| 指针/数组 | `POINTER()`、`byref()`、`类型*长度`、`cast`、`string_at` |
| 结构体 | `Structure` + `_fields_`，字段/顺序/类型须与 C 一致，注意对齐 |
| 回调 | `CFUNCTYPE`，保持引用，异常不传播 |
| 实战 | 调用 OpenSSL EVP API 计算 SHA256 |
| 性能真相 | 逐次调用有开销，批量操作才划算 |

---

## 本章练习

1. 用 ctypes 调用系统的 `strlen` 函数，计算字符串长度。
2. 写一个 C 函数 `void sort_array(int *arr, int len)`（冒泡排序），用 ctypes 调用并验证。
3. 定义一个表示网络 IP 头的结构体（含版本、TTL、源/目的 IP），用 ctypes 解析一段构造的字节数据。
4. 用回调实现一个 C 侧的「遍历数组并打印」，在 Python 回调里做自定义处理。
5. 用 ctypes 调用 OpenSSL 的 MD5 接口（查 EVP_md5），和 hashlib 对比。
6. 做基准测试：对比「Python 循环调 ctypes」和「一次批量调用」的性能差异，验证心法一。

---

**下一章预告**：ctypes 虽然零安装，但类型声明繁琐、读头文件麻烦。下一章学习 **cffi**——它能直接读 C 头文件自动生成绑定，接口更优雅，是纯 Python 项目调用 C 库的更好选择。
