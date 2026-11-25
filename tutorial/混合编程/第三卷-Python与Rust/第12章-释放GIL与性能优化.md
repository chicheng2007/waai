# 第 12 章 释放 GIL 与性能优化

## 本章目标

读完这一章，你将能够：

- 深入理解 GIL 是什么、为什么存在、它如何限制 Python 并发
- 用 `py.allow_threads` 在 Rust 里释放 GIL，实现真并行
- 用 Rust 多线程（std::thread / rayon）进一步加速
- 掌握性能基准测试的正确方法（避免常见误区）
- 用 Rust 加速真实的 AI/安全计算任务
- 知道什么时候混合编程值得、什么时候过度设计

---

## 12.1 GIL 深入：Python 并发的枷锁

### 12.1.1 GIL 是什么

GIL（Global Interpreter Lock，全局解释器锁）是 CPython 解释器里的一把全局互斥锁。**同一时刻只有一个线程能执行 Python 字节码**。

为什么需要它？因为 CPython 的内存管理（引用计数）不是线程安全的。如果两个线程同时修改一个对象的引用计数，可能出错。GIL 是最简单的解决方案：一次只让一个线程跑 Python 代码。

### 12.1.2 GIL 的影响

- **CPU 密集型 Python 代码**：多线程无用（甚至更慢，因为线程切换开销），只能用多进程
- **I/O 密集型**：多线程有效（等待 I/O 时释放 GIL）
- **C/Rust 扩展**：调用期间可以选择释放 GIL，让多线程真正并行

### 12.1.3 一个直观实验

纯 Python CPU 密集型任务，多线程和多进程对比：

```python
import time
import threading
import multiprocessing

def cpu_work(n):
    total = 0
    for i in range(n):
        total += i * i
    return total

N = 20_000_000

# 单线程
start = time.time()
cpu_work(N)
print(f"单线程: {time.time()-start:.2f}s")

# 4 线程（受 GIL 限制，几乎不提速）
start = time.time()
threads = [threading.Thread(target=cpu_work, args=(N,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
print(f"4线程: {time.time()-start:.2f}s")

# 4 进程（真正并行）
start = time.time()
procs = [multiprocessing.Process(target=cpu_work, args=(N,)) for _ in range(4)]
for p in procs: p.start()
for p in procs: p.join()
print(f"4进程: {time.time()-start:.2f}s")
```

结果通常是：单线程 ≈ 4线程（GIL 限制），4进程 ≈ 单线程的 1/4（真并行）。

**Rust 扩展的价值**：能在扩展里释放 GIL + 用 Rust 多线程，一个 Python 线程调用就能获得多核并行，比多进程更优雅（无需进程间通信）。

---

## 12.2 用 allow_threads 释放 GIL

### 12.2.1 基本用法

```rust
use pyo3::prelude::*;

#[pyfunction]
fn sum_squares(n: u64) -> u64 {
    pyo3::Python::with_gil(|py| {
        py.allow_threads(|| {
            // 这里 GIL 已释放，纯 Rust 计算，不能碰 Python 对象
            (0..n).map(|i| i * i).sum()
        })
    })
}
```

`py.allow_threads(closure)`：
1. 释放 GIL
2. 执行 closure（纯 Rust）
3. 重新获取 GIL
4. 返回结果

**规则（必须记住）**：

> `allow_threads` 的闭包里**绝对不能**访问任何 Python 对象、调用任何 Python API、操作 `PyAny`/`PyObject`。否则会崩溃（因为其他线程可能正在改这些对象）。编译器不会阻止你（closure 是 `Send` 约束但不检查 Python 对象），靠自觉。

### 12.2.2 释放 GIL 的时机判断

| 场景 | 是否释放 |
|------|---------|
| 纯数值计算（无 Python 对象） | ✅ 释放 |
| 文件 I/O、网络请求（C/Rust 层面） | ✅ 释放 |
| 需要调用 Python 函数/访问对象 | ❌ 不释放 |
| 计算很快（微秒级） | 可不释放（释放本身有开销） |
| 长时间运行（毫秒级以上） | ✅ 释放 |

---

## 12.3 Rust 多线程加速

释放 GIL 后，Rust 内部可以用多线程进一步加速。

### 12.3.1 std::thread

```rust
use pyo3::prelude::*;
use std::thread;

#[pyfunction]
fn parallel_sum_squares(n: u64, threads: usize) -> u64 {
    pyo3::Python::with_gil(|py| {
        py.allow_threads(|| {
            let chunk = n / threads as u64;
            let mut handles = Vec::new();

            for t in 0..threads {
                let start = t as u64 * chunk;
                let end = if t == threads - 1 { n } else { start + chunk };
                handles.push(thread::spawn(move || {
                    (start..end).map(|i| i * i).sum::<u64>()
                }));
            }

            handles.into_iter().map(|h| h.join().unwrap()).sum()
        })
    })
}
```

Python 调用：

```python
import fastlib
print(fastlib.parallel_sum_squares(100_000_000, 8))
```

一个 Python 调用，Rust 内部 8 线程并行，**真正利用多核**。

### 12.3.2 rayon：并行迭代器（推荐）

手写线程管理繁琐，`rayon` crate 提供并行迭代器：

Cargo.toml：

```toml
[dependencies]
rayon = "1.8"
```

代码：

```rust
use rayon::prelude::*;

#[pyfunction]
fn parallel_sum_squares_rayon(n: u64) -> u64 {
    pyo3::Python::with_gil(|py| {
        py.allow_threads(|| {
            (0..n).into_par_iter().map(|i| i * i).sum()
        })
    })
}
```

`into_par_iter()` 自动把迭代并行化，rayon 管理线程池。**代码几乎和串行版一样简单**。

### 12.3.3 何时多线程不划算

- 任务太小：线程创建/调度开销 > 计算收益
- 任务本身是 I/O 密集且已有异步
- 内存带宽瓶颈：多线程同时访问大数组可能受限于内存带宽而非 CPU

**测量，不要猜测**（下一节讲基准测试）。

---

## 12.4 性能基准测试：正确的方法

### 12.4.1 Python 侧基准：timeit

```python
import timeit
import fastlib

# 正确：多次运行取平均
time = timeit.timeit(lambda: fastlib.sum_squares(1_000_000), number=100)
print(f"平均: {time/100*1000:.2f} ms")
```

### 12.4.2 更严谨：pytest-benchmark

```bash
pip install pytest-benchmark
```

```python
def test_benchmark(benchmark):
    result = benchmark(fastlib.sum_squares, 1_000_000)
    assert result > 0
```

### 12.4.3 基准测试常见误区

| 误区 | 问题 | 正确做法 |
|------|------|---------|
| 只跑一次 | 波动大，受缓存/调度影响 | 多次运行取统计（mean/median） |
| 不预热 | 首次调用有初始化开销 | 先跑几次预热再计时 |
| 计时包含数据生成 | 测的不是目标函数 | 数据准备好再计时 |
| 对比不同输入 | 不公平 | 相同输入对比 |
| 忽略拷贝开销 | 只算计算不算转换 | 算上边界转换的总时间 |

### 12.4.4 测量边界开销

```python
import timeit
import numpy as np
import fastlib

arr = np.random.rand(1_000_000).astype(np.float64)

# 纯 Rust 计算（假设 array_sum 接收 numpy）
t1 = timeit.timeit(lambda: fastlib.array_sum(arr), number=100)

# 如果只是 Python 版（对比）
t2 = timeit.timeit(lambda: arr.sum(), number=100)

print(f"Rust: {t1/100*1000:.3f} ms, numpy: {t2/100*1000:.3f} ms")
```

**注意**：numpy 本身底层就是 C，对于简单求和，numpy 可能已经很快。Rust 的优势在于**复杂自定义计算**（numpy 没有现成函数的情况）。

---

## 12.5 实战：用 Rust 加速 AI 相似度计算

AI 应用中常需要计算大量向量间的余弦相似度（如推荐系统、RAG 检索）。纯 Python 循环慢，numpy 会创建临时数组。用 Rust 可以高效批量计算。

### 12.5.1 Rust 实现

```rust
use pyo3::prelude::*;
use rayon::prelude::*;

/// 计算查询向量与一组向量的余弦相似度
/// query: 查询向量
/// vectors: 候选向量列表（展平的一维数组）
/// dim: 向量维度
#[pyfunction]
fn batch_cosine_similarity(query: Vec<f32>, vectors: Vec<f32>, dim: usize) -> Vec<f32> {
    pyo3::Python::with_gil(|py| {
        py.allow_threads(|| {
            let q_norm: f32 = query.iter().map(|x| x * x).sum::<f32>().sqrt();

            vectors
                .chunks(dim)
                .into_par_iter()  // rayon 并行
                .map(|v| {
                    let mut dot = 0.0f32;
                    let mut norm = 0.0f32;
                    for i in 0..dim {
                        dot += query[i] * v[i];
                        norm += v[i] * v[i];
                    }
                    if q_norm > 0.0 && norm > 0.0 {
                        dot / (q_norm * norm.sqrt())
                    } else {
                        0.0
                    }
                })
                .collect()
        })
    })
}
```

### 12.5.2 Python 侧使用与验证

```python
import numpy as np
import fastlib
import timeit

dim = 768  # 典型 embedding 维度
n = 10_000  # 1 万个候选向量

query = np.random.randn(dim).astype(np.float32)
vectors = np.random.randn(n, dim).astype(np.float32)

# Rust 版（展平传入）
flat = vectors.flatten().tolist()  # 注意：这里 tolist 有拷贝开销！
start = timeit.timeit(
    lambda: fastlib.batch_cosine_similarity(query.tolist(), flat, dim),
    number=10
)
print(f"Rust (含转换): {start/10:.3f}s")

# numpy 版（向量化）
def numpy_cosine():
    q_norm = np.linalg.norm(query)
    v_norm = np.linalg.norm(vectors, axis=1)
    return (vectors @ query) / (v_norm * q_norm)

start = timeit.timeit(numpy_cosine, number=10)
print(f"numpy: {start/10:.3f}s")
```

**重要观察**：这个例子里 `tolist()` 的拷贝开销可能让 Rust 版不占优。要真正发挥 Rust 性能，应该用 numpy crate 的零拷贝接口（第 10 章）接收 numpy 数组，避免转换。

### 12.5.3 改进：零拷贝版本

```rust
use numpy::{PyReadonlyArray1, PyReadonlyArray2, PyArray1, ToPyArray};
use pyo3::prelude::*;
use rayon::prelude::*;

#[pyfunction]
fn fast_cosine<'py>(
    py: Python<'py>,
    query: PyReadonlyArray1<f32>,
    vectors: PyReadonlyArray2<f32>,
) -> PyResult<&'py PyArray1<f32>> {
    let q = query.as_slice()?;
    let v = vectors.as_array();  // ndarray 视图，零拷贝
    let (n, dim) = (v.nrows(), v.ncols());

    let q_norm: f32 = q.iter().map(|x| x * x).sum::<f32>().sqrt();

    let result: Vec<f32> = py.allow_threads(|| {
        (0..n).into_par_iter().map(|i| {
            let mut dot = 0.0f32;
            let mut norm = 0.0f32;
            for j in 0..dim {
                let val = v[[i, j]];
                dot += q[j] * val;
                norm += val * val;
            }
            if q_norm > 0.0 && norm > 0.0 { dot / (q_norm * norm.sqrt()) } else { 0.0 }
        }).collect()
    });

    Ok(result.to_pyarray(py))
}
```

零拷贝 + 并行，这才是 Rust 的正确用法。对于 numpy 没有的**自定义复杂计算**，这个方案能显著提速。

---

## 12.6 实战：用 Rust 加速安全规则匹配

安全场景中常需要对大量事件做规则匹配（如检测可疑 IP、恶意域名）。Rust 的并行 + 高效字符串处理很适合。

```rust
use pyo3::prelude::*;
use rayon::prelude::*;
use std::collections::HashSet;

/// 批量检查 IP 是否在黑名单中
/// events: (ip, status) 列表
/// blacklist: 黑名单 IP 集合
/// 返回：可疑事件索引列表
#[pyfunction]
fn detect_suspicious(events: Vec<(String, u16)>, blacklist: Vec<String>) -> Vec<usize> {
    let black: HashSet<&str> = blacklist.iter().map(|s| s.as_str()).collect();

    pyo3::Python::with_gil(|py| {
        py.allow_threads(|| {
            events
                .par_iter()
                .enumerate()
                .filter_map(|(idx, (ip, status))| {
                    if black.contains(ip.as_str()) || *status >= 500 {
                        Some(idx)
                    } else {
                        None
                    }
                })
                .collect()
        })
    })
}
```

Python：

```python
import fastlib

events = [("192.168.1.1", 200), ("10.0.0.5", 404), ("8.8.8.8", 503)]
blacklist = ["10.0.0.5", "1.1.1.1"]
suspicious = fastlib.detect_suspicious(events, blacklist)
print(suspicious)  # [1, 2]
```

HashSet 的 O(1) 查找 + rayon 并行，处理百万级事件很快。

---

## 12.7 性能优化 checklist

优化混合程序时，按这个顺序检查：

1. **真的需要优化吗？** 先测量，确认瓶颈
2. **边界转换是不是瓶颈？** 用 zero-copy（numpy buffer）避免拷贝
3. **批量化了吗？** 一次调用处理一批，别在循环里调用
4. **释放 GIL 了吗？** 长时间纯计算用 `allow_threads`
5. **用并行了吗？** rayon 并行迭代
6. **算法本身高效吗？** 数据结构选择（HashSet vs Vec）、避免重复计算
7. **编译器优化开了吗？** `maturin build --release`（`-O3`）

---

## 12.8 什么时候不该用混合编程

混合编程有成本：构建复杂、部署麻烦、调试困难、团队技能要求高。以下情况**不建议**：

- 性能不是瓶颈（先测量！）
- 项目很小、生命周期短
- 团队没有 Rust/C++ 能力
- 需要频繁迭代业务逻辑（编译慢拖慢开发）
- 纯 I/O 密集型任务（Python 异步已够好）

**记住**：混合编程是工具，不是信仰。用它解决真实问题，而不是为了炫技。

---

## 12.9 编译优化选项速查

释放 GIL 和并行化之外，编译选项也直接影响性能。用 maturin 时，这些选项值得了解。

### 12.9.1 release 模式

```bash
# 开发模式（默认 debug，优化低，编译快）
maturin develop

# release 模式（优化全开，运行快，编译慢）—— 发布必须
maturin develop --release
```

debug 和 release 的性能可能差 10 倍以上。**性能测试一定要用 release 模式**，否则测出来的是未优化版本。

### 12.9.2 Cargo.toml 优化配置

```toml
[profile.release]
opt-level = 3          # 优化级别 3（最大优化）
lto = true             # 链接时优化，跨 crate 内联
codegen-units = 1      # 单一代码生成单元，更充分优化（编译更慢）
panic = "abort"        # panic 时直接中止，减小体积（扩展里慎用）
```

`lto = true` 和 `codegen-units = 1` 能让射线式优化更彻底，通常有 5-15% 的提升，但编译时间增加。发布时对性能敏感的库值得开启。

### 12.9.3 针对 CPU 架构优化

```bash
# 在当前机器上生成针对本机 CPU 的优化代码（用 AVX 等指令集）
RUSTFLAGS="-C target-cpu=native" maturin develop --release
```

`target-cpu=native` 会让编译器使用本机支持的最新指令集（如 AVX2/AVX-512）。**注意**：这样编译出的 wheel 只能在同代或更新的 CPU 上运行，发布通用 wheel 时不要用（用通用 target）。内部部署（知道自己机器的 CPU）可以用。

### 12.9.4 基准测试的正确姿势

```bash
# 1. release 编译
maturin develop --release

# 2. 用 criterion 做 Rust 内部基准（比 timeit 更严谨）
# Cargo.toml: [dev-dependencies] criterion = "0.5"
cargo bench

# 3. Python 侧用 timeit/pytest-benchmark 测端到端（含边界）
```

Rust 内部基准（criterion）测纯算法，Python 基准测端到端（含转换开销）。两者结合才能看清全貌：如果 criterion 很快但 Python 测出来慢，说明瓶颈在边界转换而非算法。

---

## 12.10 本章总结

| 知识点 | 内容 |
|--------|------|
| GIL | CPython 一次只让一个线程执行字节码；限制 CPU 密集多线程 |
| allow_threads | 释放 GIL 做纯 Rust 计算；闭包内不能碰 Python 对象 |
| Rust 多线程 | std::thread 手写；rayon 并行迭代器（推荐） |
| 基准测试 | timeit/pytest-benchmark；多次运行、预热、相同输入、算上转换 |
| AI 实战 | 批量余弦相似度，零拷贝 numpy + rayon 并行 |
| 安全实战 | HashSet 黑名单 + 并行事件检测 |
| 优化 checklist | 测量→零拷贝→批量→释放GIL→并行→算法→release 编译 |
| 何时不用 | 性能非瓶颈、小项目、团队无能力、纯 I/O 密集 |

---

## 本章练习

1. 用纯 Python 多线程和 Rust 扩展（释放 GIL）做同一个 CPU 密集任务，对比加速。
2. 写一个 `parallel_sum` 用 rayon，测量不同线程数的加速曲线。
3. 用 timeit 正确测量一个 Rust 函数的性能（预热+多次+统计）。
4. 把 AI 相似度例子改成零拷贝版本，对比含 `tolist()` 拷贝的版本。
5. 扩展安全规则匹配：支持正则规则、多条件组合。
6. 思考：什么情况下释放 GIL 反而更慢？（提示：闭包开销、任务太小）

---

**下一章预告**：第三卷（Python+Rust）圆满完成。进入第四卷——**Python 与 Go**。从 cgo 开始：Go 与 C 的互操作桥梁，理解 Go 调用 C 和 C 调用 Go 的规则与内存约束，为后面用 Go 给 Python 做高性能网络模块打基础。
