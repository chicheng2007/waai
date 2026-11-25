# 第 12 章 Rust 安全生态与实战项目

## 本章目标

- 了解 Rust 安全生态
- 完成一个综合实战项目
- 总结 Rust 卷的核心知识
- 规划后续学习方向

---

## 12.1 Rust 安全生态

### 12.1.1 安全相关 crate

| crate | 用途 |
|-------|------|
| `sha2` / `md-5` | 哈希计算 |
| `aes` / `rsa` | 加密（RustCrypto 项目） |
| `ring` | 高性能加密库 |
| `reqwest` | HTTP 客户端 |
| `tokio` | 异步运行时 |
| `clap` | 命令行参数解析 |
| `serde` / `serde_json` | 序列化 |
| `regex` | 正则表达式 |
| `pcap` | 抓包 |

### 12.1.2 安全工具项目

- **feroxbuster**：用 Rust 写的 Web 内容发现工具（类似 dirbuster，但更快）
- **rustscan**：快速端口扫描器
- **ligolo-ng**：隧道工具
- **RustCrypto**：纯 Rust 的密码学库集合

---

## 12.2 综合实战：并发日志分析器

```rust
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};
use std::thread;
use std::fs;

#[derive(Debug)]
struct LogEntry {
    ip: String,
    event: String,
}

fn parse_log(content: &str) -> Vec<LogEntry> {
    content.lines()
        .filter_map(|line| {
            let parts: Vec<&str> = line.split('|').collect();
            if parts.len() >= 2 {
                Some(LogEntry {
                    ip: parts[0].trim().to_string(),
                    event: parts[1].trim().to_string(),
                })
            } else {
                None
            }
        })
        .collect()
}

fn analyze(logs: &[LogEntry], threshold: usize) -> (HashMap<String, usize>, HashSet<String>) {
    let mut fails: HashMap<String, usize> = HashMap::new();
    let mut ips: HashSet<String> = HashSet::new();
    
    for log in logs {
        if log.event == "LOGIN_FAIL" {
            *fails.entry(log.ip.clone()).or_insert(0) += 1;
            ips.insert(log.ip.clone());
        }
    }
    
    let suspects: HashSet<String> = fails.iter()
        .filter(|(_, &count)| count >= threshold)
        .map(|(ip, _)| ip.clone())
        .collect();
    
    (fails, suspects)
}

fn main() {
    let log_content = "192.168.1.1 | LOGIN_FAIL\n10.0.0.5 | LOGIN_FAIL\n192.168.1.1 | LOGIN_FAIL\n8.8.8.8 | LOGIN_OK\n";
    
    let logs = parse_log(log_content);
    let (fails, suspects) = analyze(&logs, 2);
    
    println!("=== 失败统计 ===");
    for (ip, count) in &fails {
        println!("{}: {} 次", ip, count);
    }
    
    println!("\n=== 可疑 IP ===");
    for ip in &suspects {
        println!("[告警] {}", ip);
    }
}
```

这个程序综合了：结构体、HashMap/HashSet、迭代器、错误处理、借用。

---

## 12.3 测试与文档（Rust 的工程优势）

Rust 把测试和文档作为语言的一等公民：

### 12.3.1 单元测试

```rust
// 测试代码和业务代码写在一起
fn is_private_ip(ip: &str) -> bool {
    ip.starts_with("192.168.") || ip.starts_with("10.")
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_private_ip() {
        assert!(is_private_ip("192.168.1.1"));
        assert!(is_private_ip("10.0.0.1"));
        assert!(!is_private_ip("8.8.8.8"));
    }
    
    #[test]
    #[should_panic]   // 期望 panic 的测试
    fn test_panic() {
        panic!("expected");
    }
}
```

运行：`cargo test`。Rust 的测试框架内置，无需额外依赖。

### 12.3.2 文档测试

Rust 的文档注释里的代码块会被自动当测试运行：

```rust
/// 计算两个数的和
///
/// # 示例
/// ```
/// let result = add(2, 3);
/// assert_eq!(result, 5);
/// ```
fn add(a: i32, b: i32) -> i32 { a + b }
```

`cargo test` 会运行文档里的示例代码，确保文档和代码永远同步——这是 Rust 文档质量高的原因。

### 12.3.3 生成文档

```bash
cargo doc --open   # 生成并打开项目文档
```

从代码注释自动生成漂亮的 API 文档。安全工具团队开发时，这意味着文档不会过时。

> **工程化价值**：测试 + 文档内置，让 Rust 项目天然更可靠、更易维护。对安全工具来说，"可验证的正确性"至关重要。

---

## 12.4 Rust 卷总结

| 章节 | 核心内容 |
|------|---------|
| 1 | Rust 定位：安全 + 性能 + 并发 |
| 2 | 环境 + Cargo |
| 3 | 基础语法；默认不可变、越界检查 |
| 4 | 所有权、借用、生命周期（核心） |
| 5 | 结构体、枚举、Option、模式匹配 |
| 6 | Result、`?`、错误处理、thiserror/anyhow |
| 7 | 泛型、trait、集合、迭代器 |
| 8 | 并发：线程、channel、Mutex、Arc、Send/Sync、tokio |
| 9 | 安全工具实战、rayon、clap |
| 10 | Rust 与 AI：candle、向量数据库 |
| 11 | FFI 与 C 互操作 |
| 12 | 生态、综合项目、测试与文档 |

---

## 12.4 后续学习方向

1. **异步编程**：tokio、async/await（高性能网络服务）
2. **深入所有权**：进阶生命周期、内部可变性（Cell/RefCell）
3. **Rust 安全研究**：用 Rust 做漏洞挖掘、fuzzing
4. **WebAssembly**：Rust 编译到 WASM
5. **嵌入式 Rust**：物联网安全
6. **贡献开源**：给 Rust 安全工具贡献代码

---

## 12.5 本章练习

1. 扩展日志分析器，支持从文件读取。
2. 用 tokio 把日志分析器改成异步版。
3. 给扫描器添加 JSON 输出（用 serde_json）。
4. 思考：Rust 相比 C++ 在安全工具开发上的优势。
5. 规划你的下一个 Rust 项目。

---

**Rust 卷完！** 接下来是 Go 卷——云原生安全与并发。Go 语法简单、并发强大、部署方便，是写安全平台和网络安全工具的高效率选择。
