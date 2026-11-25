# 第 27 章 Linux 下的 Python / C/C++ / Rust / Go

## 本章目标

读完这一章，你将能够：

- 理解各语言在 Linux 上的开发环境搭建
- 掌握 pyenv/venv 管理 Python 环境
- 理解 C/C++ 在 Linux 上的编译与系统编程
- 掌握 Rust 的 rustup/cargo 工具链
- 掌握 Go 的 GOPATH/modules 与交叉编译
- 理解 Linux 特性（信号、文件描述符、进程）在各语言中的使用
- 把前四套教程的语言知识落到 Linux 主场

---

## 27.1 Python on Linux

### 27.1.1 安装与版本管理

Ubuntu 自带 Python3，但版本可能较旧。用 pyenv 管理多版本：

```bash
# 安装依赖
sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
  libreadline-dev libsqlite3-dev libffi-dev liblzma-dev

# 安装 pyenv
curl https://pyenv.run | bash
# 按提示把 pyenv 初始化加到 ~/.bashrc

pyenv install 3.11.0
pyenv global 3.11.0
python3 --version
```

### 27.1.2 虚拟环境

```bash
# venv（标准库）
python3 -m venv myenv
source myenv/bin/activate      # 激活
pip install requests
deactivate                     # 退出
```

> **最佳实践**：每个项目用独立虚拟环境，避免依赖冲突。呼应 Python 卷的环境管理章节。

### 27.1.3 Linux 特性在 Python 中

```python
import os
import signal
import subprocess

# 进程与信号
pid = os.fork()               # 创建子进程
os.kill(pid, signal.SIGTERM)  # 发信号

# 文件描述符
fd = os.open("/tmp/test", os.O_RDWR | os.O_CREAT)
os.write(fd, b"hello")
os.close(fd)

# 环境变量
path = os.environ.get("PATH")

# 执行外部命令
result = subprocess.run(["ls", "-la"], capture_output=True, text=True)
print(result.stdout)
```

Python 的 `os`、`subprocess`、`signal` 模块直接映射 Linux 系统调用，是写安全脚本、自动化工具的利器（呼应 Python 卷的系统编程部分）。

---

## 27.2 C/C++ on Linux

### 27.2.1 开发环境

```bash
sudo apt install build-essential gdb
```

`build-essential` 包含 gcc、g++、make、libc 开发库。

### 27.2.2 Linux 系统编程

C 是 Linux 系统的"母语"，系统调用直接用：

```c
#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <signal.h>

int main() {
    pid_t pid = fork();          // 创建进程
    if (pid == 0) {
        printf("子进程 PID: %d\n", getpid());
    } else {
        printf("父进程 PID: %d, 子进程: %d\n", getpid(), pid);
        kill(pid, SIGTERM);      // 发信号
    }
    return 0;
}
```

关键头文件：

- `unistd.h`：fork、exec、read、write、getpid
- `sys/types.h`、`sys/wait.h`：进程等待
- `signal.h`：信号处理
- `sys/socket.h`、`netinet/in.h`：网络编程（呼应系统语言卷 Socket 章节）
- `pthread.h`：线程

### 27.2.3 与安全的关联

系统语言卷讲的指针、内存漏洞（栈溢出、UAF）、缓冲区溢出，都是 C/C++ 在 Linux 上的问题。理解 Linux 内存布局、ASLR、Canary（第 17、21 章）才能理解攻防。

---

## 27.3 Rust on Linux

### 27.3.1 工具链

```bash
# 安装 rustup（Rust 版本管理器）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

rustc --version
cargo --version
```

### 27.3.2 Cargo 项目

```bash
cargo new myproject
cd myproject
cargo build          # 编译（debug）
cargo build --release  # 发布版（优化）
cargo run            # 编译并运行
cargo test           # 测试
```

`Cargo.toml` 管理依赖：

```toml
[package]
name = "myproject"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
tokio = { version = "1", features = ["full"] }
```

### 27.3.3 Rust 与 Linux 安全

Rust 的内存安全特性（所有权、借用）在编译期消除缓冲区溢出、UAF 等漏洞——这正是系统语言卷强调的。用 Rust 写安全工具（如 ripgrep、fd）既高性能又内存安全。

Linux 系统编程用 `libc` crate 或 `nix` crate 调用系统调用。

---

## 27.4 Go on Linux

### 27.4.1 安装

```bash
# 官网下载或用 apt
sudo apt install golang-go
go version
```

### 27.4.2 Go Modules

```bash
go mod init myproject
# 写 main.go
go run main.go
go build
```

`go.mod` 管理依赖（类似 Cargo.toml）。

### 27.4.3 交叉编译（Go 的杀手锏）

Go 能轻松交叉编译出各平台二进制：

```bash
# 编译成 Linux amd64
GOOS=linux GOARCH=amd64 go build -o app-linux

# 编译成 Windows
GOOS=windows GOARCH=amd64 go build -o app.exe

# 编译成 macOS
GOOS=darwin GOARCH=amd64 go build -o app-mac
```

这对安全工具分发极其有用——一次编写，多平台编译（呼应系统语言卷 Go 部分）。

### 27.4.4 Go 与 Linux 系统编程

Go 标准库 `os`、`syscall`、`net` 提供系统编程能力，`os/exec` 执行命令：

```go
package main
import (
    "fmt"
    "os/exec"
)
func main() {
    out, _ := exec.Command("ls", "-la").Output()
    fmt.Println(string(out))
}
```

---

## 27.5 语言选型与混合（呼应前四套教程）

| 场景 | 推荐语言 | 原因 |
|------|---------|------|
| 安全脚本、自动化、AI 调用 | Python | 生态丰富、开发快 |
| 底层、漏洞利用、性能敏感 | C/C++ | 直接系统调用、可控内存 |
| 内存安全的系统工具 | Rust | 编译期内存安全、高性能 |
| 并发网络服务、跨平台分发 | Go | goroutine 并发、单二进制 |

**混合使用**（呼应混合编程卷）：

- Python 写业务逻辑 + C/Rust 写性能核心（pybind11、PyO3）
- Go 写并发引擎 + Python 做 AI 推理
- 用 ctypes/cffi/PyO3 把各语言组合成系统

Linux 是这一切的舞台——编译、链接、部署、运行都在这里完成。

---

## 27.6 Linux 特性对照表

| Linux 概念 | Python | C | Rust | Go |
|-----------|--------|---|------|-----|
| 进程 | os.fork/subprocess | fork() | Command::new | os/exec |
| 信号 | signal 模块 | signal() | libc::signal | os/signal |
| 文件描述符 | os.open | open() | File::open | os.Open |
| 环境变量 | os.environ | getenv() | env::var | os.Getenv |
| 线程 | threading | pthread | std::thread | goroutine |
| 网络 | socket | socket() | TcpStream | net 包 |

---

## 27.7 本章总结

| 知识点 | 内容 |
|--------|------|
| Python | pyenv 版本管理、venv 虚拟环境、os/subprocess 系统调用 |
| C/C++ | build-essential、unistd.h 系统调用、fork/exec/socket |
| Rust | rustup/cargo、Cargo.toml、内存安全、系统编程 crate |
| Go | Go Modules、交叉编译（GOOS/GOARCH）、单二进制 |
| 选型 | Python 脚本、C 底层、Rust 安全系统、Go 并发网络 |
| 混合 | pybind11/PyO3/cgo 组合语言（呼应混合编程卷） |
| 对照 | 各语言的进程/信号/文件/网络操作映射 Linux 系统调用 |

---

## 本章练习

1. 用 pyenv 安装一个 Python 版本，用 venv 创建虚拟环境。
2. 写一个 Python 脚本用 subprocess 执行 `ls -la`，理解它与 Shell 的关系。
3. 用 C 写一个 fork 程序，观察父子进程的输出。
4. 安装 Rust，用 cargo 创建一个项目并运行。
5. 安装 Go，写一个程序用 `os/exec` 执行命令。
6. 用 Go 交叉编译出一个 Windows 可执行文件（`.exe`）。
7. 对照 27.6 的表格，在各语言里实现"获取环境变量 PATH"。
8. 思考：结合前四套教程，为什么"混合编程"在 Linux 上最自然？各语言在 Linux 上有什么共同点？

---

**下一章预告**：我们将学习性能分析与调优——如何找到系统瓶颈（CPU、内存、IO、网络）并优化。这是排查 AI 训练慢、服务卡顿的必备技能。
