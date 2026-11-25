# 第 9 章 用 Go 写安全工具

## 本章目标

- 构建完整的并发漏洞扫描器
- 实现 Web 路径爆破工具
- 理解 Go 安全工具的设计模式

> **伦理声明**：所有工具仅用于本机、自建靶场（如 DVWA）或明确授权的目标。未经授权扫描他人系统违法。

---

## 9.1 并发端口扫描器（完整版）

```go
package main

import (
    "flag"
    "fmt"
    "net"
    "sort"
    "sync"
    "time"
)

type Scanner struct {
    Host    string
    Timeout time.Duration
    Workers int
}

func (s *Scanner) scanPort(port int, wg *sync.WaitGroup, sem chan struct{}, results chan<- int) {
    defer wg.Done()
    sem <- struct{}{}        // 获取信号量（限制并发）
    defer func() { <-sem }() // 释放
    
    address := fmt.Sprintf("%s:%d", s.Host, port)
    conn, err := net.DialTimeout("tcp", address, s.Timeout)
    if err == nil {
        conn.Close()
        results <- port
    }
}

func (s *Scanner) Scan(start, end int) []int {
    results := make(chan int)
    sem := make(chan struct{}, s.Workers)   // 并发控制
    var wg sync.WaitGroup
    
    for port := start; port <= end; port++ {
        wg.Add(1)
        go s.scanPort(port, &wg, sem, results)
    }
    
    go func() {
        wg.Wait()
        close(results)
    }()
    
    var open []int
    for p := range results {
        open = append(open, p)
    }
    sort.Ints(open)
    return open
}

func main() {
    host := flag.String("h", "127.0.0.1", "目标主机")
    start := flag.Int("s", 1, "起始端口")
    end := flag.Int("e", 1024, "结束端口")
    workers := flag.Int("w", 100, "并发数")
    flag.Parse()
    
    scanner := &Scanner{Host: *host, Timeout: 300 * time.Millisecond, Workers: *workers}
    
    start_time := time.Now()
    ports := scanner.Scan(*start, *end)
    elapsed := time.Since(start_time)
    
    fmt.Printf("扫描 %s 完成，耗时 %v\n", *host, elapsed)
    fmt.Printf("开放端口: %v\n", ports)
}
```

编译运行：

```bash
go build -o scanner scanner.go
./scanner -h 127.0.0.1 -s 1 -e 1024 -w 200
```

> **信号量模式**：用 `chan struct{}` 作为信号量控制并发数，避免创建过多 goroutine。这是 Go 并发控制的经典模式。

---

## 9.2 Web 路径爆破工具

```go
package main

import (
    "bufio"
    "fmt"
    "net/http"
    "os"
    "sync"
    "time"
)

func checkPath(baseURL, path string, client *http.Client, wg *sync.WaitGroup,
               sem chan struct{}, results chan<- string) {
    defer wg.Done()
    sem <- struct{}{}
    defer func() { <-sem }()
    
    url := baseURL + "/" + path
    resp, err := client.Get(url)
    if err != nil { return }
    defer resp.Body.Close()
    
    if resp.StatusCode >= 200 && resp.StatusCode < 400 {
        results <- fmt.Sprintf("[%d] %s", resp.StatusCode, url)
    }
}

func main() {
    baseURL := "http://127.0.0.1:8080"
    wordlist, _ := os.Open("wordlist.txt")
    defer wordlist.Close()
    
    client := &http.Client{Timeout: 3 * time.Second}
    sem := make(chan struct{}, 20)
    results := make(chan string)
    var wg sync.WaitGroup
    
    scanner := bufio.NewScanner(wordlist)
    for scanner.Scan() {
        wg.Add(1)
        go checkPath(baseURL, scanner.Text(), client, &wg, sem, results)
    }
    
    go func() { wg.Wait(); close(results) }()
    
    for r := range results {
        fmt.Println(r)
    }
}
```

> **伦理提示**：仅在自己的靶场（DVWA、本地 Web 服务）练习路径爆破。

---

## 9.3 Go 安全工具的设计优势

1. **并发简单**：goroutine + channel，几行代码实现高并发
2. **单二进制**：编译后直接运行，红队落地方便
3. **跨平台**：交叉编译出各平台版本
4. **标准库强**：网络、加密、解析全内置
5. **性能适中**：比 Python 快很多，开发效率也高

---

## 9.4 综合项目建议

1. **端口扫描器 + 服务识别**
2. **Web 目录/文件扫描器**
3. **子域名枚举工具**
4. **日志分析 + 告警系统**
5. **并发漏洞检测框架**

---

## 9.5 本章总结

| 模式 | 实现 |
|------|------|
| 并发控制 | `chan struct{}` 信号量 |
| 结果收集 | channel + WaitGroup |
| 命令行参数 | flag 包 |
| HTTP 检测 | http.Client + Timeout |

---

## 本章练习

1. 给扫描器添加服务 banner 识别。
2. 给路径爆破工具添加状态码过滤参数。
3. 实现一个子域名枚举工具。
4. 添加 JSON 输出格式。
5. 把工具整理到 GitHub，写 README 和用法说明。

---

**下一章预告**：学习 Go 与云原生安全——容器、Kubernetes、供应链安全，这是 Go 的主战场。
