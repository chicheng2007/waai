# 第 14 章 Go 共享库供 Python 调用

## 本章目标

读完这一章，你将能够：

- 设计干净的 C 导出层（C ABI），稳定地把 Go 能力暴露给 Python
- 处理复杂数据结构：结构体、数组、二进制 buffer 的传递
- 用句柄（handle）模式管理 Go 对象生命周期
- 正确处理 Go runtime 与线程（关键！）
- 用 ctypes/cffi 调用 Go 共享库
- 构建一个完整的 Python 包包装 Go 引擎
- 知道 Python↔Go 混合的常见陷阱

---

## 14.1 为什么需要"导出层设计"

第 13 章我们能把 Go 函数导出成 C 符号了。但直接导出 Go 的复杂类型（slice、map、interface）给 Python 是不行的——C ABI 只认识基本类型和指针。

所以需要一个**C 导出层（C ABI facade）**：

```
Python → ctypes → C ABI（基本类型/指针/结构体）→ Go 内部（丰富的 Go 类型）
```

设计原则：

1. **接口最小化**：导出少量简单函数，复杂逻辑留在 Go 内部
2. **类型扁平化**：用基本类型、指针、长度传递数据
3. **生命周期明确**：谁分配谁释放，用显式释放函数
4. **错误码化**：用返回码 + 错误串，而非 Go 的 error 直接暴露

---

## 14.2 数据传递模式

### 14.2.1 模式一：基本类型直接传

最简单的情况：int、float、bool。

```go
//export Multiply
func Multiply(a C.double, b C.double) C.double {
    return C.double(float64(a) * float64(b))
}
```

Python：

```python
lib.Multiply.argtypes = [ctypes.c_double, ctypes.c_double]
lib.Multiply.restype = ctypes.c_double
print(lib.Multiply(3.0, 4.0))  # 12.0
```

### 14.2.2 模式二：字符串传递

```go
//export ProcessString
func ProcessString(input *C.char) *C.char {
    goStr := C.GoString(input)
    result := strings.ToUpper(goStr)
    return C.CString(result)  // 调用方必须释放
}

//export FreeString
func FreeString(p *C.char) {
    C.free(unsafe.Pointer(p))
}
```

Python：

```python
lib.ProcessString.argtypes = [ctypes.c_char_p]
lib.ProcessString.restype = ctypes.c_void_p
lib.FreeString.argtypes = [ctypes.c_void_p]

ptr = lib.ProcessString(b"hello")
result = ctypes.string_at(ptr).decode()
lib.FreeString(ptr)
print(result)  # HELLO
```

**关键**：Go 用 `C.CString` 分配的内存，Python 必须调用 `FreeString` 释放。

### 14.2.3 模式三：二进制 buffer 传递

处理网络包、文件内容等二进制数据，用「指针 + 长度」：

```go
//export ProcessBytes
func ProcessBytes(data *C.char, length C.int) C.int {
    // C.GoBytes 把 C 内存拷贝成 Go []byte
    goBytes := C.GoBytes(unsafe.Pointer(data), length)
    // 处理...
    return C.int(len(goBytes))
}
```

Python 传 bytes：

```python
lib.ProcessBytes.argtypes = [ctypes.c_char_p, ctypes.c_int]
data = b"\x01\x02\x03\x04"
result = lib.ProcessBytes(data, len(data))
```

> **性能提示**：`C.GoBytes` 会拷贝数据。对大 buffer，可以考虑用 `unsafe.Slice` 直接把 C 内存当 Go slice（零拷贝），但要确保调用期间 C 内存有效，且 Go 侧不保存引用。

### 14.2.4 模式四：数组传递

数值数组用「指针 + 长度」：

```go
//export SumArray
func SumArray(arr *C.double, length C.int) C.double {
    goSlice := unsafe.Slice((*float64)(unsafe.Pointer(arr)), int(length))
    var sum float64
    for _, v := range goSlice { sum += v }
    return C.double(sum)
}
```

Python：

```python
import numpy as np
arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
lib.SumArray.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
lib.SumArray.restype = ctypes.c_double
result = lib.SumArray(arr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), len(arr))
```

numpy 的 `ctypes.data_as` 直接给出底层指针，**零拷贝**。这是 Python↔Go 高效传数组的方式。

### 14.2.5 模式五：结构体传递

C 结构体贯穿 C/Go/Python 三层：

Go 侧（在 preamble 定义 C 结构体）：

```go
package main

/*
typedef struct {
    int port;
    int status;
    const char* service;
} ScanResult;
*/
import "C"

//export FillResult
func FillResult(r *C.ScanResult) {
    r.port = 80
    r.status = 200
    r.service = C.CString("http")  // 注意释放
}
```

Python 侧：

```python
class ScanResult(ctypes.Structure):
    _fields_ = [
        ('port', ctypes.c_int),
        ('status', ctypes.c_int),
        ('service', ctypes.c_char_p),
    ]

r = ScanResult()
lib.FillResult(ctypes.byref(r))
print(r.port, r.status, r.service)
```

---

## 14.3 句柄（Handle）模式：管理 Go 对象生命周期

这是最实用的模式。Go 内部有复杂对象（如扫描器实例、模型、连接池），Python 通过整数句柄操作它。

### 14.3.1 设计

Go 侧：维护一个全局 map，句柄 → Go 对象指针。

```go
package main

/*
#include <stdlib.h>
*/
import "C"
import (
    "sync"
    "sync/atomic"
)

type Scanner struct {
    Timeout int
    results []string
}

var (
    scanners = make(map[uint64]*Scanner)
    mu       sync.RWMutex
    nextID   uint64
)

//export NewScanner
func NewScanner(timeout C.int) C.ulonglong {
    id := atomic.AddUint64(&nextID, 1)
    mu.Lock()
    scanners[id] = &Scanner{Timeout: int(timeout)}
    mu.Unlock()
    return C.ulonglong(id)
}

//export ScannerScan
func ScannerScan(handle C.ulonglong, target *C.char) C.int {
    mu.RLock()
    s := scanners[uint64(handle)]
    mu.RUnlock()
    if s == nil {
        return -1  // 无效句柄
    }
    // 执行扫描...
    s.results = append(s.results, C.GoString(target))
    return C.int(len(s.results))
}

//export FreeScanner
func FreeScanner(handle C.ulonglong) {
    mu.Lock()
    delete(scanners, uint64(handle))
    mu.Unlock()
}

func main() {}
```

Python 侧包装：

```python
import ctypes

class GoScanner:
    def __init__(self, lib, timeout=500):
        self.lib = lib
        lib.NewScanner.restype = ctypes.c_ulonglong
        lib.NewScanner.argtypes = [ctypes.c_int]
        lib.ScannerScan.argtypes = [ctypes.c_ulonglong, ctypes.c_char_p]
        lib.ScannerScan.restype = ctypes.c_int
        lib.FreeScanner.argtypes = [ctypes.c_ulonglong]
        self.handle = lib.NewScanner(timeout)

    def scan(self, target):
        return self.lib.ScannerScan(self.handle, target.encode())

    def close(self):
        if self.handle:
            self.lib.FreeScanner(self.handle)
            self.handle = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()

# 使用
lib = ctypes.CDLL("./libgo.so")
with GoScanner(lib, 500) as scanner:
    count = scanner.scan("192.168.1.1")
    print(f"已扫描 {count} 项")
# 自动释放
```

句柄模式的优点：
- Go 对象不用暴露给 Python（类型安全）
- Python 用熟悉的面向对象接口
- 生命周期通过 `close()` 明确管理（支持上下文管理器）

---

## 14.4 Go runtime 与线程：关键问题

### 14.4.1 Go runtime 自动初始化

当 `.so` 被加载时，Go runtime 会自动初始化。但如果 Python 从**非 Go 创建的线程**调用 Go 函数，需要注意：

Go 调度器会把 C/Python 线程附加到 Go runtime。cgo 会自动处理大部分情况，但有几点注意：

### 14.4.2 长时间阻塞调用

如果 Go 函数阻塞很久（如网络等待），可能占用系统线程。Go runtime 会扩展线程池，但如果大量 Python 线程同时调用 Go，可能导致线程爆炸。

**建议**：在 Go 侧用 goroutine 做并发，Python 侧少量调用即可（不要 Python 开 1000 个线程调 Go）。

### 14.4.3 回调与 GIL

如果 Go 需要回调 Python 函数（通过 `//export` 的函数指针），要注意：
- Go 调用 C 函数指针 → 该函数指针调用 Python → 需要 GIL
- Python 侧回调要用 `CFUNCTYPE` 并保持引用（第 4 章）
- 避免死锁（Go 持有锁时回调 Python，Python 又要调 Go）

### 14.4.4 信号处理

Go runtime 会安装信号处理器。如果在 Python 进程里加载 Go .so，可能干扰 Python 的信号处理（如 SIGINT）。这是一个已知的坑，测试时要注意。

---

## 14.5 错误处理模式

Go 的 `error` 不能直接穿过 C ABI。常用模式：

### 14.5.1 错误码 + 错误消息

```go
var lastError string

//export GoOperation
func GoOperation(input *C.char) C.int {
    goInput := C.GoString(input)
    if goInput == "" {
        lastError = "输入不能为空"
        return -1  // 错误码
    }
    // 处理...
    return 0  // 成功
}

//export GetLastError
func GetLastError() *C.char {
    return C.CString(lastError)  // 调用方释放
}
```

Python：

```python
rc = lib.GoOperation(b"")
if rc != 0:
    ptr = lib.GetLastError()
    err = ctypes.string_at(ptr).decode()
    lib.FreeString(ptr)
    raise RuntimeError(err)
```

### 14.5.2 返回结构体（含错误码和数据）

更复杂但更规范的做法：用输出参数返回数据，返回值表示错误码。

---

## 14.6 实战：构建完整的 Python 包包装 Go 引擎

综合前面知识，做一个完整项目：`gosec` —— Go 写的安全分析引擎，Python 包包装。

### 14.6.1 Go 侧（libgosec.go）

```go
package main

/*
#include <stdlib.h>
*/
import "C"
import (
    "crypto/sha256"
    "encoding/hex"
    "strings"
    "sync"
    "sync/atomic"
    "unsafe"
)

type Analyzer struct {
    signatures []string
}

var (
    analyzers = make(map[uint64]*Analyzer)
    mu        sync.RWMutex
    nextID    uint64
)

//export NewAnalyzer
func NewAnalyzer() C.ulonglong {
    id := atomic.AddUint64(&nextID, 1)
    mu.Lock()
    analyzers[id] = &Analyzer{signatures: []string{"malware", "Trojan", "backdoor"}}
    mu.Unlock()
    return C.ulonglong(id)
}

//export AnalyzeFile
func AnalyzeFile(handle C.ulonglong, data *C.char, length C.int) *C.char {
    mu.RLock()
    a := analyzers[uint64(handle)]
    mu.RUnlock()
    if a == nil { return C.CString("") }

    bytes := C.GoBytes(unsafe.Pointer(data), length)
    hash := sha256.Sum256(bytes)
    hashHex := hex.EncodeToString(hash[:])

    // 简单特征匹配（演示）
    text := strings.ToLower(string(bytes))
    found := []string{}
    for _, sig := range a.signatures {
        if strings.Contains(text, sig) { found = append(found, sig) }
    }
    result := hashHex + "|" + strings.Join(found, ",")
    return C.CString(result)  // 调用方释放
}

//export FreeString
func FreeString(p *C.char) { C.free(unsafe.Pointer(p)) }

//export FreeAnalyzer
func FreeAnalyzer(handle C.ulonglong) {
    mu.Lock(); delete(analyzers, uint64(handle)); mu.Unlock()
}

func main() {}
```

编译：

```bash
go build -buildmode=c-shared -o libgosec.so libgosec.go
```

### 14.6.2 Python 包装层（gosec/__init__.py）

```python
import ctypes
import os
from typing import List, Tuple

_lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "libgosec.so"))

_lib.NewAnalyzer.restype = ctypes.c_ulonglong
_lib.AnalyzeFile.argtypes = [ctypes.c_ulonglong, ctypes.c_char_p, ctypes.c_int]
_lib.AnalyzeFile.restype = ctypes.c_void_p
_lib.FreeString.argtypes = [ctypes.c_void_p]
_lib.FreeAnalyzer.argtypes = [ctypes.c_ulonglong]


class Analyzer:
    """Go 驱动的安全分析器"""
    def __init__(self):
        self._handle = _lib.NewAnalyzer()

    def analyze(self, data: bytes) -> Tuple[str, List[str]]:
        ptr = _lib.AnalyzeFile(self._handle, data, len(data))
        if not ptr:
            raise RuntimeError("分析失败")
        result = ctypes.string_at(ptr).decode()
        _lib.FreeString(ptr)
        parts = result.split("|", 1)
        signatures = parts[1].split(",") if parts[1] else []
        return parts[0], signatures

    def close(self):
        if self._handle:
            _lib.FreeAnalyzer(self._handle)
            self._handle = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
```

### 14.6.3 使用

```python
from gosec import Analyzer

with Analyzer() as analyzer:
    data = open("sample.bin", "rb").read()
    sha, signals = analyzer.analyze(data)
    print(f"SHA256: {sha}")
    print(f"命中特征: {signals}")
```

这个例子完整展示了：Go 引擎（高性能哈希+匹配）→ C ABI → Python 包装（友好 API）。

---

## 14.7 Python↔Go 混合的常见陷阱

| 陷阱 | 后果 | 避免方法 |
|------|------|---------|
| 忘记释放 C.CString | 内存泄漏 | 成对调用 FreeString |
| 传含 Go 指针的结构给 C | panic | 只传 C 类型或基本类型 |
| 返回 Go 内存指针给 Python | 悬垂指针/GC 问题 | 用 C.CString 拷贝或句柄模式 |
| Python 多线程大量调 Go | 线程爆炸 | Go 侧并发，Python 少调用 |
| 结构体布局不一致 | 数据错位 | 用同一个头文件定义 |
| 字符串含 `\0` | 被截断 | 用指针+长度传二进制 |
| Go runtime 信号冲突 | 干扰 Python 信号处理 | 测试 SIGINT 处理 |

---

## 14.8 本章总结

| 知识点 | 内容 |
|--------|------|
| 导出层设计 | 接口最小化、类型扁平化、生命周期明确、错误码化 |
| 数据传递 | 基本类型、字符串、二进制 buffer、数组、结构体 |
| 句柄模式 | 全局 map + 整数句柄，管理 Go 对象生命周期 |
| Go runtime | 自动初始化；注意阻塞、回调、信号 |
| 错误处理 | 错误码 + 错误消息（GetLastError） |
| 实战 | gosec：Go 引擎 + Python 包装 |
| 陷阱 | 内存释放、指针规则、结构体布局、字符串截断 |

---

## 本章练习

1. 设计并实现一个导出层：Go 函数接收一个整数数组，返回排序后的数组（用指针+长度）。
2. 用句柄模式实现一个"配置管理器"：Python 创建、修改、销毁 Go 配置对象。
3. 实现错误码模式：Go 函数可能失败，Python 侧正确读取错误消息并抛异常。
4. 用 numpy 的 `ctypes.data_as` 零拷贝传数组给 Go，验证性能。
5. 把 gosec 例子扩展：支持添加自定义特征、返回详细匹配位置。
6. 测试：Python 多线程调用 Go 函数，观察是否稳定，测量线程数影响。

---

**下一章预告**：第四卷收官——**gopy 与其他方案**。除了 cgo 共享库，还有哪些 Python↔Go 混合方案？gopy 自动生成绑定、RPC/进程间通信（HTTP/gRPC）、嵌入式方案各有何优劣？我们会做一个完整对比，帮你根据场景选型。
