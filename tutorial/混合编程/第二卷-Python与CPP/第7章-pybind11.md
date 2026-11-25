# 第 7 章 pybind11：C++ 与 Python 无缝绑定

## 本章目标

读完这一章，你将能够：

- 理解 pybind11 的设计哲学：header-only、模板魔法、现代 C++
- 把 C++ 函数、类、枚举暴露给 Python
- 处理 STL 容器（vector/map）与 Python 类型的自动转换
- 用 `py::gil_scoped_release` 释放 GIL 实现并行
- 用 pybind11 封装一个真实的安全/AI C++ 库
- 知道为什么 PyTorch 等框架选择 pybind11

---

## 7.1 为什么是 pybind11

前面几种方案都有一个共同问题：**它们在「迁就」C 的接口**。但现代 C++ 项目充满类、模板、STL 容器、异常、智能指针——这些用 ctypes/cffi 几乎无法优雅绑定。

pybind11 解决了这个问题：

- **Header-only**：只需包含头文件，不用链接庞大的库
- **模板魔法**：编译时自动推导类型，几行代码就能绑定复杂 C++ API
- **现代 C++ 友好**：支持 C++11/14/17，类、继承、lambda、智能指针、STL 容器
- **零开销抽象**：生成的绑定代码接近手写 C 扩展的效率
- **工业验证**：PyTorch、TensorFlow、OpenCV、faiss 都在用

> **小白问：pybind11 和 Boost.Python 有什么区别？**
> Boost.Python 是老牌方案，但依赖庞大的 Boost 库、编译慢、C++11 支持差。pybind11 借鉴了它的思路但更轻量现代，现在基本取代了 Boost.Python。

---

## 7.2 安装与第一个绑定

### 7.2.1 安装

```bash
pip install pybind11
```

pybind11 提供 CMake 集成和 Python 头文件路径查询：

```bash
python -m pybind11 --includes
# 输出类似：-I/usr/include/python3.11 -I.../pybind11/include
```

### 7.2.2 最小示例：绑定一个函数

创建 `example.cpp`：

```cpp
#include <pybind11/pybind11.h>

namespace py = pybind11;

int add(int a, int b) {
    return a + b;
}

// PYBIND11_MODULE 是模块入口，名字必须和编译出的扩展名一致
PYBIND11_MODULE(example, m) {
    m.doc() = "pybind11 示例模块";  // 模块文档字符串
    m.def("add", &add, "两个整数相加");
}
```

### 7.2.3 编译方式一：setup.py

```python
# setup.py
from setuptools import setup
import pybind11

setup(
    name="example",
    ext_modules=[{
        "name": "example",
        "sources": ["example.cpp"],
        "include_dirs": [pybind11.get_include()],
        "language": "c++",
        "extra_compile_args": ["-std=c++17", "-O3"],
    }],
)
```

```bash
python setup.py build_ext --inplace
```

### 7.2.4 编译方式二：CMake（推荐大型项目）

```cmake
cmake_minimum_required(VERSION 3.10)
project(example)

find_package(pybind11 REQUIRED)
pybind11_add_module(example example.cpp)
```

```bash
mkdir build && cd build
cmake .. && make
cp example*.so ../
```

### 7.2.5 使用

```python
import example
print(example.add(3, 5))       # 8
print(example.__doc__)         # pybind11 示例模块
print(example.add.__doc__)     # 两个整数相加
```

---

## 7.3 绑定函数：参数、重载、默认参数

### 7.3.1 函数重载

C++ 支持重载，pybind11 用多个 `m.def` 处理：

```cpp
int add(int a, int b) { return a + b; }
double add(double a, double b) { return a + b; }

PYBIND11_MODULE(example, m) {
    m.def("add", py::overload_cast<int, int>(&add), "int 版本");
    m.def("add", py::overload_cast<double, double>(&add), "double 版本");
}
```

`py::overload_cast<参数类型>` 帮编译器选择重载版本。

### 7.3.2 默认参数

```cpp
int greet(int times, const std::string& name = "world") {
    for (int i = 0; i < times; i++)
        std::cout << "Hello, " << name << "!" << std::endl;
    return times;
}

PYBIND11_MODULE(example, m) {
    m.def("greet", &greet, "打招呼",
          py::arg("times"), py::arg("name") = "world");
}
```

Python 调用：

```python
example.greet(3)               # 用默认 name
example.greet(2, "Alice")
example.greet(times=2, name="Bob")  # 关键字参数
```

### 7.3.3 Lambda 作为函数

```cpp
m.def("square", [](double x) { return x * x; }, "求平方");
```

---

## 7.4 绑定类：构造函数、方法、属性

这是 pybind11 最强大的部分。

### 7.4.1 基本类绑定

```cpp
#include <pybind11/pybind11.h>
#include <string>

namespace py = pybind11;

class Packet {
public:
    Packet(std::string src, std::string dst, int ttl)
        : src_(src), dst_(dst), ttl_(ttl) {}

    std::string describe() const {
        return src_ + " -> " + dst_ + " (TTL=" + std::to_string(ttl_) + ")";
    }

    void set_ttl(int ttl) { ttl_ = ttl; }
    int get_ttl() const { return ttl_; }

    std::string src_, dst_;
    int ttl_;
};

PYBIND11_MODULE(example, m) {
    py::class_<Packet>(m, "Packet")
        .def(py::init<std::string, std::string, int>(),
             py::arg("src"), py::arg("dst"), py::arg("ttl"))
        .def("describe", &Packet::describe)
        .def("set_ttl", &Packet::set_ttl)
        .def("get_ttl", &Packet::get_ttl)
        .def_readwrite("src", &Packet::src_)
        .def_readwrite("dst", &Packet::dst_)
        .def_readonly("ttl", &Packet::ttl_);  // 只读属性
}
```

Python 使用：

```python
from example import Packet

p = Packet("192.168.1.1", "10.0.0.1", 64)
print(p.describe())  # 192.168.1.1 -> 10.0.0.1 (TTL=64)
p.set_ttl(32)
print(p.get_ttl())   # 32
p.src = "1.1.1.1"    # 可读写属性
print(p.src)
```

### 7.4.2 绑定类的继承

```cpp
class Animal {
public:
    virtual ~Animal() = default;
    virtual std::string speak() const = 0;
};

class Dog : public Animal {
public:
    std::string speak() const override { return "Woof!"; }
};

PYBIND11_MODULE(example, m) {
    py::class_<Animal>(m, "Animal")
        .def("speak", &Animal::speak);

    py::class_<Dog, Animal>(m, "Dog")  // 第二个参数指定基类
        .def(py::init<>());
}
```

### 7.4.3 智能指针与所有权

pybind11 支持 `std::shared_ptr`、`std::unique_ptr`：

```cpp
#include <memory>

std::shared_ptr<Packet> make_packet(std::string src, std::string dst) {
    return std::make_shared<Packet>(src, dst, 64);
}

PYBIND11_MODULE(example, m) {
    py::class_<Packet, std::shared_ptr<Packet>>(m, "Packet")
        .def(py::init<std::string, std::string, int>());

    m.def("make_packet", &make_packet);
}
```

`py::class_<T, std::shared_ptr<T>>` 告诉 pybind11 用 shared_ptr 管理对象生命周期，避免内存泄漏。**这是现代 C++ 混合编程的推荐做法。**

### 7.4.4 Python 继承 C++ 类（TRAMPOLINE）

更高级的场景：让 Python 类继承 C++ 虚类并覆写方法。需要 `py::trampoline`：

```cpp
class PyAnimal : public Animal {
public:
    using Animal::Animal;

    std::string speak() const override {
        PYBIND11_OVERRIDE_PURE(std::string, Animal, speak);
    }
};
```

这样 Python 可以：

```python
class Cat(example.Animal):
    def speak(self):
        return "Meow!"
```

---

## 7.5 STL 容器与类型转换

pybind11 自动处理常见 STL 容器与 Python 类型的转换（通过 `pybind11/stl.h`）：

```cpp
#include <pybind11/stl.h>

std::vector<int> duplicate(std::vector<int> input) {
    std::vector<int> result;
    for (int x : input) {
        result.push_back(x);
        result.push_back(x);
    }
    return result;
}

std::map<std::string, int> word_count(std::vector<std::string> words) {
    std::map<std::string, int> counts;
    for (auto& w : words) counts[w]++;
    return counts;
}

PYBIND11_MODULE(example, m) {
    m.def("duplicate", &duplicate);
    m.def("word_count", &word_count);
}
```

Python：

```python
print(example.duplicate([1, 2, 3]))  # [1,1,2,2,3,3]
print(example.word_count(["a", "b", "a"]))  # {'a': 2, 'b': 1}
```

**注意**：`stl.h` 的转换是**拷贝**的（Python list → C++ vector 会复制数据）。对于大数组，用 numpy 的 buffer 协议或 `py::array`（见下节）避免拷贝。

### 7.5.1 集成 numpy

```cpp
#include <pybind11/numpy.h>

py::array_t<double> scale_array(py::array_t<double> input, double factor) {
    auto buf = input.request();
    double* ptr = static_cast<double*>(buf.ptr);
    py::array_t<double> result(buf.size);

    for (ssize_t i = 0; i < buf.size; i++) {
        result.mutable_at(i) = ptr[i] * factor;
    }
    return result;
}
```

Python：

```python
import numpy as np
import example

arr = np.array([1.0, 2.0, 3.0])
print(example.scale_array(arr, 2.0))  # [2. 4. 6.]
```

`py::array_t` 直接操作 numpy 数组的内存，是 AI 算子绑定的标准方式。

---

## 7.6 释放 GIL：让 C++ 真正并行

pybind11 默认持有 GIL。长时间运行的 C++ 函数应释放 GIL：

```cpp
#include <pybind11/pybind11.h>

void heavy_computation(int n) {
    // 纯 C++ 计算，不碰 Python 对象
    long long sum = 0;
    for (int i = 0; i < n; i++) sum += i;
}

PYBIND11_MODULE(example, m) {
    m.def("heavy_computation", [](int n) {
        py::gil_scoped_release release;  // 释放 GIL
        heavy_computation(n);
    }, "重计算（释放GIL）");
}
```

释放 GIL 后，其他 Python 线程可以运行。但**释放期间不能调用 Python API、不能碰 py::object**，否则崩溃。

### 7.6.1 结合 C++ 多线程

```cpp
#include <thread>
#include <vector>

void parallel_task(int n, int threads) {
    std::vector<std::thread> pool;
    for (int t = 0; t < threads; t++) {
        pool.emplace_back([&]() {
            for (int i = 0; i < n; i++) { /* 计算 */ }
        });
    }
    for (auto& th : pool) th.join();
}

PYBIND11_MODULE(example, m) {
    m.def("parallel_task", [](int n, int threads) {
        py::gil_scoped_release release;
        parallel_task(n, threads);
    });
}
```

这样 Python 主线程不被阻塞，C++ 用真正的多线程并行。

---

## 7.7 异常处理：C++ 异常 → Python 异常

pybind11 自动把 C++ 异常映射成 Python 异常：

```cpp
#include <stdexcept>

int divide(int a, int b) {
    if (b == 0) throw std::invalid_argument("除数不能为0");
    return a / b;
}
```

Python 调用：

```python
try:
    example.divide(10, 0)
except ValueError as e:  # std::invalid_argument → ValueError
    print(e)  # 除数不能为0
```

映射关系：

| C++ 异常 | Python 异常 |
|---------|------------|
| `std::invalid_argument` | `ValueError` |
| `std::out_of_range` | `IndexError` |
| `std::runtime_error` | `RuntimeError` |
| `std::bad_alloc` | `MemoryError` |

也可以自定义异常：

```cpp
py::register_exception<MyException>(m, "MyException");
```

---

## 7.8 实战：用 pybind11 封装一个高性能安全库

假设我们有一个 C++ 写的快速端口扫描核心（简化版），要暴露给 Python。

### 7.8.1 C++ 核心

```cpp
// scanner.cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <string>

namespace py = pybind11;

struct ScanResult {
    int port;
    bool open;
    std::string service;
};

std::vector<ScanResult> scan_ports(const std::string& host,
                                    const std::vector<int>& ports) {
    std::vector<ScanResult> results;
    // 实际实现会用 socket 连接（此处简化为演示）
    for (int port : ports) {
        bool is_open = (port % 2 == 0);  // 演示逻辑
        std::string service = is_open ? "open" : "closed";
        results.push_back({port, is_open, service});
    }
    return results;
}

PYBIND11_MODULE(scanner, m) {
    py::class_<ScanResult>(m, "ScanResult")
        .def(py::init<int, bool, std::string>())
        .def_readwrite("port", &ScanResult::port)
        .def_readwrite("open", &ScanResult::open)
        .def_readwrite("service", &ScanResult::service)
        .def("__repr__", [](const ScanResult& r) {
            return "<ScanResult port=" + std::to_string(r.port) +
                   " open=" + (r.open ? "true" : "false") + ">";
        });

    m.def("scan_ports", &scan_ports, "扫描端口",
          py::arg("host"), py::arg("ports"));
}
```

### 7.8.2 Python 侧使用

```python
import scanner

results = scanner.scan_ports("192.168.1.1", [21, 22, 80, 443, 3306])
for r in results:
    if r.open:
        print(f"端口 {r.port} 开放: {r.service}")
```

### 7.8.3 结合 Python 生态

```python
import scanner
import pandas as pd

results = scanner.scan_ports("127.0.0.1", list(range(1, 1001)))
df = pd.DataFrame([{"port": r.port, "open": r.open} for r in results])
open_ports = df[df['open']]['port'].tolist()
print(f"开放端口: {open_ports}")
```

**这就是混合编程的威力**：C++ 做高性能扫描核心，Python 做数据处理和展示，各取所长。

> **合规提醒**：端口扫描必须在授权环境（自己的靶机、CTF、书面授权的目标）进行。未经授权扫描他人系统违法。

---

## 7.9 pybind11 与 PyTorch： C++ 扩展的真实形态

PyTorch 的 `torch.utils.cpp_extension` 就是基于 pybind11。一个典型的自定义算子：

```cpp
#include <torch/extension.h>

torch::Tensor custom_relu(torch::Tensor x) {
    return x.clamp_min(0);
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("custom_relu", &custom_relu, "自定义 ReLU");
}
```

编译后 `import` 即可用。这解释了第 1 章讲的 PyTorch 架构：Python 前端 → pybind11 → C++ 核心 → CUDA 内核。

---

## 7.10 本章总结

| 知识点 | 内容 |
|--------|------|
| pybind11 定位 | Header-only，现代 C++ 绑定库，AI 框架标配 |
| 函数绑定 | `m.def`，重载用 `overload_cast`，默认参数用 `py::arg` |
| 类绑定 | `py::class_` + `py::init`，属性用 `def_readwrite/readonly` |
| 继承/智能指针 | `class_<Derived, Base>`，`class_<T, shared_ptr<T>>` 管理生命周期 |
| STL 转换 | `pybind11/stl.h` 自动转换 vector/map（拷贝）；numpy 用 `py::array_t`（零拷贝） |
| GIL | `py::gil_scoped_release` 释放 GIL，可结合 C++ 多线程 |
| 异常 | C++ 异常自动映射 Python 异常 |
| 实战 | 封装 C++ 端口扫描核心，Python 做分析与展示 |
| 代表项目 | PyTorch、TensorFlow、OpenCV、faiss |

---

## 本章练习

1. 编译最小示例，绑定一个函数并从 Python 调用。
2. 绑定一个带重载和默认参数的函数，用关键字参数调用。
3. 绑定一个 C++ 类（含构造、方法、属性），在 Python 里使用。
4. 用 `std::shared_ptr` 管理类对象，验证生命周期。
5. 用 `py::array_t` 写一个 numpy 数组处理函数，避免拷贝。
6. 用 `py::gil_scoped_release` + `std::thread` 写一个并行计算函数，测量加速。
7. 让 C++ 函数抛异常，在 Python 里捕获，验证异常映射。

---

**下一章预告**：pybind11 是「写 C++ 包装代码暴露给 Python」。下一章学习 **Python C API**——最底层、最原始的官方方案：直接用 C 写 Python 扩展模块，以及在 C/C++ 程序里**嵌入 Python 解释器**（让 C 程序能执行 Python 脚本）。这是理解所有绑定工具底层原理的钥匙。
