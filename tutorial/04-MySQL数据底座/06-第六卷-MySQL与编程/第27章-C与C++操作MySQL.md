# 第 27 章 C/C++ 操作 MySQL

## 本章目标

读完这一章，你将能够：

- 用 MySQL Connector/C API 连接和操作数据库
- 理解 C API 的核心结构和函数
- 用预处理语句防止 SQL 注入
- 理解 C++ 封装（RAII）资源管理

---

## 27.1 为什么用 C/C++ 操作 MySQL

Python 操作数据库很方便，但有些场景必须用 C/C++：

- **高性能**：AI 推理引擎、高频交易系统，需要极致性能
- **底层工具**：安全工具（扫描器、抓包分析）常是 C/C++ 写的
- **嵌入式/资源受限**：内存小的环境跑不了 Python
- **系统程序**：直接集成到 C/C++ 项目里，避免跨语言开销

MySQL 提供官方的 **Connector/C** 库，C 和 C++ 都能用。

---

## 27.2 安装 Connector/C

```bash
# Ubuntu/Debian
sudo apt install libmysqlclient-dev

# macOS
brew install mysql-client

# 检查
mysql_config --version
```

编译时要链接库：

```bash
gcc program.c -o program $(mysql_config --cflags --libs)
```

---

## 27.3 C API 核心概念

| 结构/函数 | 作用 |
|----------|------|
| `MYSQL` | 连接句柄 |
| `MYSQL_RES` | 查询结果集 |
| `MYSQL_ROW` | 结果集里的一行 |
| `mysql_init()` | 初始化连接句柄 |
| `mysql_real_connect()` | 连接数据库 |
| `mysql_query()` | 执行 SQL |
| `mysql_store_result()` | 获取结果 |
| `mysql_fetch_row()` | 逐行读取 |
| `mysql_close()` | 关闭连接 |

---

## 27.4 第一个 C 程序：查询数据

```c
#include <mysql/mysql.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    MYSQL *conn;
    MYSQL_RES *res;
    MYSQL_ROW row;

    // 1. 初始化连接句柄
    conn = mysql_init(NULL);
    if (conn == NULL) {
        fprintf(stderr, "mysql_init 失败\n");
        return 1;
    }

    // 2. 连接数据库
    if (mysql_real_connect(conn, "localhost", "secapp", "密码",
                           "security_lab", 3306, NULL, 0) == NULL) {
        fprintf(stderr, "连接失败: %s\n", mysql_error(conn));
        mysql_close(conn);
        return 1;
    }

    // 3. 执行查询
    if (mysql_query(conn, "SELECT id, ip, status FROM hosts")) {
        fprintf(stderr, "查询失败: %s\n", mysql_error(conn));
        mysql_close(conn);
        return 1;
    }

    // 4. 获取结果集
    res = mysql_store_result(conn);
    if (res == NULL) {
        fprintf(stderr, "获取结果失败: %s\n", mysql_error(conn));
        mysql_close(conn);
        return 1;
    }

    // 5. 逐行读取
    printf("ID\tIP\t\t状态\n");
    while ((row = mysql_fetch_row(res)) != NULL) {
        printf("%s\t%s\t%s\n", row[0], row[1], row[2]);
    }

    // 6. 释放资源
    mysql_free_result(res);
    mysql_close(conn);
    return 0;
}
```

编译：

```bash
gcc mysql_demo.c -o mysql_demo $(mysql_config --cflags --libs)
./mysql_demo
```

逐行理解：

- `mysql_init(NULL)`：创建一个连接对象
- `mysql_real_connect`：建立连接（参数：主机、用户、密码、库名、端口、socket、flags）
- `mysql_query`：执行 SQL 字符串
- `mysql_store_result`：把结果全部读到客户端内存
- `mysql_fetch_row`：每次返回一行（字符串数组），NULL 表示读完
- 最后必须 `mysql_free_result` 和 `mysql_close`——**C 里手动管理资源是铁律**

---

## 27.5 插入、更新、删除

增删改不返回结果集：

```c
const char *sql = "INSERT INTO hosts (ip, os, status) VALUES ('192.168.1.50', 'Ubuntu', 'UP')";
if (mysql_query(conn, sql)) {
    fprintf(stderr, "插入失败: %s\n", mysql_error(conn));
} else {
    printf("插入成功，影响 %lu 行，新ID: %lu\n",
           (unsigned long)mysql_affected_rows(conn),
           (unsigned long)mysql_insert_id(conn));
}
```

`mysql_affected_rows()` 返回影响的行数，`mysql_insert_id()` 返回自增 ID。

---

## 27.6 SQL 注入与预处理语句

**危险：直接拼接字符串**

```c
// 危险！输入可能含注入代码
char sql[512];
sprintf(sql, "SELECT * FROM users WHERE username='%s'", user_input);
mysql_query(conn, sql);
```

这和 Python 里拼接字符串一样危险（第 19 章）。

**安全：预处理语句**

```c
MYSQL_STMT *stmt = mysql_stmt_init(conn);
const char *sql = "SELECT id, username FROM users WHERE username = ?";
mysql_stmt_prepare(stmt, sql, strlen(sql));

// 绑定参数
MYSQL_BIND bind[1];
memset(bind, 0, sizeof(bind));
bind[0].buffer_type = MYSQL_TYPE_STRING;
bind[0].buffer = (char *)user_input;
bind[0].buffer_length = strlen(user_input);
mysql_stmt_bind_param(stmt, bind);

// 执行
mysql_stmt_execute(stmt);

// 绑定结果
MYSQL_BIND result[2];
long user_id;
char username[64];
memset(result, 0, sizeof(result));
result[0].buffer_type = MYSQL_TYPE_LONG;
result[0].buffer = &user_id;
result[1].buffer_type = MYSQL_TYPE_STRING;
result[1].buffer = username;
result[1].buffer_length = sizeof(username);
mysql_stmt_bind_result(stmt, result);

// 取结果
while (mysql_stmt_fetch(stmt) == 0) {
    printf("id=%ld, username=%s\n", user_id, username);
}

mysql_stmt_close(stmt);
```

预处理语句的流程：

1. `mysql_stmt_init` 初始化语句
2. `mysql_stmt_prepare` 发送带 `?` 的 SQL 模板
3. `mysql_stmt_bind_param` 绑定参数（数据单独传）
4. `mysql_stmt_execute` 执行
5. `mysql_stmt_bind_result` + `mysql_stmt_fetch` 取结果
6. `mysql_stmt_close` 释放

**这就是第 19 章"参数化查询"的 C 实现**——SQL 和数据分离，注入失效。虽然代码比 Python 繁琐，但原理一样。

---

## 27.7 事务

```c
mysql_query(conn, "START TRANSACTION");

mysql_query(conn, "UPDATE accounts SET balance=balance-100 WHERE id=1");
mysql_query(conn, "UPDATE accounts SET balance=balance+100 WHERE id=2");

// 检查是否有错误
if (mysql_errno(conn)) {
    mysql_query(conn, "ROLLBACK");
    printf("回滚\n");
} else {
    mysql_query(conn, "COMMIT");
    printf("提交\n");
}
```

---

## 27.8 C++ 封装：RAII 自动管理资源

C API 需要手动释放资源，容易忘记（内存泄露）。C++ 用 **RAII**（资源获取即初始化）自动管理：

```cpp
#include <mysql/mysql.h>
#include <string>
#include <stdexcept>

class DBConn {
private:
    MYSQL* conn;

public:
    DBConn(const char* host, const char* user,
           const char* pwd, const char* db) {
        conn = mysql_init(nullptr);
        if (!conn || !mysql_real_connect(conn, host, user, pwd, db, 3306, nullptr, 0)) {
            std::string err = conn ? mysql_error(conn) : "init failed";
            if (conn) mysql_close(conn);
            throw std::runtime_error(err);
        }
    }

    ~DBConn() {  // 析构时自动关闭
        if (conn) mysql_close(conn);
    }

    MYSQL* get() { return conn; }

    // 禁止拷贝（避免重复释放）
    DBConn(const DBConn&) = delete;
    DBConn& operator=(const DBConn&) = delete;
};

// 使用
void demo() {
    DBConn db("localhost", "secapp", "密码", "security_lab");
    if (mysql_query(db.get(), "SELECT * FROM hosts")) {
        throw std::runtime_error(mysql_error(db.get()));
    }
    // 函数结束，db 自动析构，连接自动关闭——不用手动管理！
}
```

RAII 的价值：即使函数抛异常，析构函数也会执行，资源不会泄露。这是 C++ 管理数据库连接的推荐方式。

也有官方的 **Connector/C++**（`mysqlcppconn`），提供更高层的 C++ API，但底层还是这套 C API。理解 C API 后，用 Connector/C++ 更容易。

---

## 27.9 C/C++ 操作 MySQL 的适用场景

| 场景 | 说明 |
|------|------|
| AI 推理引擎 | 高性能读取数据，低延迟 |
| 安全工具 | C/C++ 写的扫描器把结果存库 |
| 高频交易 | 微秒级延迟要求 |
| 嵌入式系统 | 资源受限，跑不了 heavy 运行时 |
| 系统程序 | 避免跨语言调用开销 |

**权衡**：C/C++ 性能高但开发效率低、容易内存错误；Python 开发快但性能低。实际项目常混合——核心用 C++，胶水用 Python（这正是第三套"混合编程"教程的主题）。

---

## 27.10 本章总结

| 知识点 | 内容 |
|--------|------|
| Connector/C | 官方 C API；C/C++ 都能用 |
| 核心结构 | MYSQL（连接）、MYSQL_RES（结果）、MYSQL_ROW（行） |
| 查询流程 | init → connect → query → store_result → fetch_row → free/close |
| 增删改 | mysql_query + affected_rows + insert_id |
| 预处理语句 | stmt_init/prepare/bind_param/execute；防注入（呼应第19章） |
| 事务 | START TRANSACTION / COMMIT / ROLLBACK |
| C++ RAII | 析构自动释放资源；禁止拷贝；异常安全 |
| 适用场景 | 高性能 AI 引擎、安全工具、嵌入式 |

---

## 本章练习

1. 写一个 C 程序连接 MySQL，查询 hosts 表并打印。
2. 用 C API 插入一条数据，输出影响行数和自增 ID。
3. 把一段拼接 SQL 的代码改成预处理语句，验证注入输入不再生效。
4. 写一个事务示例：两次 UPDATE，一次成功一次失败，观察回滚。
5. 用 C++ RAII 封装连接类，验证异常时资源自动释放。
6. 思考：C API 为什么要手动释放资源？RAII 如何解决？
7. 思考：预处理语句在 C 里为什么比 Python 繁琐？原理是否相同？

---

**下一章预告**：用 Rust 操作 MySQL——Rust 的内存安全 + 高性能，配合 MySQL 是下一代安全工具的选择。我们会用 sqlx 和 diesel 两个主流库。
