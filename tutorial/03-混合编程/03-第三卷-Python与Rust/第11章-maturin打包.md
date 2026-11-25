# 第 11 章 maturin 打包：从 Rust 代码到 pip 可装的库

## 本章目标

读完这一章，你将能够：

- 理解 maturin 在 Rust→Python 生态中的角色
- 用 maturin develop 做开发调试，用 maturin build 构建 wheel
- 理解 pyproject.toml 与 Cargo.toml 的配合
- 构建纯 Rust wheel 和 mixed Rust/Python 项目
- 处理跨平台编译（Linux/macOS/Windows）
- 把包发布到 PyPI，让别人能 `pip install` 你的 Rust 扩展
- 理解 ABI3 / abi3 稳定 ABI 的价值

---

## 11.1 为什么需要 maturin

写好了 PyO3 扩展，怎么让别人用上？

- 直接发 `.so` 文件？不专业，无法 pip 安装，版本管理混乱
- 用 setuptools？它不懂 Rust，需要复杂的自定义 build 命令

**maturin** 就是专门为 Rust→Python 打造的构建/打包工具：

- 理解 Cargo 项目，自动编译 Rust 代码
- 生成标准 Python wheel（`.whl`）
- 支持开发模式、跨平台、PyPI 发布
- 一条命令完成编译+打包

它是 HuggingFace tokenizers、polars、pydantic-core 等项目背后的打包工具。

---

## 11.2 项目结构与配置

### 11.2.1 标准项目结构

```
fastlib/
├── Cargo.toml
├── pyproject.toml
├── README.md
├── src/
│   └── lib.rs          # Rust 扩展代码
├── python/
│   └── fastlib/
│       └── __init__.py  # （可选）纯 Python 包装层
└── tests/
    └── test_basic.py
```

### 11.2.2 Cargo.toml

```toml
[package]
name = "fastlib"
version = "0.1.0"
edition = "2021"
description = "高性能安全分析库"

[lib]
name = "fastlib"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
```

### 11.2.3 pyproject.toml

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "fastlib"
version = "0.1.0"
description = "高性能安全分析库"
requires-python = ">=3.8"
classifiers = [
    "Programming Language :: Rust",
    "Programming Language :: Python :: Implementation :: CPython",
]

[tool.maturin]
# 模块名（默认和 crate 名一致）
module-name = "fastlib"
```

**关键点**：`build-backend = "maturin"` 告诉 pip 用 maturin 构建。这样别人 `pip install .` 也能工作。

---

## 11.3 开发工作流

### 11.3.1 maturin develop：快速迭代

```bash
# 先创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 开发模式：编译 + 安装到当前环境
maturin develop

# 带优化的构建（更快运行，但编译慢）
maturin develop --release
```

`maturin develop` 把编译好的扩展模块直接放进虚拟环境的 site-packages，改完 Rust 代码重新执行即可。

### 11.3.2 maturin build：构建 wheel

```bash
# 构建 wheel（输出到 target/wheels/）
maturin build --release

# 输出示例：
# 📦 Built wheel for CPython 3.11 to target/wheels/fastlib-0.1.0-cp311-cp311-linux_x86_64.whl
```

wheel 文件名包含：
- `fastlib-0.1.0`：包名+版本
- `cp311`：Python 版本
- `linux_x86_64`：平台

### 11.3.3 安装 wheel

```bash
pip install target/wheels/fastlib-0.1.0-*.whl
```

---

## 11.4 两种项目布局

### 11.4.1 纯 Rust 项目

所有代码在 Rust 里，`#[pymodule]` 直接定义模块：

```
src/lib.rs   →  import fastlib
```

适合：库本身就是 Rust 实现，Python 只是接口。

### 11.4.2 Mixed 项目（Rust + Python 包装层）

Rust 提供核心模块，Python 提供友好的包装：

```
src/lib.rs              →  编译成 fastlib._core
python/fastlib/__init__.py →  import fastlib._core 并封装
```

pyproject.toml 里指定：

```toml
[tool.maturin]
module-name = "fastlib._core"
python-source = "python"
```

`python/fastlib/__init__.py`：

```python
from ._core import add, analyze_logs

# 可以在 Python 层添加更友好的接口
def quick_analyze(lines):
    """带默认参数的便捷接口"""
    return analyze_logs(list(lines))

__all__ = ["add", "analyze_logs", "quick_analyze"]
```

**Mixed 布局的价值**：性能核心用 Rust，API 设计、文档、参数校验用 Python（更灵活）。HuggingFace tokenizers 就是这种布局。

---

## 11.5 ABI3：一个 wheel 通吃多个 Python 版本

### 11.5.1 问题

默认情况下，为 Python 3.11 编的 wheel 只能在 3.11 上用。用户用 3.10？抱歉，重新编译。

### 11.5.2 解决：abi3（稳定 ABI）

Python 提供「稳定 ABI」，跨版本兼容。PyO3 支持 abi3：

Cargo.toml：

```toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module", "abi3-py38"] }
```

`abi3-py38` 表示兼容 Python 3.8+。maturin 会自动生成 abi3 wheel：

```bash
$ maturin build --release
# 📦 fastlib-0.1.0-abi3-linux_x86_64.whl
```

文件名里的 `abi3` 表示这个 wheel 能在所有 3.8+ 版本上使用。**发布库时强烈推荐 abi3**，大大减少维护多个 wheel 的负担。

> **注意**：abi3 只能用稳定 ABI 的 API，某些新版本特性不能用。权衡：兼容性 vs 功能。

---

## 11.6 跨平台编译

### 11.6.1 各平台本地构建

```bash
# Linux：直接
maturin build --release

# macOS：直接（注意架构）
maturin build --release  # 当前架构（arm64 或 x86_64）
maturin build --release --target x86_64-apple-darwin  # 交叉到 Intel

# Windows：在 MSVC 环境里
maturin build --release
```

### 11.6.2 用 GitHub Actions 自动构建多平台 wheel

大型项目用 CI 自动为每个平台构建 wheel：

```yaml
# .github/workflows/build.yml
name: Build wheels
on: [push, release]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install maturin
        run: pip install maturin
      - name: Build wheel
        run: maturin build --release
      - uses: actions/upload-artifact@v3
        with:
          name: wheels-${{ matrix.os }}
          path: target/wheels/*.whl
```

这样 push 代码后自动生成 Linux/macOS/Windows 三个平台的 wheel。

### 11.6.3 manylinux：Linux wheel 的兼容性

Linux 发行版众多（glibc 版本不同），wheel 要兼容老系统需遵循 manylinux 标准：

```bash
# 用 maturin 的 docker 支持构建 manylinux wheel
docker run --rm -v $(pwd):/io quay.io/pypa/manylinux2014_x86_64 \
    /io/build.sh
```

或使用 `maturin build --manylinux 2014`（需要对应环境）。

> **小白问：为什么不直接发源码让用户自己编译？**
> 因为用户可能没装 Rust、编译环境复杂。**wheel 是预编译的，pip install 秒装**。这就是打包的意义——把编译负担从用户转移到开发者。

---

## 11.7 发布到 PyPI

### 11.7.1 准备

```bash
pip install twine
```

### 11.7.2 构建所有 wheel

```bash
maturin build --release --out dist
```

### 11.7.3 上传到测试 PyPI

```bash
twine upload --repository testpypi dist/*
```

测试安装：

```bash
pip install --index-url https://test.pypi.org/simple/ fastlib
```

### 11.7.4 上传到正式 PyPI

```bash
twine upload dist/*
```

需要 PyPI 账号和 API token（在 PyPI 设置里生成，用 `TWINE_PASSWORD` 环境变量传入，别硬编码）。

### 11.7.5 版本管理

每次发布要更新版本号（Cargo.toml 和 pyproject.toml 保持一致）。语义化版本：

- `0.1.0` → `0.1.1`：修 bug
- `0.1.0` → `0.2.0`：加功能（向后兼容）
- `0.x` → `1.0.0`：正式版

---

## 11.8 测试与 CI

### 11.8.1 写测试

```python
# tests/test_basic.py
import fastlib

def test_add():
    assert fastlib.add(3, 5) == 8

def test_analyze():
    lines = ["1.2.3.4 GET / 200", "1.2.3.4 GET / 404"]
    stats = fastlib.analyze_logs(lines)
    assert stats["1.2.3.4"] == (2, 1)
```

```bash
pytest tests/
```

### 11.8.2 CI 里跑测试

在 GitHub Actions 里加：

```yaml
- name: Install and test
  run: |
    maturin develop
    pip install pytest
    pytest tests/
```

确保每次修改后测试通过。

---

## 11.9 实战：打包一个完整的 Rust 安全库

综合前面的知识，打包一个完整项目 `seckit`：

```
seckit/
├── Cargo.toml           # cdylib + pyo3 abi3-py38
├── pyproject.toml       # maturin backend, module-name = "seckit._core"
├── README.md
├── src/
│   └── lib.rs           # Rust 核心：哈希计算、熵分析、端口检查
├── python/
│   └── seckit/
│       ├── __init__.py  # 友好接口
│       └── cli.py       # 命令行工具
└── tests/
    └── test_seckit.py
```

Python 包装层提供友好 API：

```python
# python/seckit/__init__.py
from ._core import calculate_entropy, shannon_entropy
import base64

def analyze_file(path: str) -> dict:
    """分析文件的熵和哈希（友好接口）"""
    with open(path, "rb") as f:
        data = f.read()
    return {
        "size": len(data),
        "entropy": calculate_entropy(data),
        "base64": base64.b64encode(data[:32]).decode(),
    }
```

构建与安装：

```bash
maturin develop --release
python -c "import seckit; print(seckit.analyze_file('test.bin'))"
```

打包发布：

```bash
maturin build --release --out dist
twine upload dist/*
```

---

## 11.10 本章总结

| 知识点 | 内容 |
|--------|------|
| maturin | Rust→Python 打包工具，生成标准 wheel |
| 配置 | Cargo.toml（cdylib + pyo3）+ pyproject.toml（maturin backend） |
| 开发 | `maturin develop` 开发模式；`maturin build --release` 构建 wheel |
| 项目布局 | 纯 Rust，或 Mixed（Rust 核心 + Python 包装层） |
| abi3 | 一个 wheel 兼容多个 Python 版本，强烈推荐发布时用 |
| 跨平台 | 各平台本地构建 + GitHub Actions 自动多平台；manylinux |
| 发布 | twine upload 到 PyPI；先测 testpypi |
| 测试 | pytest + CI 保证质量 |

---

## 本章练习

1. 用 maturin develop 把之前的 Rust 扩展装进虚拟环境并调用。
2. 用 maturin build 构建 wheel，检查文件名包含的信息。
3. 改造成 Mixed 布局：加一层 Python 包装，提供友好接口。
4. 启用 abi3-py38，构建 wheel，确认名字里有 abi3。
5. 写 pytest 测试，覆盖 Rust 扩展的主要函数。
6. （可选）配置 GitHub Actions，自动构建多平台 wheel。
7. 上传到 testpypi，再从 testpypi 安装验证。

---

**下一章预告**：Rust 扩展已经能打包发布了。下一章学习 **释放 GIL 与性能优化**——这是 Rust 相比 CPython 的核心优势：真正的多线程并行、性能基准测试方法、如何用 Rust 突破 Python 的性能天花板。这是 AI 算子加速的关键。
