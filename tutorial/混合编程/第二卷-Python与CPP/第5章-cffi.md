# 第 5 章 cffi：更优雅的 C 接口

## 本章目标

读完这一章，你将能够：

- 理解 cffi 相比 ctypes 的优势
- 掌握 cffi 的两种模式：ABI 模式（dlopen）和 API 模式（生成扩展）
- 用 `cdef` 声明 C 接口，用 `ffi` 处理类型、结构体、指针
- 直接从 C 头文件生成绑定（节省大量手写声明）
- 知道什么场景选 cffi、什么场景选 ctypes

---

## 5.1 为什么需要 cffi

ctypes 能用，但有几个痛点：

1. **类型声明繁琐**：每个函数都要写 `argtypes`/`restype`，易错
2. **不能读头文件**：C 头文件的声明要手动翻译成 Python，重复劳动
3. **C++ 支持弱**：只能调 `extern "C"` 函数
4. **代码不够像 C**：ctypes 的类型系统比较 Python 化，和 C 代码对不上

cffi 解决了这些问题。它的核心理念是：**用接近 C 的语法声明接口**，甚至直接读头文件。

cffi 有两种工作模式：

| 模式 | 工作原理 | 优点 | 缺点 |
|------|---------|------|------|
| **ABI 模式** | 运行时 `dlopen` 动态库，类似 ctypes | 无需编译，即写即用 | 每次调用有解析开销 |
| **API 模式** | 编译时生成 C 扩展模块 | 调用快，能内联 C 代码 | 需要编译步骤 |

---

## 5.2 安装与快速上手

```bash
pip install cffi
```

### 5.2.1 ABI 模式：第一个例子

```python
from cffi import FFI

ffi = FFI()

# 用类 C 语法声明接口（一个字符串搞定）
ffi.cdef("""
    int add(int a, int b);
    double divide(double a, double b);
""")

# 加载动态库
lib = ffi.dlopen("./libfast.so")

# 直接调用，无需声明 argtypes
print(lib.add(3, 5))       # 8
print(lib.divide(10.0, 3.0))  # 3.333...
```

对比 ctypes：cffi 用一段 `cdef` 字符串替代了所有 `argtypes`/`restype` 声明，更接近 C 代码原貌，可读性更好。

> **小白问：ABI 模式下 cffi 和 ctypes 本质一样吗？**
> 是的，底层都是 `dlopen` + `dlsym`。但 cffi 在调用时会做更严格的类型检查，且在 API 模式下能编译成扩展获得性能提升。cffi 的类型系统也更贴近 C。

---

## 5.3 类型、指针与内存管理

### 5.3.1 基本类型与 `ffi.new`

cffi 用 `ffi.new()` 分配 C 内存：

```python
from cffi import FFI
ffi = FFI()
ffi.cdef("void increment(int *p);")
lib = ffi.dlopen("./libfast.so")

# 分配一个 int，初值 10
p = ffi.new("int *", 10)
print(p[0])          # 10，用 [0] 解引用
lib.increment(p)
print(p[0])          # 11
```

`ffi.new("int *", 10)` 相当于 C 的 `int x = 10; int *p = &x;`。返回的指针对象生命周期由 Python 管理（引用计数），离开作用域自动释放——**比 ctypes 更安全**。

### 5.3.2 数组

```python
ffi.cdef("int sum(int *arr, int len);")

# 分配一个 5 元素 int 数组
arr = ffi.new("int[5]", [1, 2, 3, 4, 5])
print(lib.sum(arr, 5))   # 15

# 访问元素
print(arr[2])  # 3
```

### 5.3.3 字符串

```python
ffi.cdef("""
    char* reverse_string(const char* s);
    void free_string(char* p);
""")

# Python str → C char*（cffi 自动编码，但需指定）
s = ffi.new("char[]", b"hello")   # 注意用 bytes
ptr = lib.reverse_string(s)

# C char* → Python bytes
result = ffi.string(ptr).decode('utf-8')
print(result)  # olleh

# 释放 C 分配的内存（谁分配谁释放）
lib.free_string(ptr)
```

`ffi.string(ptr)` 把 C 字符串（到 `\0` 为止）读成 Python bytes。

### 5.3.4 结构体

```python
ffi.cdef("""
    struct Packet {
        char  type;
        int   length;
        char  flag;
    };
    void process_packet(struct Packet *p);
""")

p = ffi.new("struct Packet *")
p.type = b'T'
p.length = 1024
p.flag = b'1'
print(ffi.sizeof("struct Packet"))  # 12（和 C 一致）
lib.process_packet(p)
```

cffi 会按 C 规则处理对齐，结构体布局和 C 编译器一致。

### 5.3.5 内存分配函数

| 函数 | 用途 |
|------|------|
| `ffi.new("type")` | 分配并初始化，Python 管理生命周期 |
| `ffi.new_allocator()` | 自定义分配器 |
| `ffi.from_buffer(...)` | 从 Python buffer（如 bytes/bytearray/numpy 数组）创建 C 指针（零拷贝！） |
| `ffi.string(ptr)` | C 字符串 → Python bytes |
| `ffi.buffer(ptr, size)` | C 内存 → Python buffer 对象（零拷贝视图） |

**`ffi.from_buffer` 是性能关键**——能让 Python 的 bytes/numpy 数组直接作为 C 指针传入，无需拷贝。第 17 章会深入讲零拷贝。

---

## 5.4 从头文件自动生成绑定

cffi 最大的优势之一：可以直接读 C 头文件，不用手写 `cdef`。

假设有 `libfast.h`：

```c
int add(int a, int b);
double divide(double a, double b);
void process_packet(struct Packet *p);
```

用 `ffibuilder` 读头文件：

```python
# build_binding.py
from cffi import FFI

ffibuilder = FFI()

# 读头文件内容作为 cdef
with open("libfast.h") as f:
    ffibuilder.cdef(f.read())

# 设置要链接的库
ffibuilder.set_source(
    "_fast_binding",       # 生成的模块名
    '#include "libfast.h"',
    libraries=['fast'],    # 链接 libfast.so
    library_dirs=['.'],
)

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
```

运行 `python build_binding.py`，生成 `_fast_binding.c` 和 `_fast_binding...so`。然后：

```python
from _fast_binding import ffi, lib
print(lib.add(3, 5))
```

**这就是为什么 cffi 适合有大量头文件的项目**——省去手写声明的痛苦。

> **注意**：头文件里如果有复杂的宏、条件编译、C++ 语法，cffi 的解析器可能处理不了，需要手动精简。这是它的局限。

---

## 5.5 API 模式：编译成扩展获得性能

ABI 模式每次调用需要解析参数，有开销。API 模式把它编译成真正的 Python 扩展模块，调用更快。

### 5.5.1 内联 C 代码

API 模式还能在绑定里直接写 C 函数（把 Python 和 C 代码写在一起）：

```python
# build_api.py
from cffi import FFI

ffibuilder = FFI()

ffibuilder.cdef("""
    int fast_sum(int *arr, int len);
""")

# 下面的 C 代码会被编译进扩展
ffibuilder.set_source("_fastapi", """
    static int fast_sum(int *arr, int len) {
        int s = 0;
        for (int i = 0; i < len; i++) s += arr[i];
        return s;
    }
""")

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
```

编译后：

```python
from _fastapi import ffi, lib
arr = ffi.new("int[]", list(range(1000)))
print(lib.fast_sum(arr, 1000))  # 499500
```

### 5.5.2 两种模式对比

```python
import time
# ABI 模式（ctypes-like）
from cffi import FFI
ffi = FFI()
ffi.cdef("int add(int a, int b);")
lib_abi = ffi.dlopen("./libfast.so")

N = 500_000
start = time.time()
for i in range(N):
    lib_abi.add(i, 1)
abi_time = time.time() - start

# API 模式（编译扩展）
# from _fastapi import lib as lib_api
# ... 类似测试

print(f"ABI 模式: {abi_time:.3f}s")
```

API 模式比 ABI 模式快 2~5 倍（少了运行时解析），但仍比纯 C 直接调用慢一点（有 Python↔C 边界开销）。**再次印证：批量操作才是王道。**

---

## 5.6 回调与高级特性

### 5.6.1 回调

```python
from cffi import FFI
ffi = FFI()
ffi.cdef("void for_each(int *arr, int len, void (*cb)(int));")
lib = ffi.dlopen("./libfast.so")

@ffi.def_extern()
def py_callback(value):
    print(f"回调收到: {value}")

# 注意：cffi 回调需要用 ffi.callback 或 @ffi.def_extern（API 模式）
CALLBACK = ffi.callback("void(int)", py_callback)
arr = ffi.new("int[]", [1, 2, 3])
lib.for_each(arr, 3, CALLBACK)
```

保持 `CALLBACK` 的引用直到调用完成，否则可能崩溃。

### 5.6.2 `ffi.cast`：类型转换

```python
# 把 void* 转成具体类型指针
p = ffi.cast("int *", void_ptr)
print(p[0])
```

### 5.6.3 变长参数

C 的变长参数函数（如 `printf`）在 cffi 里需要特殊声明：

```python
ffi.cdef("int printf(const char *fmt, ...);")
lib = ffi.dlopen(None)  # None 表示当前进程
lib.printf(b"hello %d\n", 42)
```

---

## 5.7 实战：用 cffi 解析网络数据包

做一个安全场景的实战：用 cffi 定义 IP/TCP 头结构体，解析一段原始字节。

```python
from cffi import FFI
import struct

ffi = FFI()

ffi.cdef("""
    struct IPHeader {
        unsigned char  ihl_version;   // 低4位首部长度，高4位版本
        unsigned char  tos;
        unsigned short total_len;
        unsigned short id;
        unsigned short frag;
        unsigned char  ttl;
        unsigned char  protocol;
        unsigned short checksum;
        unsigned char  src_ip[4];
        unsigned char  dst_ip[4];
    };

    struct TCPHeader {
        unsigned short src_port;
        unsigned short dst_port;
        unsigned int   seq;
        unsigned int   ack;
        unsigned char  data_offset;
        unsigned char  flags;
        unsigned short window;
        unsigned short checksum;
        unsigned short urgent;
    };
""")

def parse_packet(packet_bytes):
    """解析一个 IPv4 + TCP 数据包"""
    # 把 Python bytes 映射到 C 结构体（零拷贝视图）
    ip = ffi.cast("struct IPHeader *", ffi.from_buffer(packet_bytes))

    version = ip.ihl_version >> 4
    ihl = (ip.ihl_version & 0x0F) * 4
    ttl = ip.ttl
    proto = ip.protocol
    src = ".".join(str(ip.src_ip[i]) for i in range(4))
    dst = ".".join(str(ip.dst_ip[i]) for i in range(4))

    print(f"版本: IPv{version}, 首部长度: {ihl} 字节")
    print(f"TTL: {ttl}, 协议: {proto} (6=TCP)")
    print(f"源 IP: {src} → 目的 IP: {dst}")

    if proto == 6:  # TCP
        tcp = ffi.cast("struct TCPHeader *", ffi.from_buffer(packet_bytes + ihl))
        sport = (tcp.src_port >> 8) | ((tcp.src_port & 0xFF) << 8)  # 网络字节序转换
        dport = (tcp.dst_port >> 8) | ((tcp.dst_port & 0xFF) << 8)
        print(f"TCP 端口: {sport} → {dport}, flags=0x{tcp.flags:02x}")

if __name__ == "__main__":
    # 构造一个示例 IP+TCP 包（简化）
    packet = bytes([
        0x45, 0x00, 0x00, 0x28,  # version/ihl, tos, total_len
        0x00, 0x01, 0x00, 0x00,  # id, frag
        0x40, 0x06, 0x00, 0x00,  # ttl=64, proto=6(TCP), checksum
        192, 168, 1, 1,          # src ip
        10, 0, 0, 1,             # dst ip
        # TCP 头
        0x00, 0x50, 0x1F, 0x90,  # src port 80, dst port 8080（网络字节序）
        0x00, 0x00, 0x00, 0x01,  # seq
        0x00, 0x00, 0x00, 0x00,  # ack
        0x50, 0x02, 0x10, 0x00,  # data offset, flags(SYN), window
        0x00, 0x00, 0x00, 0x00,  # checksum, urgent
    ])
    parse_packet(packet)
```

这个例子展示了 cffi 的 `ffi.cast` + `ffi.from_buffer` 组合：把 Python bytes **零拷贝**地当作 C 结构体访问。这是网络协议解析、恶意软件二进制分析的常用技巧。

> **安全提示**：解析不可信数据时，务必检查长度！上面代码假设包长度足够，如果传入短包会越界读取。生产代码要先验证 `len(packet_bytes) >= sizeof(IPHeader)`。

---

## 5.8 ctypes vs cffi：如何选择

| 维度 | ctypes | cffi |
|------|--------|------|
| 安装 | 标准库，零安装 | 需 `pip install cffi` |
| 类型声明 | `argtypes`/`restype`，繁琐 | `cdef` 类 C 语法，简洁 |
| 读头文件 | 不支持 | ABI 模式需手动，可脚本读 |
| C++ 支持 | 弱 | 弱（都需 extern "C"） |
| 性能 | ABI 调用开销 | API 模式更快 |
| 内存安全 | 手动管理，易错 | `ffi.new` 自动管理更安全 |
| 零拷贝 | `from_buffer`（有限） | `ffi.from_buffer` 更灵活 |
| 适用场景 | 快速调用、无第三方依赖 | 大型 C 库绑定、需要读头文件 |

**选择建议**：
- 只是快速调一两个函数、不想装东西 → **ctypes**
- 要绑定一个有很多函数的 C 库、有头文件 → **cffi**
- 追求性能 → **cffi API 模式** 或直接上 **pybind11/Cython**

---

## 5.9 本章总结

| 知识点 | 内容 |
|--------|------|
| cffi 定位 | 更优雅的 C 接口，两种模式：ABI（运行时）/API（编译） |
| 核心 | `ffi.cdef` 声明接口，`ffi.new` 分配内存，无需 argtypes |
| 内存 | `ffi.new` 由 Python 管理；`ffi.from_buffer` 零拷贝；`ffi.string` 读字符串 |
| 结构体 | 按 C 规则对齐，和 C 布局一致 |
| 读头文件 | 用 `ffibuilder.cdef(open(...).read())` 自动生成声明 |
| API 模式 | 编译成扩展，更快，可内联 C 代码 |
| 实战 | 用 cast+from_buffer 零拷贝解析 IP/TCP 包头 |
| 选型 | 简单调用用 ctypes，复杂绑定用 cffi |

---

## 本章练习

1. 用 cffi ABI 模式调用 `libfast.so` 的全部 5 个函数。
2. 用 `ffi.from_buffer` 把一个 numpy 数组传给 C 函数（提示：numpy 数组支持 buffer 协议）。
3. 写一个 `build.py` 用 `ffibuilder` 读 `libfast.h` 生成绑定模块。
4. 用 API 模式内联一个 C 函数，编译后调用，对比 ABI 模式的性能。
5. 扩展数据包解析例子：加入 UDP 头解析，并校验包长度防止越界。
6. 对比 ctypes 和 cffi 实现同一功能的代码量，谈谈你的体会。

---

**下一章预告**：ctypes 和 cffi 都是「从 Python 调 C」。下一章学习 **Cython**——Python 的超集，能给你现有的 Python 代码**渐进式加类型、编译加速**。numpy、pandas 都在用它，是给纯 Python 热点提速的利器。
