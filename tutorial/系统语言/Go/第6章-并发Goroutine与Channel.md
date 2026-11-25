# 第 6 章 并发编程：Goroutine 与 Channel

## 本章目标

- 理解 Goroutine
- 掌握 Channel 的使用
- 理解 Go 的并发哲学："不要通过共享内存来通信，而要通过通信来共享内存"
- 掌握 sync 包（WaitGroup、Mutex）
- 掌握 select 和 context

**这是 Go 最核心、最有特色的章节。** Go 的并发模型简单而强大，是它成为云原生和安全工具首选语言的关键原因。

---

## 6.1 Goroutine

### 6.1.1 什么是 Goroutine

Goroutine 是 Go 的轻量级线程：

- 由 Go 运行时调度（不是 OS 线程）
- 初始栈只有几 KB（可动态增长）
- 可以轻松创建几万、几十万个
- 切换开销极小

```go
func say(s string) {
    for i := 0; i < 3; i++ {
        fmt.Println(s, i)
        time.Sleep(100 * time.Millisecond)
    }
}

func main() {
    go say("world")    // 启动 goroutine
    say("hello")       // 主 goroutine
}
```

`go` 关键字启动一个 goroutine。

### 6.1.2 主 goroutine 退出问题

```go
func main() {
    go fmt.Println("子 goroutine")
    // main 退出，子 goroutine 可能还没执行就结束了
}
```

需要等待机制。用 `time.Sleep` 简单但不靠谱，正确做法用 WaitGroup 或 Channel。

---

## 6.2 Channel：通信的管道

Channel 是 goroutine 之间通信的通道，类型安全、线程安全。

### 6.2.1 基本用法

```go
ch := make(chan int)   // 创建无缓冲 channel

go func() {
    ch <- 42           // 发送数据
}()

value := <-ch          // 接收数据（阻塞直到有数据）
fmt.Println(value)
```

### 6.2.2 缓冲 Channel

```go
ch := make(chan int, 3)   // 缓冲大小 3

ch <- 1   // 不阻塞（缓冲没满）
ch <- 2
ch <- 3
// ch <- 4   // 阻塞（缓冲满了）
```

### 6.2.3 关闭 Channel

```go
ch := make(chan int)

go func() {
    for i := 0; i < 5; i++ {
        ch <- i
    }
    close(ch)   // 关闭，表示不再发送
}()

// 方式一：range 遍历（推荐）
for v := range ch {
    fmt.Println(v)
}

// 方式二：检查 ok
for {
    v, ok := <-ch
    if !ok { break }
    fmt.Println(v)
}
```

---

## 6.3 WaitGroup：等待多个 goroutine

```go
var wg sync.WaitGroup

func worker(id int) {
    defer wg.Done()   // 完成时减 1
    fmt.Printf("worker %d 工作\n", id)
}

func main() {
    for i := 0; i < 5; i++ {
        wg.Add(1)       // 计数加 1
        go worker(i)
    }
    wg.Wait()           // 等待所有 Done
    fmt.Println("全部完成")
}
```

---

## 6.4 select：多路复用

```go
select {
case msg := <-ch1:
    fmt.Println("收到 ch1:", msg)
case msg := <-ch2:
    fmt.Println("收到 ch2:", msg)
case <-time.After(1 * time.Second):
    fmt.Println("超时")
}
```

select 等待多个 channel 操作，哪个先就绪就执行哪个。常用于超时控制。

---

## 6.5 context：取消与超时

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

go func() {
    for {
        select {
        case <-ctx.Done():
            fmt.Println("取消")
            return
        default:
            // 工作
        }
    }
}()

<-ctx.Done()   // 等待超时
```

context 是 Go 中控制 goroutine 生命周期的标准方式，网络请求、超时、取消都靠它。

---

## 6.6 并发安全：sync.Mutex

Go 推荐用 channel 通信，但有时需要共享状态，用 Mutex：

```go
var mu sync.Mutex
var count int

func increment() {
    mu.Lock()
    defer mu.Unlock()
    count++
}
```

> **数据竞争检测**：`go run -race main.go` 能检测数据竞争，开发并发程序必备工具。

---

## 6.7 实战：并发端口扫描器

```go
package main

import (
    "fmt"
    "net"
    "sync"
    "time"
)

func scanPort(host string, port int, wg *sync.WaitGroup, results chan<- int) {
    defer wg.Done()
    
    address := fmt.Sprintf("%s:%d", host, port)
    conn, err := net.DialTimeout("tcp", address, 200*time.Millisecond)
    if err == nil {
        conn.Close()
        results <- port
    }
}

func main() {
    host := "127.0.0.1"
    results := make(chan int)
    var wg sync.WaitGroup
    
    // 启动扫描
    for port := 1; port <= 1024; port++ {
        wg.Add(1)
        go scanPort(host, port, &wg, results)
    }
    
    // 关闭结果的 goroutine
    go func() {
        wg.Wait()
        close(results)
    }()
    
    // 收集结果
    var openPorts []int
    for port := range results {
        openPorts = append(openPorts, port)
    }
    
    fmt.Println("开放端口:", openPorts)
}
```

> **注意**：这里启动了 1024 个 goroutine，Go 轻松处理。如果用 C 的线程，1024 个线程会消耗大量资源。这正是 Go 并发的优势。

> **伦理提示**：仅扫描本机或授权目标。

---

## 6.8 并发模式：Worker Pool

Worker Pool（工作池）是 Go 并发的经典模式，广泛用于扫描器、爬虫、任务处理：

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

// 工作任务
type Task struct {
    ID   int
    Data string
}

func worker(id int, tasks <-chan Task, results chan<- string, wg *sync.WaitGroup) {
    defer wg.Done()
    for task := range tasks {   // 从通道读取任务，通道关闭则退出
        // 模拟处理
        time.Sleep(100 * time.Millisecond)
        results <- fmt.Sprintf("worker %d 完成任务 %d: %s", id, task.ID, task.Data)
    }
}

func main() {
    const numWorkers = 5
    tasks := make(chan Task, 100)
    results := make(chan string, 100)
    
    var wg sync.WaitGroup
    
    // 启动固定数量的 worker
    for i := 1; i <= numWorkers; i++ {
        wg.Add(1)
        go worker(i, tasks, results, &wg)
    }
    
    // 提交任务
    for i := 1; i <= 20; i++ {
        tasks <- Task{ID: i, Data: fmt.Sprintf("数据%d", i)}
    }
    close(tasks)   // 关闭任务通道，worker 处理完会退出
    
    // 等待所有 worker 完成
    go func() {
        wg.Wait()
        close(results)
    }()
    
    // 收集结果
    for r := range results {
        fmt.Println(r)
    }
}
```

**Worker Pool 的价值**：

1. **控制并发数**：不会一次创建几万个 goroutine（资源可控）
2. **复用 worker**：避免频繁创建销毁的开销
3. **解耦生产消费**：任务生产和处理速度可以不同

> **安全工具应用**：端口扫描器、Web 目录爆破、子域名枚举，全都是 Worker Pool 模式——把目标放进任务队列，固定数量 worker 并发处理。第 9 章的工具就是基于这个模式。

---

## 6.9 并发模式：Pipeline（流水线）

Pipeline 把处理流程拆成多个阶段，每个阶段用 goroutine + channel 连接：

```go
package main

import "fmt"

// 阶段1：生成数字
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        for _, n := range nums { out <- n }
        close(out)
    }()
    return out
}

// 阶段2：平方
func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        for n := range in { out <- n * n }
        close(out)
    }()
    return out
}

// 阶段3：过滤偶数
func filterEven(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        for n := range in {
            if n%2 == 0 { out <- n }
        }
        close(out)
    }()
    return out
}

func main() {
    // 串联成流水线
    result := filterEven(square(generate(1, 2, 3, 4, 5)))
    for n := range result {
        fmt.Println(n)   // 4, 16
    }
}
```

Pipeline 让每个阶段独立并发运行，数据像流水一样处理。适合数据处理管道（日志分析、威胁检测流水线）。

---

## 6.10 goroutine 泄漏

这是 Go 并发最常见的坑：goroutine 启动后永远不退出，泄漏内存。

```go
// 错误示例：goroutine 永远阻塞在 channel 上
func leak() {
    ch := make(chan int)
    go func() {
        val := <-ch   // 永远等不到数据，goroutine 泄漏
        fmt.Println(val)
    }()
    // 没有向 ch 发送数据，也没有关闭它
}
```

**预防方法**：

1. 用 context 控制 goroutine 生命周期
2. 确保 channel 会被关闭或写入
3. 用 `go tool pprof` 检测 goroutine 数量异常

```go
// 正确：用 context 取消
func noLeak(ctx context.Context) {
    ch := make(chan int)
    go func() {
        select {
        case val := <-ch:
            fmt.Println(val)
        case <-ctx.Done():   // 取消时退出
            return
        }
    }()
}
```

> **安全关联**：长运行的安全服务（如流量监控）如果 goroutine 泄漏，最终会耗尽内存崩溃——这本身就是一种 DoS。写服务时必须注意 goroutine 的生命周期管理。

---

## 6.11 本章总结

| 知识点 | 内容 |
|--------|------|
| Goroutine | 轻量级线程；`go` 启动 |
| Channel | `make(chan T)`；`<-` 发送接收；缓冲；关闭 |
| WaitGroup | Add/Done/Wait 等待多个 goroutine |
| select | 多路复用 + 超时 |
| context | 取消、超时控制 |
| Mutex | 共享状态保护 |
| Worker Pool | 工作池模式，控制并发数 |
| Pipeline | 流水线模式，阶段化处理 |
| goroutine 泄漏 | 用 context 防止 |
| race 检测 | `go run -race` |
| 哲学 | 通过通信共享内存，而非共享内存通信 |

---

## 本章练习

1. 用 goroutine 并发计算 1-100 的和。
2. 用 channel 实现生产者-消费者。
3. 用 WaitGroup 等待多个任务。
4. 用 select 实现超时控制。
5. 用 Worker Pool 重写端口扫描器。
6. 用 Pipeline 实现一个日志处理流水线。
7. 用 `go run -race` 检测数据竞争。
8. 思考：goroutine 为什么比线程轻量？goroutine 泄漏如何预防？

---

**下一章预告**：学习 Go 网络编程——TCP、HTTP、Socket。这是写安全工具和 Web 服务的基础，Go 的标准库对网络支持极好。
