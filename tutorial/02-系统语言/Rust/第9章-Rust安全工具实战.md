# 第 9 章 用 Rust 写安全工具

## 本章目标

- 用 Rust 构建完整的安全工具
- 实现一个并发端口扫描器
- 实现一个文件哈希工具
- 理解 Rust 在安全工具开发中的优势

> **伦理声明**：所有工具仅用于本机、自建靶场或授权环境。

---

## 9.1 项目：并发端口扫描器

### 9.1.1 Cargo.toml

```toml
[package]
name = "rustscan"
version = "0.1.0"
edition = "2021"

[dependencies]
clap = { version = "4", features = ["derive"] }  # 命令行参数
colored = "2"   # 彩色输出
```

### 9.1.2 主程序

```rust
use std::net::{TcpStream, ToSocketAddrs};
use std::time::Duration;
use std::sync::{Arc, Mutex};
use std::thread;

struct Scanner {
    target: String,
    timeout: Duration,
    open_ports: Arc<Mutex<Vec<u16>>>,
}

impl Scanner {
    fn new(target: &str, timeout_ms: u64) -> Self {
        Self {
            target: target.to_string(),
            timeout: Duration::from_millis(timeout_ms),
            open_ports: Arc::new(Mutex::new(Vec::new())),
        }
    }
    
    fn scan_port(&self, port: u16) -> bool {
        let addr = format!("{}:{}", self.target, port);
        match addr.to_socket_addrs() {
            Ok(mut iter) => {
                if let Some(socket_addr) = iter.next() {
                    TcpStream::connect_timeout(&socket_addr, self.timeout).is_ok()
                } else {
                    false
                }
            }
            Err(_) => false,
        }
    }
    
    fn scan_range(&self, start: u16, end: u16, threads: usize) -> Vec<u16> {
        let mut handles = vec![];
        let chunk = (end - start + 1) as usize / threads;
        
        for t in 0..threads {
            let s = start + (t * chunk) as u16;
            let e = if t == threads - 1 { end } else { s + chunk as u16 - 1 };
            
            // 每个线程需要自己的 Scanner 数据副本
            let target = self.target.clone();
            let timeout = self.timeout;
            let open_ports = Arc::clone(&self.open_ports);
            
            handles.push(thread::spawn(move || {
                for port in s..=e {
                    let addr = format!("{}:{}", target, port);
                    if let Ok(mut iter) = addr.to_socket_addrs() {
                        if let Some(sa) = iter.next() {
                            if TcpStream::connect_timeout(&sa, timeout).is_ok() {
                                open_ports.lock().unwrap().push(port);
                            }
                        }
                    }
                }
            }));
        }
        
        for h in handles { h.join().unwrap(); }
        
        let mut ports = self.open_ports.lock().unwrap().clone();
        ports.sort();
        ports
    }
}

fn main() {
    let scanner = Scanner::new("127.0.0.1", 200);
    let open = scanner.scan_range(1, 1024, 50);
    println!("开放端口: {:?}", open);
}
```

编译运行：

```bash
cargo build --release
./target/release/rustscan
```

---

## 9.2 Rust 安全工具的优势体现

### 9.2.1 内存安全

扫描器处理网络数据（banner、响应内容），如果用 C 写，解析时稍不注意就溢出。Rust 的 String/Vec 自动管理，不会溢出。

### 9.2.2 并发安全

多线程共享结果列表，用 `Arc<Mutex<Vec>>`，编译器保证正确同步。C 里忘记加锁就是数据竞争，Rust 编译不过。

### 9.2.3 错误处理

网络操作到处可能失败，Rust 用 Result + `?` 优雅处理，不会像 C 那样忽略返回值导致隐患。

---

## 9.3 文件哈希工具（SHA256 简化版）

```rust
use std::fs;
use std::path::Path;

// 实际项目用 sha2 crate：cargo add sha2
// 这里演示文件读取的安全处理

fn read_file_safe(path: &Path) -> Result<Vec<u8>, String> {
    // 检查文件大小，防止读取超大文件耗内存
    let metadata = fs::metadata(path)
        .map_err(|e| format!("无法读取元数据: {}", e))?;
    
    let max_size = 100 * 1024 * 1024;  // 100MB 上限
    if metadata.len() > max_size {
        return Err("文件过大".into());
    }
    
    fs::read(path).map_err(|e| format!("读取失败: {}", e))
}

fn main() {
    match read_file_safe(Path::new("suspicious.bin")) {
        Ok(data) => println!("读取 {} 字节", data.len()),
        Err(e) => eprintln!("错误: {}", e),
    }
}
```

> **安全思路**：Rust 的类型系统让你自然写出安全检查（Result 强制处理错误、大小检查防止 DoS）。

---

## 9.4 综合项目建议

1. **端口扫描器** + 服务指纹识别（读取 banner）
2. **日志分析器**：解析日志 + 异常检测 + 报告
3. **文件完整性检查**：哈希计算 + 基线对比
4. **弱口令检测器**：多线程检测 + 安全报告

---

## 9.5 用 rayon 简化并行

手写线程管理比较繁琐，rayon 提供并行迭代器，几乎零成本地把顺序代码变并行：

```rust
// Cargo.toml: rayon = "1"
use rayon::prelude::*;

fn parallel_scan(ports: Vec<u16>, target: &str) -> Vec<u16> {
    ports.par_iter()   // 并行迭代器
        .filter(|&&port| {
            let addr = format!("{}:{}", target, port);
            std::net::TcpStream::connect_timeout(
                &addr.parse().unwrap(),
                std::time::Duration::from_millis(200)
            ).is_ok()
        })
        .copied()
        .collect()
}

fn main() {
    let open = parallel_scan((1..=1024).collect(), "127.0.0.1");
    println!("开放端口: {:?}", open);
}
```

`par_iter()` 把普通的 `iter()` 变成并行版本，rayon 自动用线程池分配任务。代码几乎没有变化，但自动利用了多核 CPU。

> **对比手写线程**：前面用 `std::thread` + `Arc<Mutex>` 写了几十行；用 rayon 只要几行。而且 rayon 的 work-stealing 调度比手动分块更负载均衡。这是 Rust 生态"零成本抽象"的又一体现。

---

## 9.6 用 clap 构建专业 CLI

```rust
// Cargo.toml: clap = { version = "4", features = ["derive"] }
use clap::Parser;

#[derive(Parser, Debug)]
#[command(name = "rustscan", about = "高性能端口扫描器")]
struct Args {
    /// 目标 IP
    #[arg(short, long, default_value = "127.0.0.1")]
    target: String,
    
    /// 起始端口
    #[arg(short, long, default_value_t = 1)]
    start: u16,
    
    /// 结束端口
    #[arg(short = 'e', long, default_value_t = 1024)]
    end: u16,
    
    /// 超时（毫秒）
    #[arg(long, default_value_t = 200)]
    timeout: u64,
}

fn main() {
    let args = Args::parse();
    println!("扫描 {}:{} - {}", args.target, args.start, args.end);
}
```

clap 自动生成 `--help`、参数校验、错误信息。这是写专业命令行安全工具的标准做法。

---

## 9.7 本章总结

| 优势 | 体现 |
|------|------|
| 内存安全 | String/Vec 自动管理，无溢出 |
| 并发安全 | Arc+Mutex，编译器保证同步 |
| 错误处理 | Result + ?，不忽略错误 |
| 高性能 | 接近 C 的性能 |
| rayon | 并行迭代器，简化并发 |
| clap | 专业的命令行参数解析 |

---

## 本章练习

1. 给扫描器添加命令行参数（用 clap）。
2. 用 rayon 重写扫描器的并发部分，对比代码量。
3. 添加服务 banner 识别。
4. 实现文件哈希工具（用 sha2 crate）。
5. 把工具整理到 GitHub，写 README。

---

**下一章预告**：学习 Rust 与 AI——candle 框架、模型推理、向量数据库，看看 Rust 在 AI 领域的实际应用。
