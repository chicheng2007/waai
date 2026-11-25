# 第 28 章 Rust 操作 MySQL

## 本章目标

读完这一章，你将能够：

- 用 sqlx 异步操作 MySQL
- 理解 Rust 数据库库的特点（sqlx / diesel）
- 用参数化查询防注入
- 理解异步与连接池

---

## 28.1 为什么用 Rust 操作 MySQL

Rust 在系统语言卷里我们讲过——**内存安全 + 高性能**。用它操作 MySQL 的优势：

- 无 GC，性能接近 C/C++
- 编译期内存安全，没有段错误、UAF
- 现代异步生态（tokio），高并发
- 类型安全，编译期就能发现很多错误

适合：下一代安全工具、高性能数据库中间件、AI 服务的数据层。

---

## 28.2 Rust 的 MySQL 库

| 库 | 类型 | 特点 |
|----|------|------|
| sqlx | 异步 | 纯 Rust、支持异步、编译期检查 SQL（可选）、流行 |
| diesel | ORM | 类型安全的 ORM、同步为主、成熟 |
| mysql_async | 异步 | 纯 Rust 异步驱动 |

本章重点讲 **sqlx**——最流行、最现代。

---

## 28.3 用 sqlx 连接和查询

创建项目：

```bash
cargo new rust_mysql_demo
cd rust_mysql_demo
```

Cargo.toml：

```toml
[dependencies]
sqlx = { version = "0.7", features = ["mysql", "runtime-tokio", "tls-rustls"] }
tokio = { version = "1", features = ["full"] }
```

### 基本查询

```rust
use sqlx::mysql::MySqlPoolOptions;
use sqlx::Row;

#[tokio::main]
async fn main() -> Result<(), sqlx::Error> {
    // 1. 创建连接池
    let pool = MySqlPoolOptions::new()
        .max_connections(5)
        .connect("mysql://secapp:密码@localhost:3306/security_lab")
        .await?;

    // 2. 查询
    let rows = sqlx::query("SELECT id, ip, status FROM hosts")
        .fetch_all(&pool)
        .await?;

    // 3. 处理结果
    for row in rows {
        let id: i32 = row.get("id");
        let ip: String = row.get("ip");
        let status: String = row.get("status");
        println!("{}: {} - {}", id, ip, status);
    }

    Ok(())
}
```

关键点：

- `#[tokio::main]` 把 main 变成异步
- `MySqlPoolOptions` 创建连接池
- `sqlx::query(...).fetch_all(&pool).await?` 异步查询
- `row.get("列名")` 取值，类型标注决定类型

---

## 28.4 参数化查询（防注入）

```rust
// 安全：用 bind 传参数
let ip = "192.168.1.10";
let row = sqlx::query("SELECT id, status FROM hosts WHERE ip = ?")
    .bind(ip)
    .fetch_one(&pool)
    .await?;
```

`?` 是占位符，`bind()` 传值——和 Python 的 `%s`、C 的 prepare 一样，SQL 和数据分离，防注入（第 19 章）。

sqlx 还支持**编译期检查** SQL（需要 DATABASE_URL 环境变量），写错的 SQL 在编译时就能发现——这是 sqlx 的独特优势。

---

## 28.5 增删改

```rust
// 插入
sqlx::query("INSERT INTO hosts (ip, os, status) VALUES (?, ?, ?)")
    .bind("10.0.0.10")
    .bind("Ubuntu")
    .bind("UP")
    .execute(&pool)
    .await?;

// 更新
sqlx::query("UPDATE hosts SET status = ? WHERE ip = ?")
    .bind("DOWN")
    .bind("10.0.0.10")
    .execute(&pool)
    .await?;

// 删除
sqlx::query("DELETE FROM hosts WHERE ip = ?")
    .bind("10.0.0.10")
    .execute(&pool)
    .await?;
```

`execute()` 返回执行结果，可看影响行数。

---

## 28.6 用结构体映射（query_as）

```rust
use sqlx::FromRow;

#[derive(Debug, FromRow)]
struct Host {
    id: i32,
    ip: String,
    os: Option<String>,   // 可空列用 Option
    status: String,
}

let hosts: Vec<Host> = sqlx::query_as::<_, Host>(
    "SELECT id, ip, os, status FROM hosts"
)
.fetch_all(&pool)
.await?;

for h in hosts {
    println!("{:?}", h);
}
```

`FromRow` 派生宏自动把查询结果映射到结构体。可空列用 `Option<T>` 对应 SQL 的 NULL——类型系统帮你正确处理空值。

---

## 28.7 事务

```rust
let mut tx = pool.begin().await?;

sqlx::query("UPDATE accounts SET balance=balance-? WHERE id=?")
    .bind(100).bind(1)
    .execute(&mut *tx)
    .await?;

sqlx::query("UPDATE accounts SET balance=balance+? WHERE id=?")
    .bind(100).bind(2)
    .execute(&mut *tx)
    .await?;

tx.commit().await?;  // 提交
// 出错时 tx 被 drop，自动回滚
```

Rust 的事务很优雅：如果中途出错返回 Err，`tx` 被 drop 时自动回滚（RAII 思想，呼应第 27 章）。

---

## 28.8 错误处理

```rust
#[tokio::main]
async fn main() {
    match run().await {
        Ok(_) => println!("成功"),
        Err(e) => eprintln!("错误: {}", e),
    }
}

async fn run() -> Result<(), Box<dyn std::error::Error>> {
    // ... 数据库操作
    Ok(())
}
```

或者用 `anyhow` crate 简化错误处理（系统语言卷讲过）：

```rust
use anyhow::Result;

async fn run() -> Result<()> {
    // ? 自动传播错误
    Ok(())
}
```

---

## 28.9 diesel（ORM，了解）

diesel 是类型安全的 ORM：

```rust
// 定义表（diesel::table! 宏）
diesel::table! {
    hosts (id) {
        id -> Integer,
        ip -> Varchar,
        status -> Varchar,
    }
}

// 查询（类型安全，编译期检查）
let results: Vec<Host> = hosts::table
    .filter(hosts::status.eq("UP"))
    .load::<Host>(&mut conn)?;
```

diesel 的优点是编译期类型安全——查询写错编译不过。缺点是需要 schema 生成、学习曲线陡。小项目用 sqlx 更灵活，大项目 diesel 的类型安全有价值。

---

## 28.10 Rust 操作 MySQL 的适用场景

- **安全工具**：Rust 写的扫描器、日志分析器存结果到 MySQL
- **AI 服务**：高性能数据层，异步读取特征数据
- **数据库中间件**：代理、连接池、分库分表工具
- **高并发服务**：tokio 异步 + 连接池，扛高并发

---

## 28.11 本章总结

| 知识点 | 内容 |
|--------|------|
| Rust 优势 | 内存安全 + 高性能 + 异步生态 |
| sqlx | 异步 MySQL 库；连接池；编译期 SQL 检查 |
| 查询 | `query().fetch_all().await`；`row.get()` |
| 参数化 | `?` + `bind()`；防注入（呼应第19章） |
| 映射 | `FromRow` 派生；Option 对应 NULL |
| 事务 | `pool.begin()` + `commit()`；drop 自动回滚 |
| diesel | 类型安全 ORM；编译期检查 |
| 适用 | 安全工具、AI 数据层、高并发服务 |

---

## 本章练习

1. 用 sqlx 连接 MySQL，查询 hosts 表并打印。
2. 用 `bind()` 做参数化查询，验证注入输入不生效。
3. 用 `query_as` 把结果映射到结构体，处理可空列。
4. 写一个事务示例，中途出错观察自动回滚。
5. 配置连接池的 `max_connections`，理解为什么要用连接池。
6. 思考：Rust 的事务为什么 drop 时自动回滚？和第 27 章的 RAII 有什么关系？
7. 思考：sqlx 的编译期 SQL 检查有什么价值？

---

**下一章预告**：用 Go 操作 MySQL——Go 的 database/sql + 驱动，简洁的并发数据库访问。Go 是云原生安全工具的主力语言，很多安全平台用 Go 写。
