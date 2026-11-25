# 第 29 章 Go 操作 MySQL

## 本章目标

读完这一章，你将能够：

- 用 Go 的 database/sql + go-sql-driver 操作 MySQL
- 理解 Go 的连接池配置
- 用参数化查询防注入
- 在并发场景中使用数据库（配合 goroutine）

---

## 29.1 为什么用 Go 操作 MySQL

Go 在系统语言卷里讲过——**简单、并发强、易部署**。用 Go 操作 MySQL 的优势：

- 标准库 `database/sql` 提供统一的数据库接口
- 原生并发（goroutine）适合高并发数据库访问
- 单二进制部署，适合云原生安全工具
- 大量安全工具（扫描器、C2、AI 网关）用 Go 写

---

## 29.2 安装驱动

```bash
go mod init go_mysql_demo
go get github.com/go-sql-driver/mysql
```

Go 的标准库 `database/sql` 只定义接口，具体驱动由第三方提供。`go-sql-driver/mysql` 是最常用的 MySQL 驱动。

---

## 29.3 连接和查询

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/go-sql-driver/mysql"  // 空导入，注册驱动
)

func main() {
    // 1. 打开数据库（DSN: 用户:密码@协议(地址:端口)/库名?参数）
    db, err := sql.Open("mysql",
        "secapp:密码@tcp(localhost:3306)/security_lab?charset=utf8mb4&parseTime=True")
    if err != nil {
        panic(err)
    }
    defer db.Close()

    // 2. 测试连接
    if err := db.Ping(); err != nil {
        panic(err)
    }

    // 3. 查询
    rows, err := db.Query("SELECT id, ip, status FROM hosts")
    if err != nil {
        panic(err)
    }
    defer rows.Close()

    // 4. 遍历结果
    for rows.Next() {
        var id int
        var ip, status string
        if err := rows.Scan(&id, &ip, &status); err != nil {
            panic(err)
        }
        fmt.Printf("%d: %s - %s\n", id, ip, status)
    }
}
```

关键点：

- `_ "github.com/go-sql-driver/mysql"`：空导入，触发驱动的 init 注册
- `sql.Open` 不立即连接，只是创建句柄；`db.Ping()` 才真正测试连接
- `defer rows.Close()` 和 `defer db.Close()`：Go 的 defer 自动释放资源
- `rows.Scan(&变量...)`：把行数据扫描到变量，顺序对应 SELECT 的列

DSN 参数：

- `charset=utf8mb4`：字符集
- `parseTime=True`：把 DATETIME 解析成 Go 的 time.Time
- `loc=Local`：时区

---

## 29.4 参数化查询（防注入）

```go
// 安全：用 ? 占位符
var status string
err := db.QueryRow("SELECT status FROM hosts WHERE ip = ?", "192.168.1.10").Scan(&status)
if err != nil {
    panic(err)
}
fmt.Println(status)
```

`QueryRow` 查询单行，`?` 是占位符，后面传参数——Go 驱动会做参数化，防注入（第 19 章）。

> **注意**：Go 的占位符是 `?`（MySQL 风格），不是 `$1`（PostgreSQL 风格）。

---

## 29.5 增删改

```go
// 插入
result, err := db.Exec(
    "INSERT INTO hosts (ip, os, status) VALUES (?, ?, ?)",
    "10.0.0.20", "Ubuntu", "UP")
if err != nil {
    panic(err)
}
id, _ := result.LastInsertId()
rowsAffected, _ := result.RowsAffected()
fmt.Printf("插入 ID=%d, 影响 %d 行\n", id, rowsAffected)

// 更新
db.Exec("UPDATE hosts SET status = ? WHERE ip = ?", "DOWN", "10.0.0.20")

// 删除
db.Exec("DELETE FROM hosts WHERE ip = ?", "10.0.0.20")
```

`Exec` 执行不返回行的 SQL，返回 `Result`（含 LastInsertId、RowsAffected）。

---

## 29.6 事务

```go
tx, err := db.Begin()
if err != nil {
    panic(err)
}

_, err = tx.Exec("UPDATE accounts SET balance=balance-? WHERE id=?", 100, 1)
if err != nil {
    tx.Rollback()
    panic(err)
}

_, err = tx.Exec("UPDATE accounts SET balance=balance+? WHERE id=?", 100, 2)
if err != nil {
    tx.Rollback()
    panic(err)
}

if err := tx.Commit(); err != nil {
    panic(err)
}
```

Go 的事务：显式 `Rollback()` 或用 `defer tx.Rollback()`（提交后再 Rollback 会失败但无害，这是常见写法）。

---

## 29.7 连接池配置

```go
// 设置连接池参数
db.SetMaxOpenConns(25)                 // 最大打开连接数
db.SetMaxIdleConns(5)                  // 最大空闲连接数
db.SetConnMaxLifetime(5 * 60 * 1000000000)  // 连接最大生命周期（5分钟，纳秒）
```

更清晰的写法（用 time 包）：

```go
import "time"

db.SetMaxOpenConns(25)
db.SetMaxIdleConns(5)
db.SetConnMaxLifetime(5 * time.Minute)
```

`database/sql` 自带连接池，配置这些参数能避免连接数过多或连接老化断开（呼应第 25、26 章）。

---

## 29.8 并发查询（Go 的强项）

Go 的 goroutine 配合数据库，能高效并发查询：

```go
func checkIP(ip string, db *sql.DB, ch chan<- string) {
    var status string
    err := db.QueryRow("SELECT status FROM hosts WHERE ip = ?", ip).Scan(&status)
    if err != nil {
        ch <- fmt.Sprintf("%s: 未找到", ip)
        return
    }
    ch <- fmt.Sprintf("%s: %s", ip, status)
}

func main() {
    db, _ := sql.Open("mysql", "dsn...")
    defer db.Close()

    ips := []string{"192.168.1.10", "192.168.1.11", "10.0.0.5"}
    ch := make(chan string, len(ips))

    // 并发查询
    for _, ip := range ips {
        go checkIP(ip, db, ch)
    }

    // 收集结果
    for range ips {
        fmt.Println(<-ch)
    }
}
```

多个 goroutine 共享同一个 `*sql.DB`（它是并发安全的，内部有连接池），并发查询，用 channel 收集结果。这是 Go 并发 + 数据库的经典模式——安全扫描器常用。

---

## 29.9 用 database/sql 的注意事项

1. **必须关闭 rows**：`defer rows.Close()`，否则连接泄露
2. **处理 err**：每个操作都检查 err，别忽略
3. **连接串含敏感信息**：DSN 里的密码别硬编码，用环境变量
4. **Scan 类型匹配**：数据库类型要和 Go 变量类型对应（INT→int，VARCHAR→string，DATETIME→time.Time 需 parseTime=True）
5. **NULL 处理**：可空列用 `sql.NullString`、`sql.NullInt64` 等

```go
var os sql.NullString
rows.Scan(&os)
if os.Valid {
    fmt.Println(os.String)
} else {
    fmt.Println("NULL")
}
```

---

## 29.10 本章总结

| 知识点 | 内容 |
|--------|------|
| database/sql | Go 标准库接口；go-sql-driver/mysql 驱动 |
| 连接 | `sql.Open` + `db.Ping()`；DSN 配置 |
| 查询 | `db.Query` + `rows.Scan`；`QueryRow` 查单行 |
| 参数化 | `?` 占位符 + 参数；防注入（第19章） |
| 增删改 | `db.Exec`；LastInsertId / RowsAffected |
| 事务 | `db.Begin` + `Commit` / `Rollback` |
| 连接池 | SetMaxOpenConns / MaxIdleConns / ConnMaxLifetime |
| 并发 | goroutine 共享 *sql.DB + channel 收集 |
| 注意 | 关闭 rows、处理 err、NULL 用 sql.Null* |

---

## 本章练习

1. 用 Go 连接 MySQL，查询 hosts 表并打印。
2. 用 `?` 占位符做参数化查询，验证注入输入不生效。
3. 写一个插入示例，输出 LastInsertId 和 RowsAffected。
4. 写一个事务示例，中途出错 Rollback。
5. 配置连接池参数，理解每个参数的含义。
6. 用 goroutine + channel 并发查询多个 IP，收集结果。
7. 处理一个可空列，用 sql.NullString 区分 NULL 和空字符串。
8. 思考：为什么 `sql.Open` 不立即连接？`db.Ping()` 的作用？
9. 思考：Go 的并发查询为什么高效？和连接池有什么关系？

---

**下一章预告**：MySQL 在 AI 系统中的应用——特征存储、向量元数据、模型元数据、实验追踪、RAG 知识库。这是把数据库和 AI 结合的实战指南。
