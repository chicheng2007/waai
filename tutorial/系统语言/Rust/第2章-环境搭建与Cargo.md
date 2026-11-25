# 第 2 章 环境搭建与 Cargo

## 本章目标

- 安装 Rust 工具链
- 理解 Cargo（包管理与构建工具）
- 创建并运行第一个 Rust 项目
- 理解 cargo 的常用命令

---

## 2.1 安装 Rust

### 2.1.1 使用 rustup（官方推荐）

**Linux / macOS**：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Windows**：

下载 <https://rustup.rs/> 的安装程序，双击安装。

安装完成后验证：

```bash
rustc --version
cargo --version
```

rustup 管理多个 Rust 版本（stable、beta、nightly），可以用 `rustup update` 更新。

---

## 2.2 Cargo：Rust 的项目管理神器

Cargo 是 Rust 的构建系统和包管理器，类似于 Python 的 pip + virtualenv + setuptools 的结合体，但更强大。

### 2.2.1 创建项目

```bash
cargo new hello_rust
cd hello_rust
```

生成的结构：

```
hello_rust/
├── Cargo.toml        # 项目配置（依赖、元信息）
└── src/
    └── main.rs       # 源代码
```

### 2.2.2 Cargo.toml

```toml
[package]
name = "hello_rust"
version = "0.1.0"
edition = "2021"

[dependencies]
# 在这里添加依赖，如：
# rand = "0.8"
```

### 2.2.3 第一个程序

`src/main.rs`：

```rust
fn main() {
    println!("Hello, Rust!");
}
```

运行：

```bash
cargo run
```

编译但不运行：

```bash
cargo build
```

### 2.2.4 常用 Cargo 命令

```bash
cargo new <name>        # 创建新项目
cargo build             # 编译（调试版）
cargo build --release   # 编译（发布版，优化）
cargo run               # 编译并运行
cargo check             # 快速检查能否编译（不生成可执行文件）
cargo test              # 运行测试
cargo add <crate>       # 添加依赖（需要 cargo-edit）
cargo update            # 更新依赖
cargo doc --open        # 生成并打开文档
```

> **效率技巧**：写代码时经常用 `cargo check`，它比 `cargo build` 快，能快速发现编译错误。

---

## 2.3 crates.io：Rust 的包仓库

crates.io 是 Rust 的官方包仓库（类似 PyPI）。添加依赖：

```toml
[dependencies]
rand = "0.8"       # 随机数
serde = "1.0"      # 序列化
serde_json = "1.0" # JSON
tokio = "1"        # 异步运行时
```

Cargo 会自动下载依赖并编译。版本约束遵循语义化版本（SemVer）。

---

## 2.4 与 Python 的对比

| 操作 | Python | Rust |
|------|--------|------|
| 创建项目 | 手动建文件夹 | `cargo new` |
| 安装依赖 | `pip install` | 写入 Cargo.toml + `cargo build` |
| 运行环境 | `python main.py` | `cargo run` |
| 依赖锁定 | requirements.txt | Cargo.lock（自动生成） |
| 测试 | pytest | `cargo test`（内置） |

Rust 的工具链高度集成，开箱即用，这是它相比 C/C++ 的一大优势（C/C++ 的构建工具五花八门，配置复杂）。

---

## 2.5 编译模式

```bash
# 调试版（默认）：编译快，包含调试信息，运行慢
cargo build

# 发布版：编译慢，高度优化，运行快
cargo build --release
```

发布版可执行文件在 `target/release/` 目录，调试版在 `target/debug/`。

> **性能对比**：发布版通常比调试版快 10-100 倍。基准测试一定要用 release 版。

---

## 2.6 本章总结

| 知识点 | 内容 |
|--------|------|
| 安装 | rustup（官方工具链管理器） |
| Cargo | 构建系统 + 包管理器；`cargo new/build/run/check/test` |
| Cargo.toml | 项目配置和依赖声明 |
| crates.io | Rust 包仓库 |
| 编译模式 | debug（快编译）vs release（快运行） |

---

## 本章练习

1. 安装 Rust，创建第一个项目并运行。
2. 添加一个依赖（如 rand），在代码中使用它。
3. 用 `cargo check` 和 `cargo build` 对比速度。
4. 写一个简单的单元测试，用 `cargo test` 运行。
5. 编译 release 版，对比运行速度。

---

**下一章预告**：学习 Rust 基础语法——变量、数据类型、函数、控制流。Rust 的语法和 C/Python 有相似之处，但也有独特之处。
