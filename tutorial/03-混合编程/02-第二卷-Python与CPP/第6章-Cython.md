# 第 6 章 Cython：给 Python 代码编译加速

## 本章目标

读完这一章，你将能够：

- 理解 Cython 的定位：Python 的超集，渐进式加速
- 用 `cdef` 声明 C 类型，把动态 Python 变量变成静态 C 变量
- 编译 `.pyx` 成 Python 扩展模块
- 用 Cython 调用 C 函数、封装 C 库
- 掌握 `with nogil` 释放 GIL 实现真并行
- 知道如何用性能分析找到该加速的热点

---

## 6.1 Cython 是什么

Cython 是 **Python 的超集**：`.pyx` 文件里的代码大部分是 Python，但可以加 C 类型声明，然后被编译成 C 代码，再编译成 Python 扩展模块。

**核心卖点**：

- **渐进式**：你可以只给热点函数加类型，其他代码保持纯 Python
- **加速显著**：数值计算、循环密集型代码可提速 10~100 倍
- **能调 C**：可以直接 `cdef extern` 声明并调用 C 函数
- **工业级**：numpy、pandas、scikit-learn、lxml 都在用

**和 ctypes/cffi 的区别**：

| | ctypes/cffi | Cython |
|--|------------|--------|
| 方向 | Python 调现成 C 库 | 把 Python 代码变成 C、或包装 C 库 |
| 代码形态 | Python + 声明 | `.pyx`（Python+C 混合语法） |
| 编译 | ABI 模式无需编译 | 必须编译 |
| 适用 | 调外部库 | 加速自己的代码 |

---

## 6.2 安装与第一个 Cython 程序

```bash
pip install cython
```

### 6.2.1 编译流程三件套

**第一步**：写 `.pyx` 文件 `fastsum.pyx`：

```cython
# fastsum.pyx

def py_sum(int n):
    """纯 Python 风格的循环（动态类型）"""
    cdef long total = 0
    cdef int i
    for i in range(n):
        total += i
    return total
```

注意 `cdef` 关键字——这是 Cython 的核心，声明 C 类型变量。

**第二步**：写 `setup.py`：

```python
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("fastsum.pyx", language_level=3),
)
```

**第三步**：编译：

```bash
python setup.py build_ext --inplace
```

生成 `fastsum.c` 和 `fastsum.cpython-xxx.so`（扩展模块）。

**第四步**：像普通模块一样导入：

```python
import fastsum
import time

n = 10_000_000
start = time.time()
result = fastsum.py_sum(n)
print(f"结果: {result}, 耗时: {time.time()-start:.3f}s")
```

### 6.2.2 加速效果对比

写一个纯 Python 版本对比：

```python
def pure_sum(n):
    total = 0
    for i in range(n):
        total += i
    return total
```

经验值：加类型的 Cython 版本通常比纯 Python 快 **20~50 倍**（主要省去了循环中每次操作的 Python 对象装箱/类型检查）。

> **小白问：为什么加个 `cdef int` 就快这么多？**
> 纯 Python 里，`i` 和 `total` 是 Python 对象（有类型信息、引用计数、动态分派）。每次 `total += i` 都要：检查两个对象类型、找到 `+` 的实现、创建新对象、更新引用计数……
>
> Cython 的 `cdef long total` 把它变成裸 C 的 `long` 变量，`total += i` 直接编译成一条 CPU 指令。没有对象、没有类型检查、没有装箱拆箱。这就是性能差距的来源。

---

## 6.3 Cython 语法核心

### 6.3.1 `cdef` 声明变量

```cython
cdef int a = 10
cdef double x = 3.14
cdef long long big = 1234567890123
cdef char* s
cdef int* arr
```

### 6.3.2 `cdef` 声明函数

```cython
cdef int helper(int a, int b):
    """cdef 函数：只能在 Cython 内部调用，不暴露给 Python（更快）"""
    return a + b

def public_func(int a, int b):
    """def 函数：暴露给 Python 调用"""
    return helper(a, b)
```

- `cdef` 函数：纯 C 函数，调用开销小，Python 不可见
- `def` 函数：Python 可见，有边界开销
- `cpdef` 函数：两者兼顾，既生成 C 函数又暴露 Python 接口

### 6.3.3 类型化函数参数

```cython
def compute(int n, double factor):
    cdef int i
    cdef double total = 0.0
    for i in range(n):
        total += factor * i
    return total
```

参数声明类型后，Python 调用时 Cython 会自动转换（并检查类型）。

### 6.3.4 结构体与 C 类型

```cython
cdef struct Point:
    double x
    double y

cdef Point p
p.x = 1.0
p.y = 2.0
```

---

## 6.4 调用 C 库：`cdef extern`

Cython 可以直接声明外部 C 函数并调用：

```cython
# cdef extern from "math.h":
#     double sqrt(double x)

# 使用系统库
cdef extern from "math.h":
    double sqrt(double x)
    double sin(double x)

def compute_hypot(double a, double b):
    return sqrt(a*a + b*b)
```

编译时需要链接数学库，在 `setup.py` 里：

```python
setup(
    ext_modules=cythonize(...),
    libraries=['m'],  # Linux 链接 libm
)
```

### 6.4.1 声明结构体和函数

```cython
cdef extern from "libfast.h":
    struct Packet:
        char type
        int length
        char flag

    int add(int a, int b)
    int array_max(int *arr, int len)
    void free_string(char *p)

def wrap_array_max(list data):
    """把 Python list 转成 C 数组，调用 C 函数"""
    cdef int[::1] arr = array('i', data)  # memoryview，见下节
    return array_max(&arr[0], len(data))
```

---

## 6.5 memoryview：零拷贝访问缓冲区

Cython 的 `memoryview`（类型化内存视图）能直接访问 numpy 数组、bytes 等缓冲区，无需拷贝。

```cython
# fastscale.pyx
cdef extern from "math.h":
    double sqrt(double)

def scale_array(double[::1] arr, double factor):
    """原地缩放 numpy 数组（零拷贝）"""
    cdef int i
    cdef int n = arr.shape[0]
    for i in range(n):
        arr[i] *= factor
    return arr

def norm(double[::1] arr):
    """计算向量范数"""
    cdef int i
    cdef double total = 0.0
    for i in range(arr.shape[0]):
        total += arr[i] * arr[i]
    return sqrt(total)
```

`double[::1]` 表示「一维、连续的 double 数组」。调用时传 numpy 数组：

```python
import numpy as np
import fastscale

arr = np.array([1.0, 2.0, 3.0, 4.0])
fastscale.scale_array(arr, 2.0)
print(arr)  # [2. 4. 6. 8.] —— 原地修改，零拷贝
print(fastscale.norm(arr))  # 10.0
```

**这是 AI 场景的关键技术**：numpy 数组的底层是连续 C 内存，Cython 直接操作它，没有拷贝开销。

> **注意**：`[::1]` 要求内存连续。如果传入非连续数组（如切片 `arr[::2]`），会报错。用 `arr = np.ascontiguousarray(arr)` 保证连续。

---

## 6.6 释放 GIL：`with nogil`

Cython 默认持有 GIL。如果循环是纯 C 计算（不碰 Python 对象），可以释放 GIL 让其他线程运行，甚至用 OpenMP 多线程并行。

```cython
# cimport 是 Cython 的 import（编译期）
from cython.parallel import prange

cimport cython

@cython.boundscheck(False)      # 关闭边界检查（更快，但要自己保证不越界）
@cython.wraparound(False)       # 关闭负索引
def parallel_sum(double[::1] arr):
    cdef int i
    cdef double total = 0.0
    cdef int n = arr.shape[0]

    with nogil:
        for i in prange(n):     # prange 用 OpenMP 并行
            total += arr[i]
    return total
```

编译需要 OpenMP 支持，`setup.py`：

```python
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

extensions = [
    Extension(
        "parallel",
        ["parallel.pyx"],
        extra_compile_args=["-fopenmp"],
        extra_link_args=["-fopenmp"],
        include_dirs=[np.get_include()],
    )
]
setup(ext_modules=cythonize(extensions, language_level=3))
```

**GIL 规则（重要）**：

- `with nogil` 块里**不能**访问 Python 对象、不能调用 Python 函数
- 只能操作 C 类型变量、C 函数、memoryview
- 需要 Python 操作时，用 `with gil:` 重新获取

---

## 6.7 实战：用 Cython 加速 AI/安全代码

### 6.7.1 案例一：快速计算余弦相似度（AI 常用）

```cython
# similarity.pyx
cimport cython
from libc.math cimport sqrt

@cython.boundscheck(False)
@cython.wraparound(False)
def cosine_similarity(double[::1] a, double[::1] b):
    cdef int i, n = a.shape[0]
    cdef double dot = 0.0, norm_a = 0.0, norm_b = 0.0
    with nogil:
        for i in range(n):
            dot += a[i] * b[i]
            norm_a += a[i] * a[i]
            norm_b += b[i] * b[i]
    return dot / (sqrt(norm_a) * sqrt(norm_b))
```

对比 numpy 版本，Cython 版在向量维度小时可能更快（省去 numpy 的临时数组分配），且可与循环融合。

### 6.7.2 案例二：恶意软件字节特征提取（安全常用）

安全分析中常统计文件的字节直方图（256 个 bin），作为恶意软件检测特征：

```cython
# features.pyx
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
def byte_histogram(unsigned char[::1] data):
    """统计字节直方图，返回 256 维计数"""
    cdef unsigned long long[256] hist
    cdef int i
    cdef int n = data.shape[0]

    # 初始化
    for i in range(256):
        hist[i] = 0

    with nogil:
        for i in range(n):
            hist[data[i]] += 1

    # 转 Python list
    return [hist[i] for i in range(256)]
```

调用：

```python
import numpy as np
import features

data = np.fromfile("suspicious.bin", dtype=np.uint8)
hist = features.byte_histogram(data)
# 把 hist 喂给 sklearn 分类器做恶意软件检测
```

纯 Python 逐字节统计一个 10MB 文件要几秒，Cython 版几十毫秒。

---

## 6.8 性能分析：先找热点再加速

**不要盲目加速**。正确流程：

1. **先用 `cProfile` 找到真正的热点**
2. 只把热点函数用 Cython 重写
3. 验证正确性 + 测量加速比

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# ... 运行你的程序 ...
profiler.disable()
pstats.Stats(profiler).sort_stats('cumulative').print_stats(20)
```

`cumulative` 列显示累计耗时，最上面就是该优化的热点。

> **经验**：80% 的时间花在 20% 的代码上。找到那 20%，用 Cython/C/Rust 重写它。

---

## 6.9 Cython 调试与发布实践

### 6.9.1 生成 HTML 注解视图

Cython 有个强大的调试工具：`cythonize -a`，会生成 HTML 文件，用颜色标注每行代码生成了多少 C 代码。

```bash
cythonize -a -i fastsum.pyx
# 生成 fastsum.html
```

在浏览器打开 `fastsum.html`：
- **浅黄色**行：生成了少量 C 代码（好）
- **深黄色**行：生成了大量 C 代码（可能有 Python 操作介入，是优化热点）

点击行号还能展开对应的 C 代码。这是找出「哪里不小心触发了 Python 操作」的利器。如果一行本以为是纯 C 计算却显示为深黄，通常是因为用了 Python 对象而非 C 类型。

### 6.9.2 常见性能陷阱

| 陷阱 | 现象 | 解决 |
|------|------|------|
| 忘记给变量加 `cdef` | 循环里仍是 Python 对象操作 | 给循环变量和累加器加类型 |
| 用 Python list 而非 memoryview | 每次访问有类型检查 | 用 `double[::1]` memoryview |
| 保留边界检查 | 每次访问检查越界 | `@cython.boundscheck(False)`（自己保证不越界） |
| 负索引支持 | 额外开销 | `@cython.wraparound(False)` |
| 频繁调用小函数 | 边界开销累积 | 用 `cdef` 函数（纯 C 调用） |
| 字符串操作 | Python 对象开销 | 用 C `char*`（需注意编码） |

### 6.9.3 发布 Cython 扩展

用 `pyproject.toml` + `setup.py` 让用户 `pip install` 时能自动编译：

```toml
# pyproject.toml
[build-system]
requires = ["setuptools", "wheel", "Cython>=3.0"]
build-backend = "setuptools.build_meta"
```

```python
# setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

setup(
    name="fastsum",
    version="0.1.0",
    ext_modules=cythonize(
        [Extension("fastsum", ["fastsum.pyx"], include_dirs=[np.get_include()])],
        compiler_directives={"language_level": 3},
    ),
    zip_safe=False,
)
```

发布到 PyPI 时，可以预编译各平台 wheel（用 cibuildwheel），让用户免编译直接安装。

### 6.9.4 Cython 与 Pypy 的关系

Cython 和 PyPy 都是加速 Python 的方案，但思路不同：
- **Cython**：编译时加类型，生成 C 扩展（需要编译步骤，类型显式）
- **PyPy**：运行时 JIT 编译，无需改代码（对纯 Python 代码友好，但 C 扩展兼容性差）

现实选择：如果项目依赖大量 C 扩展（numpy 等），PyPy 常不兼容，Cython 更稳妥。本教程聚焦 Cython，因为它在工业界（numpy/pandas）和混合编程场景更通用。

---

## 6.10 本章总结

| 知识点 | 内容 |
|--------|------|
| Cython 定位 | Python 超集，渐进式加类型编译加速 |
| 编译流程 | `.pyx` → setup.py + cythonize → build_ext --inplace |
| `cdef` | 声明 C 变量/函数；`def` 暴露 Python；`cpdef` 两者兼顾 |
| `cdef extern` | 声明并调用 C 库函数/结构体 |
| memoryview | `double[::1]` 零拷贝访问 numpy 数组 |
| GIL | `with nogil` 释放 GIL，`prange` OpenMP 并行；块内不能碰 Python 对象 |
| 装饰优化 | `@cython.boundscheck(False)` 关闭检查提速 |
| 实战 | 余弦相似度、字节直方图（恶意软件特征） |
| 方法论 | 先 cProfile 找热点，再选择性加速 |

---

## 本章练习

1. 编译 `fastsum.pyx`，对比纯 Python 和 Cython 版本的耗时。
2. 写一个 Cython 函数计算数组的元素平方和，用 memoryview 接收 numpy 数组。
3. 用 `cdef extern` 调用 C 标准库的 `abs` 或 `pow`。
4. 用 `with nogil` + `prange` 写一个并行求和，测量多线程加速比。
5. 用 `cProfile` 分析一个你写的程序，找出热点函数。
6. 扩展字节直方图例子：同时统计「可打印字符占比」「熵」等特征。

---

**下一章预告**：Cython 是「Python 代码加类型编译」。下一章学习 **pybind11**——从 C++ 出发，把现代 C++ 类和函数优雅地暴露给 Python。它是 PyTorch、TensorFlow 等 AI 框架的绑定方案，是 C++ 项目对接 Python 的首选。
