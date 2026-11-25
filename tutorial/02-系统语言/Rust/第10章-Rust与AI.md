# 第 10 章 Rust 与 AI：高性能推理

## 本章目标

- 了解 Rust 的 AI 生态（candle、linfa 等）
- 理解 Rust 在大模型推理中的优势
- 用 Rust 调用简单的 ML 功能
- 理解向量数据库与 RAG

Rust 在 AI 领域主要不是做训练（训练还是 Python 的天下），而是做**推理部署、高性能服务、AI 基础设施**——这些场景需要性能、并发、内存安全。

---

## 10.1 Rust AI 生态

| 库 | 用途 |
|----|------|
| **candle** | Hugging Face 出品的深度学习框架，支持大模型推理 |
| **linfa** | 传统机器学习（类似 scikit-learn） |
| **ndarray** | N 维数组（类似 NumPy） |
| **burn** | 深度学习框架 |
| **tch-rs** | PyTorch 的 Rust 绑定 |
| **qdrant-client** | 向量数据库客户端 |

---

## 10.2 ndarray：Rust 的 NumPy

```rust
// Cargo.toml: ndarray = "0.15"
use ndarray::{Array2, Array1};

fn main() {
    // 创建矩阵
    let a = Array2::<f64>::zeros((2, 3));
    let b = array![[1.0, 2.0], [3.0, 4.0]];
    
    // 矩阵乘法
    let c = b.dot(&b);
    println!("{:?}", c);
    
    // 数组运算
    let v = Array1::from_vec(vec![1.0, 2.0, 3.0]);
    let sum = v.sum();
    let mean = v.mean();
}
```

---

## 10.3 用 candle 做大模型推理（概念示例）

```rust
// Cargo.toml:
// candle-core = "0.3"
// candle-transformers = "0.3"

use candle_core::{Device, Tensor};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let device = Device::Cpu;  // 或 Device::Cuda(0)
    
    // 创建张量
    let a = Tensor::new(&[1f32, 2.0, 3.0], &device)?;
    let b = Tensor::new(&[4f32, 5.0, 6.0], &device)?;
    
    // 运算
    let c = a.add(&b)?;
    println!("{:?}", c.to_vec::<f32>()?);   // [5, 7, 9]
    
    Ok(())
}
```

> **candle 的优势**：纯 Rust 实现，无 Python 依赖，能编译成单个二进制文件，部署极其方便。适合在边缘设备、服务器里嵌入大模型推理。

---

## 10.4 向量数据库与 RAG

向量数据库是大模型 RAG（检索增强生成）的核心基础设施。Rust 写的向量数据库性能优异：

- **Qdrant**：用 Rust 写的向量搜索引擎，高性能
- **Weaviate**：部分 Go，但生态支持 Rust

RAG 流程回顾（第 25 章学过）：

```
文档 → 向量化 → 存入向量库 → 查询时检索相似向量 → 给 LLM 生成答案
```

Rust 适合做 RAG 系统里的**高性能检索服务**部分。

---

## 10.5 为什么用 Rust 做 AI 服务

| 场景 | Rust 优势 |
|------|----------|
| 推理服务 API | 高并发、低延迟、无 GC 停顿 |
| 边缘设备推理 | 单二进制、依赖少、资源占用低 |
| 向量检索 | 性能接近 C++，内存安全 |
| 模型网关/代理 | 高并发、稳定 |

> **对比 Python**：Python 做 AI 服务部署复杂（要装 Python 环境、一堆依赖），Rust 编译成单个可执行文件，部署到任何机器都很简单。

---

## 10.6 本章总结

| 知识点 | 内容 |
|--------|------|
| AI 生态 | candle、linfa、ndarray、burn |
| ndarray | Rust 的 NumPy |
| candle | 大模型推理，纯 Rust，易部署 |
| 向量数据库 | Qdrant；RAG 基础设施 |
| 优势 | 高并发、低延迟、单二进制部署 |

---

## 本章练习

1. 用 ndarray 实现矩阵乘法。
2. 用 candle 加载一个简单的模型做推理。
3. 思考：为什么 AI 推理服务适合用 Rust？
4. 了解 Qdrant，尝试用 Rust 客户端做向量检索。
5. 对比 Rust 和 Python 做 AI 服务的优劣。

---

**下一章预告**：学习 FFI（外部函数接口）——Rust 与 C 互操作，让 Rust 能复用 C/C++ 的海量库，也能被其他语言调用。
