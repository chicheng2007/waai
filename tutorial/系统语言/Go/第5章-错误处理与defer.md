# 第 5 章 错误处理与 defer

## 本章目标

- 理解 Go 的 error 接口
- 掌握错误处理模式
- 掌握 panic/recover
- 深入理解 defer 的执行时机

Go 没有异常（exception），用显式的 error 返回值处理错误。这让错误处理清晰、可控。

---

## 5.1 error 接口

```go
type error interface {
    Error() string
}
```

任何实现了 `Error()` 方法的类型都是 error。

### 5.1.1 基本错误处理

```go
f, err := os.Open("config.txt")
if err != nil {
    fmt.Println("打开失败:", err)
    return
}
defer f.Close()
// 使用 f
```

> **Go 的习惯**：立即检查 err，不为 nil 就处理/返回。代码里会大量出现 `if err != nil`。

### 5.1.2 创建错误

```go
import "errors"

err := errors.New("端口不合法")

// 带格式
err := fmt.Errorf("IP %s 格式错误", ip)
```

### 5.1.3 自定义错误类型

```go
type ScanError struct {
    IP     string
    Reason string
}

func (e *ScanError) Error() string {
    return fmt.Sprintf("扫描 %s 失败: %s", e.IP, e.Reason)
}

func scan(ip string) error {
    if ip == "" {
        return &ScanError{IP: ip, Reason: "IP为空"}
    }
    return nil
}
```

### 5.1.4 错误包装（Go 1.13+）

```go
if err != nil {
    return fmt.Errorf("读取配置失败: %w", err)  // %w 包装错误
}

// 判断错误类型
if errors.Is(err, os.ErrNotExist) {
    fmt.Println("文件不存在")
}
```

---

## 5.2 panic 与 recover

### 5.2.1 panic

```go
panic("严重错误")
```

panic 会终止当前函数执行，逐层展开 goroutine，最后崩溃程序（除非 recover）。

> **Go 哲学**：panic 用于"程序无法继续"的严重错误，普通错误用 error 返回。

### 5.2.2 recover

```go
func safeCall() {
    defer func() {
        if r := recover(); r != nil {
            fmt.Println("捕获 panic:", r)
        }
    }()
    
    panic("出错了")  // 会被 recover 捕获
    fmt.Println("这行不会执行")
}
```

recover 必须在 defer 的函数里调用，用于从 panic 中恢复。

> **使用场景**：服务器里防止一个请求 panic 导致整个服务崩溃。但不要滥用——普通错误用 error，别拿 panic 当异常。

---

## 5.3 defer 深入

### 5.3.1 执行时机

```go
func example() {
    defer fmt.Println("defer 1")
    defer fmt.Println("defer 2")
    fmt.Println("函数体")
}
// 输出：
// 函数体
// defer 2
// defer 1   （LIFO）
```

### 5.3.2 参数求值时机

```go
func example() {
    i := 1
    defer fmt.Println(i)   // 参数 i 在 defer 时就求值（=1）
    i = 2
}
// 输出: 1
```

### 5.3.3 defer 与返回值

```go
func f() (result int) {
    defer func() {
        result++   // 修改命名返回值
    }()
    return 1   // 实际返回 2
}
```

> 这个特性很强大但容易混淆，理解即可，谨慎使用。

---

## 5.4 实战：健壮的配置加载

```go
package main

import (
    "bufio"
    "fmt"
    "os"
    "strconv"
    "strings"
)

type Config struct {
    Host string
    Port int
}

func loadConfig(path string) (Config, error) {
    var cfg Config
    
    f, err := os.Open(path)
    if err != nil {
        return cfg, fmt.Errorf("打开配置失败: %w", err)
    }
    defer f.Close()
    
    scanner := bufio.NewScanner(f)
    for scanner.Scan() {
        line := scanner.Text()
        parts := strings.SplitN(line, "=", 2)
        if len(parts) != 2 { continue }
        
        key, value := strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
        switch key {
        case "host":
            cfg.Host = value
        case "port":
            port, err := strconv.Atoi(value)
            if err != nil {
                return cfg, fmt.Errorf("端口格式错误: %w", err)
            }
            cfg.Port = port
        }
    }
    
    if cfg.Host == "" {
        return cfg, fmt.Errorf("缺少 host 配置")
    }
    return cfg, nil
}

func main() {
    cfg, err := loadConfig("config.txt")
    if err != nil {
        fmt.Println("错误:", err)
        return
    }
    fmt.Printf("主机: %s, 端口: %d\n", cfg.Host, cfg.Port)
}
```

---

## 5.6 错误处理的最佳实践

### 5.6.1 错误处理的三层境界

```go
// 第一层：忽略错误（最差）
f, _ := os.Open("config.txt")   // 忽略错误，后续可能 panic

// 第二层：简单处理
f, err := os.Open("config.txt")
if err != nil {
    return err   // 直接返回，无上下文
}

// 第三层：包装上下文（最佳）
f, err := os.Open("config.txt")
if err != nil {
    return fmt.Errorf("加载配置文件 %s 失败: %w", path, err)
}
```

好的错误信息应该回答三个问题：**什么操作失败了、在哪个上下文、根本原因是什么**。

### 5.6.2 错误处理模式对比

| 模式 | 适用场景 |
|------|---------|
| 返回 error | 大部分场景；可恢复错误 |
| panic/recover | 程序无法继续；或库内部不一致 |
| 日志 + 继续 | 非关键错误（如缓存失效） |
| 重试 | 网络抖动、临时故障 |

```go
// 重试模式（带指数退避）
func fetchWithRetry(url string, maxRetries int) error {
    var err error
    for i := 0; i < maxRetries; i++ {
        err = fetch(url)
        if err == nil { return nil }
        time.Sleep(time.Duration(1<<i) * time.Second)  // 1,2,4,8 秒
    }
    return fmt.Errorf("重试 %d 次后仍失败: %w", maxRetries, err)
}
```

### 5.6.3 错误与日志

```go
import "log"

// 记录错误但继续执行（非致命错误）
if err != nil {
    log.Printf("警告: 加载插件失败: %v", err)
    // 继续运行，使用默认配置
}
```

> **安全视角**：错误处理不当本身就是安全问题。忽略错误可能导致程序在不安全状态下运行；错误信息泄露过多可能暴露系统内部细节（如数据库结构、路径）。生产环境的错误日志和返回给用户的错误信息要区别对待——内部详细记录，对用户返回通用提示。

---

## 5.7 本章总结

| 知识点 | 内容 |
|--------|------|
| error 接口 | `Error() string` |
| 错误处理 | `if err != nil`；`fmt.Errorf`、`errors.New` |
| 自定义错误 | 实现 Error() 方法 |
| 错误包装 | `%w`、`errors.Is/As` |
| panic/recover | 严重错误；recover 在 defer 中捕获 |
| defer | LIFO；参数即时求值；可修改命名返回值 |
| 最佳实践 | 包装上下文；重试模式；错误与日志分离 |

---

## 本章练习

1. 写一个函数用 `%w` 包装错误。
2. 实现自定义错误类型。
3. 用 recover 防止程序崩溃。
4. 演示 defer 的 LIFO 顺序和参数求值时机。
5. 实现带指数退避的重试逻辑。
6. 思考：Go 为什么不用异常而用 error 返回值？各有什么优劣？

---

**下一章预告**：学习 Go 的核心竞争力——并发编程：Goroutine 与 Channel。这是 Go 最强大的特性。
