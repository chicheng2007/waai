# 第 7 章 泛型、trait 与集合

## 本章目标

- 掌握泛型（Generic）
- 掌握 trait（特征）与 trait 对象
- 掌握常用集合（Vec、HashMap、HashSet）
- 理解 Rust 的抽象机制

泛型和 trait 是 Rust 实现代码复用和抽象的核心工具。它们和 C++ 模板、Java 接口有相似之处，但设计更优雅、更安全。

---

## 7.1 泛型

### 7.1.1 泛型函数

```rust
fn largest<T: PartialOrd>(list: &[T]) -> &T {
    let mut largest = &list[0];
    for item in &list[1..] {
        if item > largest {
            largest = item;
        }
    }
    largest
}

let numbers = vec![34, 50, 25, 100];
let result = largest(&numbers);   // &100
```

`T: PartialOrd` 是 trait 约束，表示 T 必须支持比较。

### 7.1.2 泛型结构体

```rust
struct Point<T> {
    x: T,
    y: T,
}

let int_point = Point { x: 5, y: 10 };
let float_point = Point { x: 1.0, y: 2.0 };
```

### 7.1.3 泛型枚举（回顾 Option/Result）

```rust
enum Option<T> { Some(T), None }
enum Result<T, E> { Ok(T), Err(E) }
```

---

## 7.2 trait：定义行为

### 7.2.1 定义与实现

```rust
trait Analyze {
    fn analyze(&self) -> String;
    fn severity(&self) -> u8 {
        5   // 默认实现
    }
}

struct Malware { name: String }

impl Analyze for Malware {
    fn analyze(&self) -> String {
        format!("分析恶意软件: {}", self.name)
    }
    fn severity(&self) -> u8 {
        9   // 覆盖默认
    }
}
```

trait 类似 Java 的接口或 C++ 的纯虚类，定义"类型必须实现的行为"。

### 7.2.2 trait 约束

```rust
// 方式一：泛型约束
fn report<T: Analyze>(item: &T) {
    println!("{} (等级 {})", item.analyze(), item.severity());
}

// 方式二：impl Trait（更简洁）
fn report(item: &impl Analyze) {
    println!("{}", item.analyze());
}
```

### 7.2.3 trait 对象（动态分发）

```rust
fn report_all(items: &[Box<dyn Analyze>]) {
    for item in items {
        println!("{}", item.analyze());
    }
}

let items: Vec<Box<dyn Analyze>> = vec![
    Box::new(Malware { name: "WannaCry".into() }),
];
```

`dyn Analyze` 是 trait 对象，允许运行时多态（类似 C++ 虚函数）。

> **静态 vs 动态分发**：泛型（`impl Trait`）是静态分发，编译期确定类型，零开销；trait 对象是动态分发，运行时查表，有轻微开销。追求性能用泛型，需要异构集合用 trait 对象。

---

## 7.3 常用 trait

| trait | 作用 |
|-------|------|
| `Display` | 用户友好的字符串表示（`{}`） |
| `Debug` | 调试表示（`{:?}`），可 `#[derive]` |
| `Clone` | 克隆 |
| `Copy` | 按位复制 |
| `PartialEq` / `Eq` | 相等比较 |
| `PartialOrd` / `Ord` | 排序 |
| `Default` | 默认值 |
| `Iterator` | 迭代器 |

```rust
#[derive(Debug, Clone, PartialEq)]
struct IpAddr {
    octets: [u8; 4],
}
```

`#[derive]` 自动实现 trait，非常方便。

---

## 7.4 集合

### 7.4.1 Vec：动态数组

```rust
let mut v = Vec::new();
v.push(22);
v.push(80);

let v2 = vec![22, 80, 443];   // 宏创建

// 迭代
for port in &v {
    println!("{}", port);
}

// 常用方法
v.len();       // 长度
v.contains(&80);  // 是否包含
v.sort();      // 排序
v.dedup();     // 去重（需先排序）
```

### 7.4.2 HashMap：键值映射

```rust
use std::collections::HashMap;

let mut fails = HashMap::new();
fails.insert("192.168.1.1", 5);
fails.insert("10.0.0.1", 12);

// 访问
if let Some(count) = fails.get("10.0.0.1") {
    println!("{}", count);
}

// 遍历
for (ip, count) in &fails {
    println!("{}: {}", ip, count);
}

// 安全访问（不存在时插入默认值）
let entry = fails.entry("8.8.8.8").or_insert(0);
*entry += 1;
```

`entry API` 是 Rust 特有，高效且安全。

### 7.4.3 HashSet：集合

```rust
use std::collections::HashSet;

let mut blacklist = HashSet::new();
blacklist.insert("10.0.0.1");
blacklist.insert("192.168.1.100");

if blacklist.contains("10.0.0.1") {
    println!("黑名单 IP!");
}
```

HashSet 查找 O(1)，适合黑名单、去重。

### 7.4.4 迭代器（Iterator）

```rust
let ports = vec![22, 80, 443, 3389];

// 函数式风格
let known: Vec<_> = ports.iter()
    .filter(|&&p| p < 1024)
    .map(|&p| p)
    .collect();

// 求和
let sum: i32 = ports.iter().sum();

// 计数器
let count = ports.iter().count();
```

> **零成本抽象**：迭代器链编译后通常和手写的 for 循环性能一样，但代码更优雅。这是 Rust "零成本抽象"的典范。

---

## 7.5 实战：通用威胁检测器

```rust
use std::collections::HashMap;

trait Detect {
    fn name(&self) -> &str;
    fn indicator(&self) -> String;
}

struct PortScan { ip: String, count: usize }
struct Malware { hash: String }

impl Detect for PortScan {
    fn name(&self) -> &str { "端口扫描" }
    fn indicator(&self) -> String { format!("{} 扫描了 {} 个端口", self.ip, self.count) }
}

impl Detect for Malware {
    fn name(&self) -> &str { "恶意软件" }
    fn indicator(&self) -> String { format!("哈希: {}", self.hash) }
}

fn report<T: Detect>(items: &[T]) {
    for item in items {
        println!("[{}] {}", item.name(), item.indicator());
    }
}

fn main() {
    let scans = vec![
        PortScan { ip: "10.0.0.1".into(), count: 5000 },
    ];
    report(&scans);
    
    // 统计
    let mut stats: HashMap<&str, usize> = HashMap::new();
    *stats.entry("扫描").or_insert(0) += 1;
    println!("统计: {:?}", stats);
}
```

---

## 7.6 运算符重载与泛型实践

Rust 允许通过实现特定 trait 来重载运算符：

```rust
use std::ops::Add;

#[derive(Debug, Clone, Copy)]
struct Vector2D { x: f64, y: f64 }

impl Add for Vector2D {
    type Output = Vector2D;
    fn add(self, other: Vector2D) -> Vector2D {
        Vector2D { x: self.x + other.x, y: self.y + other.y }
    }
}

let a = Vector2D { x: 1.0, y: 2.0 };
let b = Vector2D { x: 3.0, y: 4.0 };
let c = a + b;   // 重载了 + 运算符
```

**可重载的运算符对应 trait**：

| 运算符 | trait |
|--------|-------|
| `+` | `Add` |
| `-` | `Sub` |
| `*` | `Mul` |
| `/` | `Div` |
| `==` | `PartialEq` |
| `<` | `PartialOrd` |
| `[]` | `Index` / `IndexMut` |

标准库的 `Vec`、`String` 能通过 `+` 拼接，就是实现了 `Add` trait。

---

## 7.7 Iterator 的惰性求值

Rust 的迭代器是**惰性**的——不消费就不执行：

```rust
let result: Vec<i32> = (1..1000000)
    .filter(|n| {
        println!("检查 {}", n);   // 只有被 filter 处理的才打印
        n % 2 == 0
    })
    .take(3)
    .collect();
// 只处理前几个元素就停了，不会遍历全部100万个！
```

`take(3)` 让迭代器只取 3 个满足条件的元素就停止。这是惰性求值带来的效率——不会做无用功。

> **性能启示**：迭代器链会被编译器优化成高效的循环，加上惰性求值，性能和手写循环相当，但代码更声明式、更易读。这就是"零成本抽象"的真实含义。

---

## 7.8 本章总结

| 知识点 | 内容 |
|--------|------|
| 泛型 | `fn f<T>`、`struct S<T>`；trait 约束 |
| trait | 定义行为；impl 实现；默认方法 |
| trait 对象 | `dyn Trait`，动态分发 |
| 常用 trait | Display/Debug/Clone/PartialEq 等；derive |
| 运算符重载 | 实现 Add/Sub/Index 等 trait |
| Vec | 动态数组；迭代器 |
| HashMap | 键值映射；entry API |
| HashSet | 集合；O(1) 查找 |
| 迭代器 | filter/map/collect；惰性求值；零成本抽象 |

---

## 本章练习

1. 写一个泛型函数求切片最大值。
2. 定义 trait `PortCheck`，为不同端口类型实现。
3. 用 HashMap 统计日志中每个 IP 的出现次数。
4. 用迭代器链过滤出高危端口。
5. 为自定义类型重载 `+` 运算符。
6. 验证迭代器的惰性求值。
7. 思考：泛型（静态分发）和 trait 对象（动态分发）各适合什么场景？

---

**下一章预告**：学习 Rust 并发编程——线程、消息传递、共享状态。Rust 的所有权系统在并发中发挥巨大威力，编译期就能防止数据竞争。
