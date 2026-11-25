# 第 3 章 Rust 基础语法

## 本章目标

- 掌握变量、数据类型、运算符
- 掌握函数和控制流
- 理解 Rust 的独特性（不可变默认、类型推断、`!` 宏）
- 理解 Rust 的内存安全体现在细节中

---

## 3.1 变量与可变性

### 3.1.1 默认不可变

```rust
fn main() {
    let x = 5;
    // x = 6;   // 编译错误！x 默认不可变
    println!("x = {}", x);
    
    let mut y = 5;   // mut 让它可变
    y = 6;
    println!("y = {}", y);
}
```

> **设计哲学**：默认不可变，让你明确知道哪些变量会变。这减少了bug，也让并发更安全（不可变数据天然线程安全）。

### 3.1.2 类型推断

```rust
let x = 5;        // 编译器推断为 i32
let y = 3.14;     // f64
let z = "hello";  // &str

// 也可以显式标注
let a: u64 = 100;
let b: f32 = 2.5;
```

### 3.1.3 变量遮蔽（Shadowing）

```rust
let x = 5;
let x = x + 1;      // 遮蔽（shadow）前一个 x
let x = "hello";    // 甚至能改变类型！
println!("{}", x);  // hello
```

遮蔽和 `mut` 不同：遮蔽是创建新变量，旧变量被隐藏。

---

## 3.2 数据类型

### 3.2.1 标量类型

```rust
// 整数
let a: i8 = -128;      // 有符号
let b: u8 = 255;       // 无符号
let c: i32 = -2147483648;  // 默认整数类型
let d: u64 = 18446744073709551615;

// 浮点
let e: f32 = 3.14;
let f: f64 = 3.14159265359;  // 默认浮点类型

// 布尔
let g: bool = true;

// 字符（Unicode，4字节）
let h: char = '中';
```

> **Rust 的安全**：整数溢出在 debug 模式会 panic（崩溃报错），release 模式会回绕。这比 C 的静默溢出安全——debug 阶段就能发现问题。
>
> ```rust
> let mut x: u8 = 255;
> // x += 1;   // debug 模式 panic: attempt to add with overflow
> ```

### 3.2.2 复合类型

**元组**：

```rust
let tup: (i32, f64, char) = (500, 6.4, 'A');
let (x, y, z) = tup;   // 解构
println!("{}", tup.0);  // 500
```

**数组**：

```rust
let arr = [1, 2, 3, 4, 5];
let first = arr[0];
let arr2 = [0; 10];   // 10个0

// 越界检查（运行时）
// let x = arr[10];   // panic: index out of bounds
```

> **安全**：Rust 数组越界会 panic，而不是像 C 那样悄悄越界写内存。这就是内存安全的体现。

---

## 3.3 函数

```rust
fn main() {
    let result = add(3, 5);
    println!("{}", result);
}

fn add(a: i32, b: i32) -> i32 {
    a + b   // 注意：没有分号！表达式返回值
}
```

要点：

- 用 `fn` 定义
- 参数必须标注类型
- 返回值用 `-> 类型`
- **最后一行不加分号**，作为返回值（加了分号就变成语句，返回 `()`）

```rust
fn no_return() {
    println!("hello");   // 返回单元类型 ()
}
```

---

## 3.4 控制流

### 3.4.1 if 表达式

```rust
let age = 18;
if age >= 18 {
    println!("成年");
} else if age >= 12 {
    println!("青少年");
} else {
    println!("儿童");
}

// if 是表达式，可以返回值
let status = if age >= 18 { "成年" } else { "未成年" };
```

> **注意**：Rust 的 `if` 条件必须是 `bool` 类型，不像 C 那样"非0即真"。
> ```rust
> // if 1 { }   // 编译错误！1 不是 bool
> ```

### 3.4.2 循环

```rust
// loop：无限循环
loop {
    if condition { break; }
}

// while
let mut i = 0;
while i < 10 {
    println!("{}", i);
    i += 1;
}

// for（最常用，安全）
let arr = [10, 20, 30];
for element in arr {
    println!("{}", element);
}

for i in 0..10 {   // 范围 0 到 9
    println!("{}", i);
}
```

> **Rust 的 for 循环更安全**：通过迭代器遍历，不会像 C 那样手动管理下标导致越界。

### 3.4.3 循环标签

```rust
'outer: loop {
    loop {
        if done { break 'outer; }   // 跳出指定循环
    }
}
```

---

## 3.5 注释与宏

```rust
// 单行注释

/* 块注释 */

/// 文档注释（生成文档）
fn add(a: i32, b: i32) -> i32 { a + b }

// 宏：println! 后面的 ! 表示宏，不是函数
println!("Hello");
```

---

## 3.6 实战：IP 分类程序

```rust
fn classify_ip(ip: &str) -> &str {
    if ip.starts_with("192.168.") || ip.starts_with("10.") {
        "内网IP"
    } else if ip.starts_with("127.") {
        "本地回环"
    } else {
        "公网IP"
    }
}

fn main() {
    let ips = ["192.168.1.1", "8.8.8.8", "127.0.0.1", "10.0.0.1"];
    for ip in ips {
        println!("{} -> {}", ip, classify_ip(ip));
    }
}
```

---

## 3.7 本章总结

| 知识点 | 内容 |
|--------|------|
| 变量 | 默认不可变，`mut` 可变；支持遮蔽 |
| 类型推断 | 编译器推断类型；默认 i32/f64 |
| 安全 | 整数溢出panic、数组越界panic、条件必须bool |
| 函数 | `fn`、`-> 返回值`；最后表达式无分号 |
| 控制流 | if 是表达式；loop/while/for；for 用迭代器最安全 |
| 宏 | `println!` 是宏 |

---

## 本章练习

1. 写一个程序判断端口号是否合法（1-65535）。
2. 用 for 循环打印九九乘法表。
3. 演示整数溢出在 debug 模式的 panic。
4. 用 if 表达式根据分数返回等级。
5. 思考：Rust 的默认不可变和数组越界检查如何提升安全性？

---

**下一章预告**：进入 Rust 最核心的部分——所有权、借用与生命周期。这是 Rust 内存安全的基石，也是学习的最大难点。
