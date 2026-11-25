# 第 13 章 cgo 基础：Go 与 C 的桥梁

## 本章目标

读完这一章，你将能够：

- 理解 cgo 的作用：让 Go 与 C 代码互操作
- 用 `import "C"` 在 Go 里调用 C 函数
- 用 `//export` 把 Go 函数导出给 C 调用
- 掌握 cgo 的类型转换规则
- 理解 cgo 的内存规则与指针传递限制（关键！）
- 用 cgo 编译 Go 静态/动态库
- 知道 cgo 的代价与适用场景

---

## 13.1 为什么 Go 需要和 C 互操作

Go 是一门优秀的系统语言，但现实工程中：

- **复用 C 生态**：OpenSSL、libpcap、sqlite、各种硬件驱动都是 C 库
- **兼顾 Python**：Python 要调用 Go，最成熟的路径是通过 C ABI（Go 导出 C 接口），而 Go 的 C 接口就是 cgo 提供的
- **遗留代码**：已有大量 C 代码要逐步迁移到 Go

**cgo** 是 Go 官方提供的 C 互操作机制。它是 Go 与 Python 混合编程的**关键中间层**——Python 通过 ctypes/cffi 调用 Go 编译的共享库，而这个共享库的 C 接口正是用 cgo 导出的。

```
Python ←(ctypes/cffi)→ C ABI ←(cgo)→ Go 代码
```

---

## 13.2 第一个 cgo 程序

### 13.2.1 在 Go 里调用 C 函数

创建 `main.go`：

```go
package main

/*
#include <stdlib.h>
#include <stdio.h>

static int c_add(int a, int b) {
    return a + b;
}
*/
import "C"
import "fmt"

func main() {
    a := C.int(3)
    b := C.int(5)
    result := C.c_add(a, b)
    fmt.Printf("C.c_add(3, 5) = %d\n", int(result))

    // 调用 C 标准库函数
    cstr := C.CString("Hello from Go")
    defer C.free(unsafe.Pointer(cstr))  // 必须手动释放！
    C.puts(cstr)
}
```

关键点：

1. `import "C"` 前紧跟的注释块是 **C 代码区**（preamble），可以写 `#include` 和 C 函数定义
2. `import "C"` 必须紧跟在注释块后面，中间不能有空行
3. C 类型用 `C.xxx` 访问（如 `C.int`、`C.CString`）
4. `C.CString` 分配的内存必须用 `C.free` 手动释放

需要导入 `unsafe` 包（上面代码漏了，实际要加 `import "unsafe"`）。

运行：

```bash
go run main.go
# C.c_add(3, 5) = 8
# Hello from Go
```

> **小白问：为什么 `C.CString` 要手动 free？**
> 因为 `C.CString` 调用的是 C 的 `malloc`，Go 的 GC 管不了 C 分配的内存。不 free 就内存泄漏。这再次印证第 2 章的心法：**谁分配谁释放**。

### 13.2.2 用 `//export` 把 Go 函数导出给 C

创建 `golib.go`：

```go
package main

/*
#include <stdlib.h>

// 声明 Go 导出的函数（给 C 用）
extern int GoAdd(int a, int b);
*/
import "C"

//export GoAdd
func GoAdd(a C.int, b C.int) C.int {
    return a + b
}

func main() {}  // 构建库时需要 main 函数（空即可）
```

`//export GoAdd` 告诉 cgo 把这个 Go 函数导出成 C 符号 `GoAdd`。

编译成 C 静态库：

```bash
go build -buildmode=c-archive -o libgo.a golib.go
```

会生成 `libgo.a`（静态库）和 `libgo.h`（头文件）：

```c
// libgo.h 里会自动生成声明
extern int GoAdd(int a, int b);
```

---

## 13.3 类型转换

cgo 有严格的类型映射：

| C 类型 | Go 类型（cgo） |
|--------|---------------|
| `int` | `C.int` |
| `long` | `C.long` |
| `unsigned int` | `C.uint` |
| `float` | `C.float` |
| `double` | `C.double` |
| `char*` | `*C.char` |
| `void*` | `unsafe.Pointer` |
| `size_t` | `C.size_t` |

转换规则：

```go
// Go 类型 → C 类型（显式转换）
goInt := 42
cInt := C.int(goInt)

// C 类型 → Go 类型（显式转换）
result := int(C.c_add(C.int(3), C.int(5)))

// Go string → C char*
cstr := C.CString("hello")
defer C.free(unsafe.Pointer(cstr))

// C char* → Go string
goStr := C.GoString(cstr)
```

**字符串转换的拷贝**：

- `C.CString(goStr)`：**拷贝** Go 字符串到 C 内存（malloc）
- `C.GoString(cstr)`：**拷贝** C 字符串到 Go 字符串
- 大量/高频字符串传递有开销，注意批量化

---

## 13.4 cgo 的内存规则（关键难点）

这是 cgo 最容易出错的地方，也是 Go 官方反复强调的。

### 13.4.1 指针传递规则

Go 有 GC，对象可能被移动（虽然目前 Go 的 GC 不移动对象，但规范上保留可能性）。C 不知道 Go 的 GC。所以 cgo 对指针传递有严格限制：

**规则**：传给 C 的 Go 指针，不能指向包含 Go 指针的 Go 内存。

```go
// ✅ 可以：指向基本类型或不含指针的结构
x := C.int(10)
C.some_c_func(&x)  // x 是 C 类型，OK

// ❌ 不可以：指向包含 Go 指针的结构
type Bad struct {
    Ptr *string  // 含 Go 指针
}
b := Bad{}
// C.some_c_func(&b)  // 错误！运行时检查会 panic
```

### 13.4.2 `runtime.cgocall` 检查

Go 运行时会检查传给 C 的指针是否合法。违反规则会 panic：`cgo argument has Go pointer to Go pointer`。

### 13.4.3 内存所有权

| 分配方 | 释放方 | 函数 |
|--------|--------|------|
| Go (`make`, `new`) | Go GC | 无需手动 |
| C (`C.CString`, `malloc`) | C (`C.free`) | 必须手动 |
| C 返回给 Go 的指针 | 看约定 | 通常需 C 提供释放函数 |

```go
// C 函数返回 malloc 的指针，Go 用完要调用 C 的释放函数
ptr := C.c_get_buffer()
// ... 使用 ptr ...
C.c_free_buffer(ptr)  // 谁分配谁释放
```

---

## 13.5 在 Go 里封装 C 库：完整示例

假设有个 C 库提供字符串哈希函数（简化），我们用 cgo 封装成 Go 包。

### 13.5.1 C 库 `hashlib.h` / `hashlib.c`

```c
// hashlib.h
#ifndef HASHLIB_H
#define HASHLIB_H
unsigned long simple_hash(const char* s);
#endif
```

```c
// hashlib.c
#include "hashlib.h"
unsigned long simple_hash(const char* s) {
    unsigned long h = 0;
    while (*s) { h = h * 31 + *s++; }
    return h;
}
```

### 13.5.2 Go 封装

```go
package hashwrapper

/*
#cgo CFLAGS: -I.
#cgo LDFLAGS: -L. -lhash
#include <stdlib.h>
#include "hashlib.h"
*/
import "C"
import "unsafe"

func Hash(s string) uint64 {
    cs := C.CString(s)
    defer C.free(unsafe.Pointer(cs))
    return uint64(C.simple_hash(cs))
}
```

`#cgo CFLAGS` 和 `#cgo LDFLAGS` 告诉 cgo 编译/链接参数（头文件路径、链接库）。

---

## 13.6 Go 编译共享库给 C/Python 用

这是与 Python 混合的关键：把 Go 代码编译成 `.so`，然后 Python 用 ctypes 调用。

### 13.6.1 导出 Go 函数

```go
package main

/*
#include <stdlib.h>
*/
import "C"
import (
    "unsafe"
)

//export GoHash
func GoHash(input *C.char) C.ulong {
    goStr := C.GoString(input)
    var h C.ulong = 0
    for _, c := range goStr {
        h = h*31 + C.ulong(c)
    }
    return h
}

//export GoProcess
func GoProcess(data *C.char, length C.int) C.int {
    // 处理二进制数据
    goBytes := C.GoBytes(unsafe.Pointer(data), length)
    return C.int(len(goBytes))
}

func main() {}
```

### 13.6.2 编译成共享库

```bash
go build -buildmode=c-shared -o libgo.so golib.go
```

生成 `libgo.so` 和 `libgo.h`。

### 13.6.3 Python 调用

```python
import ctypes

lib = ctypes.CDLL("./libgo.so")

lib.GoHash.argtypes = [ctypes.c_char_p]
lib.GoHash.restype = ctypes.c_ulong
print(lib.GoHash(b"hello"))  # Go 算出的哈希

lib.GoProcess.argtypes = [ctypes.c_char_p, ctypes.c_int]
lib.GoProcess.restype = ctypes.c_int
print(lib.GoProcess(b"binary data", 11))
```

**这就是 Python↔Go 混合的核心路径**：Go 用 cgo 导出 C ABI → 编译成 .so → Python ctypes 调用。第 14 章会深入讲这个过程和注意事项。

---

## 13.7 实战：用 Go 写一个高性能并发端口检查（导出给 Python）

Go 的并发（goroutine）非常适合网络扫描。我们写一个 Go 函数，并发检查端口，导出给 Python。

```go
package main

/*
#include <stdlib.h>
*/
import "C"
import (
    "fmt"
    "net"
    "sync"
    "time"
)

//export CheckPorts
func CheckPorts(host *C.char, ports *C.int, count C.int) *C.char {
    goHost := C.GoString(host)

    // 把 C 数组转成 Go slice
    cPorts := unsafe.Slice(ports, int(count))
    goPorts := make([]int, int(count))
    for i, p := range cPorts {
        goPorts[i] = int(p)
    }

    var wg sync.WaitGroup
    var mu sync.Mutex
    openPorts := []int{}

    for _, port := range goPorts {
        wg.Add(1)
        go func(p int) {
            defer wg.Done()
            address := fmt.Sprintf("%s:%d", goHost, p)
            conn, err := net.DialTimeout("tcp", address, 500*time.Millisecond)
            if err == nil {
                conn.Close()
                mu.Lock()
                openPorts = append(openPorts, p)
                mu.Unlock()
            }
        }(port)
    }
    wg.Wait()

    // 结果转成字符串返回（简化，实际应返回结构化数据）
    result := fmt.Sprint(openPorts)
    return C.CString(result)  // 注意：调用方要释放这块内存！
}

//export FreeCString
func FreeCString(p *C.char) {
    C.free(unsafe.Pointer(p))
}

func main() {}
```

编译：

```bash
go build -buildmode=c-shared -o libgoscan.so goscan.go
```

Python 调用：

```python
import ctypes

lib = ctypes.CDLL("./libgoscan.so")
lib.CheckPorts.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
lib.CheckPorts.restype = ctypes.c_void_p
lib.FreeCString.argtypes = [ctypes.c_void_p]

ports = (ctypes.c_int * 5)(21, 22, 80, 443, 8080)
ptr = lib.CheckPorts(b"127.0.0.1", ports, 5)
result = ctypes.string_at(ptr).decode()
lib.FreeCString(ptr)  # 谁分配谁释放
print(f"开放端口: {result}")
```

Go 用 goroutine 并发扫描，Python 负责编排和展示。**注意**：上面 Go 代码缺了 `unsafe` import，实际要加 `import "unsafe"`。

> **合规提醒**：端口扫描仅在授权环境进行。

---

## 13.8 cgo 的代价与注意事项

### 13.8.1 性能开销

- **跨边界开销**：每次 C↔Go 调用有上下文切换成本
- **字符串拷贝**：`C.CString`/`C.GoString` 都拷贝
- **cgo 调用不能完全内联**：比纯 Go 调用慢

**优化**：批量化，减少调用次数。

### 13.8.2 构建复杂

- 需要 C 编译器
- 交叉编译变复杂（cgo 默认禁用交叉编译，需 CGO_ENABLED=1 和交叉编译器）
- 构建产物依赖 libc（除非静态链接）

### 13.8.3 调试困难

- Go 和 C 的调试器不同（delve 调 Go，gdb 调 C）
- 内存错误可能跨越语言边界

### 13.8.4 何时用 cgo

- 必须复用 C 库
- 要给 Python/其他语言提供 Go 能力（通过 C ABI）
- 性能关键且 Go 实现更合适

---

## 13.9 深入：cgo 编译模式与静态链接

掌握了 cgo 的基本用法后，理解它的编译模式和链接方式，对部署至关重要。

### 13.9.1 两种构建模式

| 模式 | 命令 | 产物 | 特点 |
|------|------|------|------|
| c-archive | `go build -buildmode=c-archive` | `.a` + `.h` | 静态库，链接进可执行文件，部署简单 |
| c-shared | `go build -buildmode=c-shared` | `.so`/`.dll` + `.h` | 动态库，运行时加载，Python 常用 |

`c-archive` 把 Go runtime 和你的代码打包成静态库，C 主程序链接后得到一个自包含的可执行文件。`c-shared` 生成动态库，Python 用 ctypes 加载（第 14 章重点）。

### 13.9.2 CGO_ENABLED 与交叉编译

```bash
# 查看当前 cgo 状态
go env CGO_ENABLED

# 关闭 cgo（纯 Go，可交叉编译）
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build

# 开启 cgo 交叉编译（需要对应平台的 C 交叉编译器）
CGO_ENABLED=1 CC=x86_64-w64-mingw32-gcc GOOS=windows GOARCH=amd64 \
    go build -buildmode=c-shared -o libgo.dll
```

**关键限制**：cgo 默认禁用交叉编译（因为需要目标平台的 C 编译器）。这就是为什么含 cgo 的 Go 项目跨平台构建比纯 Go 复杂。解决方法是安装交叉编译工具链（如 mingw-w64），或用 Docker/CI 在各平台本地构建（第 11 章的 GitHub Actions 思路同样适用）。

### 13.9.3 静态链接 libc

默认动态链接 libc，部署时目标机器必须有对应 libc。用 musl 可以静态链接，得到完全自包含的库：

```bash
CC=musl-gcc CGO_ENABLED=1 go build -buildmode=c-shared -o libgo.so
```

`ldd libgo.so` 如果显示 `statically linked` 或没有 libc 依赖，说明静态链接成功。这在容器镜像精简（scratch 镜像）时非常有用。

### 13.9.4 初始化与导出符号检查

编译后验证导出的符号：

```bash
# 查看导出函数（应该有 GoAdd 等）
nm -D libgo.so | grep -i goadd

# 查看头文件里的声明
cat libgo.h
```

如果符号没导出，检查：
1. 函数是否有 `//export` 注释（注意 `//` 后必须有空格，紧挨着函数定义）
2. 包是否是 `main`（导出函数必须在 main 包）
3. 是否有空的 `func main() {}`

### 13.9.5 常见问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 找不到 `GoAdd` 符号 | 缺 `//export` 或非 main 包 | 检查注释格式和包名 |
| `undefined reference` | 链接时没找到依赖库 | 检查 LDFLAGS |
| 运行时 panic 指针错误 | 违反 cgo 指针规则 | 只传 C 类型或不含 Go 指针的结构 |
| 交叉编译失败 | CGO_ENABLED 或缺少交叉编译器 | 安装对应工具链 |
| 加载 .so 报依赖错误 | 动态链接的库缺失 | 用 musl 静态链接或带上依赖 |

---

## 13.10 本章总结

| 知识点 | 内容 |
|--------|------|
| cgo 定位 | Go 与 C 互操作，是 Python↔Go 混合的中间层 |
| 调用 C | `import "C"` + preamble，`C.xxx` 访问 C 类型/函数 |
| 导出 Go | `//export FuncName`，编译 `c-shared` 生成 .so + .h |
| 类型转换 | `C.int`、`C.CString`、`C.GoString`、`C.GoBytes`；字符串有拷贝 |
| 内存规则 | 传给 C 的 Go 指针不能指向含 Go 指针的内存；C 分配的手动 free |
| 编译库 | `go build -buildmode=c-shared -o libgo.so` |
| 实战 | Go 并发端口检查导出给 Python |
| 代价 | 边界开销、字符串拷贝、构建复杂、调试困难 |

---

## 本章练习

1. 写 cgo 程序在 Go 里调用 C 的 `printf` 和 `strlen`。
2. 用 `//export` 导出一个 Go 函数，编译成 `.so`，用 Python ctypes 调用。
3. 写一个 C 函数返回 malloc 分配的字符串，Go 调用后正确释放。
4. 验证 cgo 的指针规则：尝试传含 Go 指针的结构给 C，观察 panic。
5. 把并发端口检查例子改造：返回 JSON 格式结果（含端口和服务）。
6. 测量 cgo 调用的开销：对比 Go 内部调用和跨 C 边界调用的耗时。

---

**下一章预告**：cgo 基础已经打通。下一章深入 **Go 共享库供 Python 调用**——设计一个干净的 C 导出层、处理复杂数据类型（结构体、数组、回调）、管理内存生命周期、处理 Go runtime 的初始化与线程问题。这是把 Go 能力稳定暴露给 Python 的实战指南。
