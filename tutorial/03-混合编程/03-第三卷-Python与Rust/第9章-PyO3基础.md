# 第 9 章 PyO3：用 Rust 写 Python 扩展

## 本章目标

读完这一章，你将能够：

- 理解 PyO3 的定位：Rust 写 Python 扩展的现代方案
- 用 PyO3 写第一个 Rust 扩展模块
- 理解 `#[pyfunction]`、`#[pymodule]`、`#[pyclass]` 三大宏
- 掌握 Rust 与 Python 的基本类型转换
- 理解 PyO3 的错误处理（`PyResult`）
- 知道为什么 HuggingFace tokenizers 等选择 PyO3

---

## 9.1 为什么用 Rust 做 Python 扩展

你可能会问：Python↔C/C++ 的方案已经很多了（ctypes、cffi、Cython、pybind11），为什么还要用 Rust？

**因为 Rust 在安全关键点上有不可替代的优势**：

| 优势 | 说明 |
|------|------|
| **内存安全** | 所有权系统编译期消除缓冲区溢出、UAF、Double Free——安全工具的刚需 |
| **无 GIL 负担** | 可轻松释放 GIL 做真并行，Rust 本身无 GC |
| **性能** | 与 C 相当，零成本抽象 |
| **现代工具链** | cargo 管理依赖，比 C/C++ 的构建体验好太多 |
| **并发安全** | 编译期防止数据竞争，`Send`/`Sync` 保证 |

代价是学习曲线（所有权/借用）。但如果你已经学过本系列的《系统语言卷》Rust 部分，这里会很顺。

**真实案例**：
- **HuggingFace tokenizers**：Rust 核心，PyO3 绑定，分词提速数十倍
- **polars**：Rust 写的 DataFrame，PyO3 暴露给 Python，比 pandas 快很多
- **pydantic-core**：pydantic v2 的 Rust 核心，验证提速 5-50 倍
- **cryptography**：部分加密原语用 Rust
- **ruff**：Rust 写的 Python linter，比 flake8 快 100 倍

> **小白问：这些工具都是纯 Rust 应用，只是顺便给 Python 用吗？**
> 不，它们是**专门为 Python 设计的库**，核心逻辑用 Rust 写，通过 PyO3 提供 Python API。用户 `import` 时感觉就是在用 Python 库，但底层是 Rust。这正是混合编程的理想形态。

---

## 9.2 环境准备

### 9.2.1 安装 Rust

```bash
curl https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env
rustc --version   # 1.70+
cargo --version
```

### 9.2.2 安装 maturin 和 PyO3 工具

```bash
pip install maturin
```

`maturin` 是 Rust→Python 的构建/打包工具（类似 pybind11 的 setup.py，但更简单）。PyO3 是绑定库（Rust crate）。

### 9.2.3 项目结构

```
myproject/
├── Cargo.toml        # Rust 项目配置
├── pyproject.toml    # Python 打包配置（maturin 用）
└── src/
    └── lib.rs        # Rust 库代码（含 PyO3 绑定）
```

---

## 9.3 第一个 PyO3 扩展

### 9.3.1 Cargo.toml

```toml
[package]
name = "fastlib"
version = "0.1.0"
edition = "2021"

[lib]
name = "fastlib"
crate-type = ["cdylib"]  # 关键：生成动态库供 Python 加载

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
```

`crate-type = ["cdylib"]` 表示生成 C 兼容的动态库。`extension-module` feature 告诉 PyO3 这是给 Python 用的扩展（不链接 libpython）。

### 9.3.2 pyproject.toml

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "fastlib"
requires-python = ">=3.8"
```

### 9.3.3 src/lib.rs

```rust
use pyo3::prelude::*;

/// 一个简单的加法函数
#[pyfunction]
fn add(a: i64, b: i64) -> i64 {
    a + b
}

/// 模块定义
#[pymodule]
fn fastlib(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add, m)?)?;
    Ok(())
}
```

代码解析：

- `#[pyfunction]`：把 Rust 函数标记为可被 Python 调用
- `#[pymodule]`：定义 Python 模块入口
- `wrap_pyfunction!(add, m)?`：把函数包装成 Python 可调用的 wrapper
- `PyResult<()>`：返回类型，Ok(()) 表示成功

### 9.3.4 构建与安装

```bash
# 开发模式：编译并装到当前虚拟环境
maturin develop

# 或构建 wheel
maturin build --release
```

`maturin develop` 会编译 Rust 代码并把生成的扩展模块安装到当前 Python 环境。

### 9.3.5 使用

```python
import fastlib
print(fastlib.add(3, 5))  # 8
print(fastlib.add.__doc__)  # 一个简单的加法函数（docstring 来自 Rust 注释）
```

**恭喜，你用 Rust 写出了第一个 Python 扩展！**

---

## 9.4 类型转换：Rust 与 Python 的数据桥梁

PyO3 自动处理很多类型转换：

| Rust 类型 | Python 类型 | 说明 |
|----------|------------|------|
| `i32`, `i64`, `u64` | `int` | 整数 |
| `f32`, `f64` | `float` | 浮点 |
| `bool` | `bool` | 布尔 |
| `String`, `&str` | `str` | 字符串 |
| `Vec<T>` | `list` | 列表 |
| `Option<T>` | `None` 或 T | 可选 |
| `HashMap<K,V>` | `dict` | 字典 |
| `(A, B)` | `tuple` | 元组 |
| `PyObject` | 任意 Python 对象 | 动态 |

### 9.4.1 基本类型示例

```rust
use pyo3::prelude::*;

#[pyfunction]
fn greet(name: &str, times: usize) -> String {
    let mut result = String::new();
    for _ in 0..times {
        result.push_str(&format!("Hello, {}!\n", name));
    }
    result
}

#[pyfunction]
fn sum_list(numbers: Vec<i64>) -> i64 {
    numbers.iter().sum()
}

#[pyfunction]
fn maybe_double(value: Option<i64>) -> Option<i64> {
    value.map(|x| x * 2)  // None → None, Some(x) → Some(2x)
}

#[pymodule]
fn fastlib(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(greet, m)?)?;
    m.add_function(wrap_pyfunction!(sum_list, m)?)?;
    m.add_function(wrap_pyfunction!(maybe_double, m)?)?;
    Ok(())
}
```

```python
import fastlib
print(fastlib.greet("Alice", 2))
print(fastlib.sum_list([1, 2, 3, 4, 5]))  # 15
print(fastlib.maybe_double(Some))  # 传 None → None
print(fastlib.maybe_double(21))    # 42
```

### 9.4.2 字符串处理的注意事项

Rust 的 `String` 是 UTF-8，Python `str` 是 Unicode。`&str` 参数接收 Python str 时会转换成 Rust 的 UTF-8 字符串（有拷贝开销）。

返回 `String` 会创建新的 Python str 对象（也有拷贝）。对性能敏感的大量字符串处理，可以考虑 `PyBytes` 或直接操作 buffer（第 10、17 章深入）。

---

## 9.5 错误处理：PyResult

### 9.5.1 返回 Result

Rust 函数可以返回 `PyResult<T>`，出错时 Python 侧收到异常：

```rust
use pyo3::exceptions::PyValueError;

#[pyfunction]
fn safe_divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyValueError::new_err("除数不能为 0"))
    } else {
        Ok(a / b)
    }
}
```

```python
import fastlib
try:
    fastlib.safe_divide(10, 0)
except ValueError as e:
    print(e)  # 除数不能为 0
```

### 9.5.2 常用异常类型

`pyo3::exceptions` 模块提供各种异常：

| Rust | Python |
|------|--------|
| `PyValueError` | `ValueError` |
| `PyTypeError` | `TypeError` |
| `PyRuntimeError` | `RuntimeError` |
| `PyKeyError` | `KeyError` |
| `PyIOError` | `IOError` |
| `PyIndexError` | `IndexError` |

### 9.5.3 `?` 运算符与错误传播

```rust
#[pyfunction]
fn read_config(path: &str) -> PyResult<String> {
    let content = std::fs::read_to_string(path)
        .map_err(|e| PyIOError::new_err(format!("读取失败: {}", e)))?;
    Ok(content)
}
```

Rust 的 `?` + `PyResult` 让错误处理既安全又简洁。相比 C API 手动设置异常，这清爽太多。

---

## 9.6 `#[pyclass]`：把 Rust 结构体暴露为 Python 类

### 9.6.1 基本类

```rust
use pyo3::prelude::*;

#[pyclass]
struct FirewallRule {
    #[pyo3(get, set)]
    ip: String,
    #[pyo3(get, set)]
    port: u16,
    #[pyo3(get, set)]
    action: String,  // "allow" 或 "deny"
}

#[pymethods]
impl FirewallRule {
    #[new]
    fn new(ip: String, port: u16, action: String) -> Self {
        FirewallRule { ip, port, action }
    }

    fn matches(&self, target_ip: &str, target_port: u16) -> bool {
        self.ip == target_ip && self.port == target_port
    }

    fn describe(&self) -> String {
        format!("{}:{} → {}", self.ip, self.port, self.action)
    }
}

#[pymodule]
fn fastlib(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<FirewallRule>()?;
    Ok(())
}
```

```python
import fastlib
rule = fastlib.FirewallRule("192.168.1.1", 22, "deny")
print(rule.describe())  # 192.168.1.1:22 → deny
print(rule.matches("192.168.1.1", 22))  # True
rule.port = 80  # 可写属性
print(rule.ip)  # 可读属性
```

### 9.6.2 类方法、静态方法、属性

```rust
#[pymethods]
impl FirewallRule {
    #[staticmethod]
    fn allow_all() -> Self {
        FirewallRule { ip: "0.0.0.0".into(), port: 0, action: "allow".into() }
    }

    #[getter]
    fn is_deny(&self) -> bool {
        self.action == "deny"
    }

    fn __repr__(&self) -> String {
        format!("<FirewallRule {}>", self.describe())
    }
}
```

### 9.6.3 类的线程安全：`Send` 和 `Sync`

Python 可能从多个线程调用同一个对象，PyO3 默认要求 `#[pyclass]` 类型是 `Send`。如果内部有可变状态，用 `Mutex` 或 `Arc<Mutex<T>>` 保护：

```rust
use std::sync::Mutex;

#[pyclass]
struct Counter {
    value: Mutex<i64>,
}

#[pymethods]
impl Counter {
    #[new]
    fn new() -> Self { Counter { value: Mutex::new(0) } }

    fn increment(&self) -> i64 {
        let mut v = self.value.lock().unwrap();
        *v += 1;
        *v
    }
}
```

这体现了 Rust 的并发安全：**编译器逼你正确处理共享可变状态**，避免数据竞争。

---

## 9.7 实战：用 PyO3 写一个高性能日志分析器

做一个安全场景的实战：分析大量日志行，提取 IP 和状态码，统计每个 IP 的请求数。这是纯 Python 处理很慢的任务。

```rust
use pyo3::prelude::*;
use std::collections::HashMap;

/// 分析日志，统计每个 IP 的请求数和错误数
/// 输入：日志行列表
/// 输出：(ip -> (总请求数, 错误数))
#[pyfunction]
fn analyze_logs(lines: Vec<String>) -> PyResult<HashMap<String, (usize, usize)>> {
    let mut stats: HashMap<String, (usize, usize)> = HashMap::new();

    for line in lines {
        // 简化解析：假设格式 "IP ... status"
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 2 { continue; }

        let ip = parts[0];
        let status: u16 = parts[parts.len()-1].parse().unwrap_or(0);

        let entry = stats.entry(ip.to_string()).or_insert((0, 0));
        entry.0 += 1;
        if status >= 400 { entry.1 += 1; }
    }

    Ok(stats)
}

#[pymodule]
fn fastlib(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(analyze_logs, m)?)?;
    Ok(())
}
```

Python 侧：

```python
import fastlib
import time

# 生成 100 万行模拟日志
lines = [f"192.168.1.{i%100} GET /page HTTP/1.1 {200 if i%10 else 404}"
         for i in range(1_000_000)]

start = time.time()
stats = fastlib.analyze_logs(lines)
print(f"Rust 处理耗时: {time.time()-start:.3f}s")

# 找出错误最多的 IP
top = sorted(stats.items(), key=lambda x: x[1][1], reverse=True)[:5]
for ip, (total, errors) in top:
    print(f"{ip}: {total} 请求, {errors} 错误")
```

Rust 处理 100 万行通常只需几十毫秒，纯 Python 可能要几秒。**这就是混合编程的价值**：Python 负责生成数据、展示结果，Rust 负责重活。

---

## 9.8 PyO3 与 pybind11 对比

| 维度 | PyO3 (Rust) | pybind11 (C++) |
|------|------------|---------------|
| 语言安全 | 编译期内存安全 | 手动内存管理（可配智能指针） |
| 学习曲线 | 陡（所有权） | 中（现代 C++） |
| 性能 | 与 C++ 相当 | 与 C 相当 |
| GIL 释放 | `py.allow_threads` | `py::gil_scoped_release` |
| 错误处理 | `PyResult` + `?` | 异常自动映射 |
| 打包 | maturin（简单） | setup.py/cmake |
| 生态案例 | tokenizers、polars、pydantic-core、ruff | PyTorch、TensorFlow、OpenCV |
| 适用 | 安全关键、高并发模块 | 已有 C++ 代码、AI 算子 |

**选择建议**：
- 已有大量 C++ 代码 → pybind11
- 从零写高性能/安全关键模块 → PyO3
- 追求内存安全（安全工具）→ PyO3

---

## 9.9 本章总结

| 知识点 | 内容 |
|--------|------|
| PyO3 定位 | Rust 写 Python 扩展，内存安全 + 高性能 |
| 环境 | Rust + maturin；Cargo.toml 用 cdylib + extension-module |
| 三大宏 | `#[pyfunction]`、`#[pymodule]`、`#[pyclass]`/`#[pymethods]` |
| 类型转换 | 整数/浮点/字符串/Vec/Option/HashMap 自动转换 |
| 错误处理 | `PyResult` + `PyValueError` 等异常类型 + `?` |
| 类 | `#[pyclass]` + `#[new]` + get/set；`Send`/`Mutex` 保证线程安全 |
| 实战 | Rust 高速日志分析器，Python 编排 |
| 对比 | vs pybind11：更安全但学习曲线陡 |

---

## 本章练习

1. 搭好 Rust + maturin 环境，编译第一个 `add` 扩展并调用。
2. 写一个函数 `count_words(s: &str) -> HashMap<String, usize>`，统计词频，从 Python 调用。
3. 用 `PyResult` 实现一个安全检查函数，输入无效时抛出 `ValueError`。
4. 用 `#[pyclass]` 定义一个 `SecurityRule` 类，包含方法、属性、`__repr__`。
5. 用 `Mutex` 实现一个线程安全的计数器类，从 Python 多线程调用验证。
6. 把实战的日志分析器扩展：支持更多日志格式、提取时间戳、按分钟聚合。
7. 对比 Rust 和纯 Python 版日志分析的性能，记录加速比。

---

**下一章预告**：PyO3 基础已经能让你写出扩展。下一章深入**数据类型互转**——字符串、列表、字典、numpy 数组、自定义类在 Rust 与 Python 之间如何高效传递，以及如何处理 Python 对象的底层操作（`PyObject`、借用、GIL）。这是写出高性能模块的关键。
