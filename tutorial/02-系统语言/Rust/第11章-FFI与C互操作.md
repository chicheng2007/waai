# 第 11 章 FFI：Rust 与 C 互操作

## 本章目标

- 理解 FFI（外部函数接口）
- 用 Rust 调用 C 函数
- 把 Rust 函数暴露给 C
- 理解 FFI 中的安全边界
- 理解 Rust 逐步替换 C 代码的策略

现实中不可能全部用 Rust 重写。FFI 让 Rust 能与 C/C++ 代码互操作——复用海量现有库，或让现有系统逐步引入 Rust。

---

## 11.1 FFI 基础

FFI（Foreign Function Interface）允许不同语言的代码互相调用。Rust 通过 `extern "C"` 声明 C 函数。

### 11.1.1 调用 C 函数

```rust
// 调用 C 标准库的 puts
extern "C" {
    fn puts(s: *const std::os::raw::c_char) -> std::os::raw::c_int;
}

use std::ffi::CString;

fn main() {
    let c_str = CString::new("Hello from Rust calling C!").unwrap();
    unsafe {
        puts(c_str.as_ptr());
    }
}
```

要点：

- `extern "C" { }` 声明外部函数
- `unsafe` 块：调用外部函数是不安全的（编译器无法验证）
- `CString`：把 Rust 字符串转成 C 字符串（带 `\0`）

### 11.1.2 数据类型映射

Rust 和 C 的类型要匹配，用 `std::os::raw` 里的类型：

| C 类型 | Rust 类型 |
|--------|----------|
| `int` | `c_int` |
| `char` | `c_char` |
| `size_t` | `size_t` |
| `void*` | `*mut c_void` / `*const c_void` |
| `char*` | `*const c_char` / `*mut c_char` |

---

## 11.2 把 Rust 函数暴露给 C

```rust
// lib.rs
use std::os::raw::{c_int, c_char};
use std::ffi::CStr;

#[no_mangle]
pub extern "C" fn add(a: c_int, b: c_int) -> c_int {
    a + b
}

#[no_mangle]
pub extern "C" fn is_valid_ip(ptr: *const c_char) -> bool {
    if ptr.is_null() { return false; }
    let c_str = unsafe { CStr::from_ptr(ptr) };
    match c_str.to_str() {
        Ok(s) => s.split('.').count() == 4,
        Err(_) => false,
    }
}
```

编译成动态库：

```toml
# Cargo.toml
[lib]
crate-type = ["cdylib"]
```

```bash
cargo build --release
# 生成 libxxx.so (Linux) / xxx.dll (Windows) / libxxx.dylib (macOS)
```

C 代码里就能调用这些函数了。

> `#[no_mangle]` 告诉编译器不要改名（mangle），保证 C 能按名字找到函数。

---

## 11.3 unsafe 的正确使用

`unsafe` 不是"坏"的，而是"程序员要保证安全"的标记。FFI 场景常见 unsafe：

```rust
unsafe {
    // 1. 解引用裸指针
    let value = *ptr;
    
    // 2. 调用 extern 函数
    c_function();
    
    // 3. 访问静态可变变量
    static_mut = 10;
}
```

**FFI 安全原则**：

1. 检查指针是否为 null
2. 确保指针指向有效内存
3. 确保数据格式正确（如字符串以 `\0` 结尾）
4. 用 RAII 管理资源，避免泄漏

> **Rust 的价值**：把 unsafe 代码隔离在最小范围（FFI 边界），核心逻辑仍用安全的 Rust 写。这样攻击面大大缩小。

---

## 11.4 渐进式替换策略

很多公司在用"Rust 逐步替换 C 模块"的策略：

```
1. 先用 Rust 写新模块
2. 通过 FFI 与现有 C 代码交互
3. 逐步替换旧的 C 模块
4. 最终核心都是安全的 Rust 代码
```

**典型案例**：

- **Linux 内核**：引入 Rust 写驱动，与 C 内核通过 FFI 交互
- **Android**：用 Rust 重写部分组件，减少内存漏洞
- **微软**：用 Rust 重写 Windows 的部分系统组件

这种策略让项目能在保持兼容的同时，逐步提升安全性。

---

## 11.5 实战：Rust 调用 C 的数学库（示例）

```rust
extern "C" {
    fn sqrt(x: f64) -> f64;  // C 标准库 math.h 的 sqrt
}

fn main() {
    let result = unsafe { sqrt(16.0) };
    println!("sqrt(16) = {}", result);   // 4
}
```

编译时需要链接数学库：

```bash
rustc main.rs -o main -lm
```

---

## 11.6 本章总结

| 知识点 | 内容 |
|--------|------|
| FFI | `extern "C"` 声明/暴露函数 |
| 类型映射 | 用 `std::os::raw` 的 c_int、c_char 等 |
| 字符串 | CString（Rust→C）、CStr（C→Rust） |
| unsafe | FFI 边界必需；检查指针、格式、资源 |
| 渐进替换 | Rust 逐步替换 C 模块的策略 |
| no_mangle | 暴露给 C 时防止改名 |

---

## 本章练习

1. 写一个 Rust 函数暴露给 C，计算两个数的最大公约数。
2. 用 Rust 调用 C 的 `strlen` 函数。
3. 思考：为什么 FFI 边界需要 unsafe？如何最小化 unsafe 代码？
4. 了解一个用 Rust 逐步替换 C 的真实项目。

---

**下一章预告**：Rust 卷收官——综合实战项目，把所有权、并发、错误处理、FFI 等知识整合成一个完整的安全工具。
