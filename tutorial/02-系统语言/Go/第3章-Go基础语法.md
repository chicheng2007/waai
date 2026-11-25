# 第 3 章 Go 基础语法

## 本章目标

- 掌握变量、数据类型、运算符
- 掌握函数和控制流
- 理解 Go 的独特性（`:=`、多返回值、无隐式转换）
- 理解 Go 的简洁设计哲学

---

## 3.1 变量

### 3.1.1 声明方式

```go
package main

import "fmt"

func main() {
    // 方式一：var 声明
    var a int = 10
    var b = 20        // 类型推断
    var c string      // 零值 ""
    
    // 方式二：短变量声明（最常用，函数内）
    d := 30
    
    fmt.Println(a, b, c, d)
}
```

`:=` 是 Go 的特色，简洁地声明并初始化变量。只能在函数内使用。

### 3.1.2 多变量声明

```go
var x, y int = 1, 2
var a, b = 3, "hello"
m, n := 5, 6

// 常量
const Pi = 3.14159
const (
    StatusOK = 200
    StatusNotFound = 404
)
```

### 3.1.3 零值

Go 的变量声明后自动初始化为"零值"：

| 类型 | 零值 |
|------|------|
| int | 0 |
| float | 0.0 |
| string | "" |
| bool | false |
| pointer | nil |

> 这消除了 C 里"未初始化变量"的隐患。

---

## 3.2 数据类型

### 3.2.1 基本类型

```go
// 整数
var a int = 42           // 平台相关
var b int8 = -128
var c uint64 = 100

// 浮点
var d float32 = 3.14
var e float64 = 3.14159  // 默认

// 字符串
var s string = "hello"

// 布尔
var flag bool = true
```

### 3.2.2 严格类型（无隐式转换）

```go
var a int = 10
var b int64 = 20
// a + b   // 编译错误！不同类型不能直接运算
a + int(b)   // 必须显式转换
```

> **Go 的设计**：禁止隐式类型转换，避免 C 里因隐式转换导致的 bug 和漏洞。

---

## 3.3 函数

### 3.3.1 基本函数

```go
func add(a int, b int) int {
    return a + b
}

// 参数类型相同可简写
func add2(a, b int) int {
    return a + b
}
```

### 3.3.2 多返回值（Go 特色）

```go
func divide(a, b int) (int, error) {
    if b == 0 {
        return 0, fmt.Errorf("除数不能为零")
    }
    return a / b, nil
}

result, err := divide(10, 2)
if err != nil {
    fmt.Println("错误:", err)
} else {
    fmt.Println("结果:", result)
}
```

> **多返回值是 Go 错误处理的基础**——函数返回一个结果 + 一个 error，调用者必须处理。

### 3.3.3 命名返回值

```go
func split(sum int) (x, y int) {
    x = sum * 4 / 9
    y = sum - x
    return   // 裸返回，返回命名的 x, y
}
```

---

## 3.4 控制流

### 3.4.1 if

```go
if score >= 90 {
    fmt.Println("优秀")
} else if score >= 60 {
    fmt.Println("及格")
} else {
    fmt.Println("不及格")
}

// if 带初始化语句
if v := 10; v > 5 {
    fmt.Println(v)
}
```

> Go 的 `if` 条件必须是 bool，且不支持三元运算符（用 if-else 代替）。

### 3.4.2 switch

```go
switch port {
case 80:
    fmt.Println("HTTP")
case 443:
    fmt.Println("HTTPS")
default:
    fmt.Println("未知")
}

// 一个 case 多值
switch port {
case 80, 8080, 8000:
    fmt.Println("Web服务")
}
```

> Go 的 switch **默认不贯穿**（不用写 break），要贯穿用 `fallthrough`。这比 C 安全。

### 3.4.3 for（Go 只有 for）

```go
// 标准 for
for i := 0; i < 10; i++ {
    fmt.Println(i)
}

// while 风格
for condition {
    // ...
}

// 无限循环
for {
    break
}

// range 遍历
ports := []int{22, 80, 443}
for i, port := range ports {
    fmt.Println(i, port)
}
```

---

## 3.5 实战：端口分类

```go
package main

import (
    "fmt"
    "strconv"
)

func classifyPort(port int) string {
    switch {
    case port < 1 || port > 65535:
        return "非法端口"
    case port < 1024:
        return "知名端口"
    case port < 49152:
        return "注册端口"
    default:
        return "动态端口"
    }
}

func main() {
    for _, p := range []int{22, 80, 8080, 50000, 70000} {
        fmt.Printf("%d: %s\n", p, classifyPort(p))
    }
    _ = strconv.Itoa(80)  // 类型转化示例
}
```

---

## 3.6 数组与切片

Go 的数组和切片是两套东西，理解区别很重要：

```go
// 数组：长度固定，是值类型
var arr [5]int = [5]int{1, 2, 3, 4, 5}
arr2 := arr        // 复制整个数组！改 arr2 不影响 arr
arr2[0] = 99
fmt.Println(arr[0])   // 1，原数组没变

// 切片：长度可变，是引用类型（底层指向数组）
slice := []int{1, 2, 3}
slice2 := slice    // 共享底层数组！改 slice2 影响 slice
slice2[0] = 99
fmt.Println(slice[0])  // 99
```

### 3.6.1 切片的底层结构

切片是一个三元组描述符：

```
┌──────┬─────┬─────┐
│ ptr  │ len │ cap │
└──────┴─────┴─────┘
   │    当前长度 容量
   ↓
底层数组
```

```go
s := make([]int, 3, 5)   // len=3, cap=5
fmt.Println(len(s), cap(s))   // 3 5

s = append(s, 4, 5)   // 追加，len=5
// s = append(s, 6)   // 超过 cap，触发扩容（分配新数组，复制数据）

// 切片操作
s2 := s[1:3]   // 左闭右开，包含下标1、2
```

> **性能提示**：预分配容量 `make([]T, 0, expectedCap)` 能避免 append 时反复扩容，提升性能。处理大量数据时很重要。

### 3.6.2 map（字典）

```go
m := make(map[string]int)
m["HTTP"] = 80
m["HTTPS"] = 443

// 安全读取（检查 key 是否存在）
if port, ok := m["SSH"]; ok {
    fmt.Println(port)
}

// 删除
delete(m, "HTTP")

// 遍历
for key, value := range m {
    fmt.Println(key, value)
}
```

map 是无序的，遍历顺序每次可能不同。需要有序就先取出 key 排序。

---

## 3.7 本章总结

| 知识点 | 内容 |
|--------|------|
| 变量 | `var` 和 `:=`；零值自动初始化 |
| 类型 | 严格，无隐式转换 |
| 数组 | 长度固定，值类型，复制开销大 |
| 切片 | 长度可变，引用类型；ptr/len/cap |
| map | 字典；安全读取用 `v, ok` |
| 函数 | 多返回值；命名返回值 |
| 控制流 | if（初始化语句）、switch（不贯穿）、for（唯一循环） |
| range | 遍历数组/切片/map |

---

## 本章练习

1. 写程序判断一个年份是否闰年。
2. 用多返回值写一个函数：返回数组的最大值和最小值。
3. 用 switch 实现端口到服务名的映射。
4. 用 range 遍历字符串（注意中文字符，用 `[]rune`）。
5. 验证数组是值类型、切片是引用类型。
6. 用 map 统计一段文本中单词出现次数。
7. 思考：Go 只有 for 循环，相比 C 的 for/while/do-while 有什么优劣？

---

**下一章预告**：学习函数、方法与接口——Go 的面向对象实现方式（没有 class，用 struct + 方法 + 接口）。
