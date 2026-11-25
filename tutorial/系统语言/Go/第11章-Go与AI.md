# 第 11 章 Go 与 AI：服务编排与工程化

## 本章目标

- 了解 Go 在 AI 领域的定位
- 了解 Ollama 与大模型本地运行
- 用 Go 构建 AI API 服务/网关
- 理解 Go 做 AI 工程化的优势

Go 在 AI 领域不主打训练，而是**工程化**：把模型包装成高并发服务、做 API 网关、编排 AI 应用。这是 AI 落地的关键环节。

---

## 11.1 Go AI 生态

| 项目 | 用途 |
|------|------|
| **Ollama** | 本地运行大模型的工具（Go 写） |
| **langchaingo** | Go 版 LangChain |
| **go-openai** | OpenAI API 的 Go 客户端 |
| **llama.go** | llama.cpp 的 Go 绑定 |
| **gorgonia** | Go 的深度学习库 |

---

## 11.2 Ollama：本地大模型

Ollama 是用 Go 写的工具，能在本机一键运行 Llama、DeepSeek、Qwen 等大模型。它提供简单的 HTTP API，Go 可以轻松调用：

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

type OllamaRequest struct {
    Model  string `json:"model"`
    Prompt string `json:"prompt"`
    Stream bool   `json:"stream"`
}

type OllamaResponse struct {
    Response string `json:"response"`
}

func askOllama(prompt string) (string, error) {
    reqBody := OllamaRequest{
        Model:  "llama2",
        Prompt: prompt,
        Stream: false,
    }
    data, _ := json.Marshal(reqBody)
    
    resp, err := http.Post("http://localhost:11434/api/generate",
        "application/json", bytes.NewBuffer(data))
    if err != nil { return "", err }
    defer resp.Body.Close()
    
    var result OllamaResponse
    json.NewDecoder(resp.Body).Decode(&result)
    return result.Response, nil
}

func main() {
    answer, err := askOllama("什么是网络安全?")
    if err != nil {
        fmt.Println("错误:", err)
        return
    }
    fmt.Println(answer)
}
```

---

## 11.3 构建 AI API 网关

Go 的高并发适合做 AI 服务的网关（负载均衡、限流、缓存）：

```go
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "sync"
    "time"
)

// 简单的限流器
type RateLimiter struct {
    mu       sync.Mutex
    requests map[string][]time.Time
    limit    int
    window   time.Duration
}

func (rl *RateLimiter) Allow(key string) bool {
    rl.mu.Lock()
    defer rl.mu.Unlock()
    
    now := time.Now()
    times := rl.requests[key]
    
    // 清理过期
    var valid []time.Time
    for _, t := range times {
        if now.Sub(t) < rl.window { valid = append(valid, t) }
    }
    
    if len(valid) >= rl.limit { return false }
    
    rl.requests[key] = append(valid, now)
    return true
}

var limiter = &RateLimiter{
    requests: make(map[string][]time.Time),
    limit:    10,
    window:   time.Minute,
}

func aiHandler(w http.ResponseWriter, r *http.Request) {
    clientIP := r.RemoteAddr
    if !limiter.Allow(clientIP) {
        http.Error(w, "请求过于频繁", http.StatusTooManyRequests)
        return
    }
    
    // 这里转发到实际的 AI 模型服务
    response := map[string]string{"answer": "这是 AI 的回答"}
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}

func main() {
    http.HandleFunc("/api/ask", aiHandler)
    fmt.Println("AI 网关启动 :8080")
    http.ListenAndServe(":8080", nil)
}
```

> **安全价值**：AI 服务网关能做限流（防滥用）、认证、日志审计、内容过滤——这是 AI 系统安全的重要组成部分。

---

## 11.4 Go 做 RAG 系统

RAG（检索增强生成）系统需要高性能检索服务，Go 适合做这层：

```
用户问题 → Go API 网关 → 向量库检索 → 组装 Prompt → 调用 LLM → 返回
```

Go 负责编排，发挥并发和部署优势。

---

## 11.5 流式响应（Streaming）

大模型的输出是"一个字一个字"生成的，用户体验上需要流式返回（像 ChatGPT 那样逐字显示）。Go 的 HTTP 流式响应实现很优雅：

```go
package main

import (
    "bufio"
    "encoding/json"
    "fmt"
    "net/http"
    "strings"
    "time"
)

func streamHandler(w http.ResponseWriter, r *http.Request) {
    // 设置流式响应头
    w.Header().Set("Content-Type", "text/event-stream")
    w.Header().Set("Cache-Control", "no-cache")
    w.Header().Set("Connection", "keep-alive")
    
    flusher, ok := w.(http.Flusher)
    if !ok {
        http.Error(w, "不支持流式", http.StatusInternalServerError)
        return
    }
    
    // 模拟逐 token 输出（实际对接模型 API）
    tokens := strings.Split("你好，我是 AI 助手，很高兴为你服务。", "")
    for _, token := range tokens {
        data, _ := json.Marshal(map[string]string{"token": token})
        fmt.Fprintf(w, "data: %s\n\n", data)
        flusher.Flush()   // 立即推送给客户端
        time.Sleep(50 * time.Millisecond)
    }
}

func main() {
    http.HandleFunc("/stream", streamHandler)
    http.ListenAndServe(":8080", nil)
}
```

> **Server-Sent Events (SSE)** 是大模型流式输出的标准方式。`http.Flusher` 让你能绕过缓冲，实时推送数据。这是 AI 应用工程化的必备技术。

---

## 11.6 调用 OpenAI 兼容 API

国内很多大模型（DeepSeek、通义、智谱等）都兼容 OpenAI 的接口格式，用同一套代码就能切换模型：

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "os"
)

type Message struct {
    Role    string `json:"role"`
    Content string `json:"content"`
}

type ChatRequest struct {
    Model    string    `json:"model"`
    Messages []Message `json:"messages"`
    Temperature float64 `json:"temperature"`
}

type ChatResponse struct {
    Choices []struct {
        Message Message `json:"message"`
    } `json:"choices"`
}

func chat(baseURL, apiKey, model, question string) (string, error) {
    reqBody := ChatRequest{
        Model: model,
        Messages: []Message{
            {Role: "system", Content: "你是一位网络安全专家。"},
            {Role: "user", Content: question},
        },
        Temperature: 0.7,
    }
    data, _ := json.Marshal(reqBody)
    
    req, _ := http.NewRequest("POST", baseURL+"/chat/completions", bytes.NewBuffer(data))
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer "+apiKey)
    
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil { return "", err }
    defer resp.Body.Close()
    
    body, _ := io.ReadAll(resp.Body)
    var result ChatResponse
    if err := json.Unmarshal(body, &result); err != nil { return "", err }
    
    if len(result.Choices) == 0 {
        return "", fmt.Errorf("API 返回为空: %s", body)
    }
    return result.Choices[0].Message.Content, nil
}

func main() {
    // 从环境变量读 API Key（安全！不要写死在代码里）
    apiKey := os.Getenv("LLM_API_KEY")
    baseURL := os.Getenv("LLM_BASE_URL")  // 如 https://api.deepseek.com
    
    answer, err := chat(baseURL, apiKey, "deepseek-chat", "如何防御 SQL 注入?")
    if err != nil {
        fmt.Println("错误:", err)
        return
    }
    fmt.Println(answer)
}
```

> **安全提示**：API Key 必须通过环境变量或密钥管理服务提供，绝不能硬编码或提交到 GitHub。这是 AI 应用最常见的泄密点之一。

---

## 11.7 AI 应用的安全防护

作为安全从业者，构建 AI 应用时必须考虑安全：

### 11.7.1 Prompt 注入检测中间件

```go
func sanitizePrompt(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // 读取请求体
        body, _ := io.ReadAll(r.Body)
        r.Body = io.NopCloser(bytes.NewBuffer(body))
        
        prompt := string(body)
        
        // 检测注入特征
        suspiciousPatterns := []string{
            "忽略之前的", "ignore previous", "system prompt",
            "你现在是", "开发者模式", "jailbreak",
        }
        for _, pattern := range suspiciousPatterns {
            if strings.Contains(strings.ToLower(prompt), strings.ToLower(pattern)) {
                http.Error(w, "检测到可疑输入", http.StatusBadRequest)
                return
            }
        }
        
        next.ServeHTTP(w, r)
    })
}
```

### 11.7.2 输出内容审查

模型的输出也可能包含有害内容或敏感信息泄露，需要二次审查：

```go
func reviewOutput(output string) (bool, string) {
    // 检查是否泄露敏感信息（如 API Key、身份证号）
    patterns := map[string]*regexp.Regexp{
        "API Key": regexp.MustCompile(`sk-[a-zA-Z0-9]{20,}`),
        "手机号":   regexp.MustCompile(`1[3-9]\d{9}`),
        "身份证":   regexp.MustCompile(`\d{17}[\dXx]`),
    }
    
    for name, re := range patterns {
        if re.MatchString(output) {
            return false, "输出包含敏感信息: " + name
        }
    }
    return true, ""
}
```

> **纵深防御**：Prompt 注入目前没有银弹，必须多层防护——输入过滤、权限最小化、输出审查、人工确认关键操作。这与第 30 章讲的 AI 安全原则一致。

---

## 11.8 本章总结

| 知识点 | 内容 |
|--------|------|
| Go AI 生态 | Ollama、langchaingo、go-openai |
| Ollama | 本地大模型，HTTP API 调用 |
| 流式响应 | SSE + http.Flusher，逐 token 输出 |
| OpenAI 兼容 API | 一套代码切换多个模型 |
| AI 网关 | 限流、认证、日志、内容过滤 |
| AI 应用安全 | Prompt 注入检测、输出审查 |
| RAG | Go 做编排层，高性能检索 |
| 优势 | 高并发、单二进制、易部署 |

---

## 本章练习

1. 安装 Ollama，用 Go 调用它生成文本。
2. 实现 SSE 流式输出。
3. 用 OpenAI 兼容接口接入一个国内大模型。
4. 给 AI 网关添加认证（API Key）和 Prompt 注入检测。
5. 实现输出敏感信息审查。
6. 用 Go 做一个 RAG 查询的 API 原型。
7. 思考：为什么 AI 服务网关适合用 Go 写？AI 应用有哪些特有的安全挑战？

---

**下一章预告**：Go 卷收官——综合实战项目，构建并发漏洞扫描器，总结 Go 卷知识。
