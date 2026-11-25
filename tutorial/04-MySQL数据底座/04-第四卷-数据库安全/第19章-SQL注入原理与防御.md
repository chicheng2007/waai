# 第 19 章 SQL 注入：原理、利用与防御

> **伦理声明（重要）**：本章所有攻击技术仅用于**你自己搭建的本地靶场**（如 DVWA、sqli-labs）或获得书面授权的环境。未经授权对他人系统测试属于违法行为。请严格遵守《网络安全法》等法律法规，守住白帽底线。学习攻击技术的目的是**更好地防御**。

## 本章目标

读完这一章，你将能够：

- 理解 SQL 注入的根本原因——代码与数据混淆
- 掌握联合查询注入、布尔盲注、时间盲注的原理
- 理解预编译语句（参数化查询）为什么能防御注入
- 知道其他的防御手段和纵深防御思路
- 在靶场里亲手复现注入与防御

---

## 19.1 SQL 注入的本质

**SQL 注入（SQL Injection）** 是因为程序把用户输入**直接拼接**进 SQL 语句，导致输入被当作 SQL 代码执行。

看一个典型的漏洞代码（Python 伪代码）：

```python
# 危险代码：字符串拼接
username = input("用户名: ")
sql = f"SELECT * FROM users WHERE username = '{username}'"
cursor.execute(sql)
```

正常输入 `admin`，SQL 变成：

```sql
SELECT * FROM users WHERE username = 'admin'
```

没问题。

但攻击者输入：`admin' OR '1'='1`

SQL 变成：

```sql
SELECT * FROM users WHERE username = 'admin' OR '1'='1'
```

`OR '1'='1'` 永远为真，导致**返回所有用户**——绕过登录验证！

**根本原因**：用户输入（数据）被当成了 SQL 代码（指令）。程序和数据的边界被打破了。

> **小白问**：SQL 注入真的是最危险的漏洞吗？
> 它在 OWASP Top 10 长年位居前列。历史上无数大厂被注入攻破：拖库、绕登录、删表、拿服务器权限。理解它，是 Web 安全的必修课。

---

## 19.2 搭建练习靶场

强烈建议用 **sqli-labs**——专门练 SQL 注入的靶场。

```bash
# 用 Docker 一键搭建（需要 Docker + MySQL）
docker run -d -p 8080:80 --name sqli-labs acgpiano/sqli-labs
```

或者用 DVWA：

```bash
docker run -d -p 8081:80 --name dvwa vulnerables/web-dvwa
```

访问 `http://localhost:8080`，按提示初始化。后面所有演示都在靶场里做。

---

## 19.3 判断是否存在注入

### 第一步：加单引号

在输入框输入：`'`

如果页面报错（SQL 语法错误），说明输入被拼进了 SQL——可能存在注入。

```
You have an error in your SQL syntax...
```

### 第二步：注释掉后面的内容

输入：`' -- `（注意 -- 后面有空格）

SQL 变成：

```sql
SELECT * FROM users WHERE username = '' -- '
```

`--` 是 SQL 注释符，后面的被注释掉。如果页面正常返回（或返回特定结果），注入点确认。

MySQL 注释符：

- `-- ` （两个减号加空格）
- `#`
- `/* ... */` （多行注释）

### 第三步：恒真/恒假测试

输入：`' OR 1=1 -- ` → 恒真，返回所有数据
输入：`' OR 1=2 -- ` → 恒假，返回空

两次结果不同，说明注入有效。

---

## 19.4 联合查询注入（UNION）

如果查询的结果会显示在页面上，可以用 UNION 把其他表的数据"拼"进结果。

### 确定列数

用 ORDER BY 猜列数：

```
' ORDER BY 1 --    正常
' ORDER BY 2 --    正常
' ORDER BY 3 --    正常
' ORDER BY 4 --    报错 → 说明有 3 列
```

### 确定显示位

```
' UNION SELECT 1,2,3 -- 
```

页面会显示 1、2、3 中哪些数字出现在页面上——出现的位置就是"显示位"。

### 爆库、爆表、爆列

假设第 2 列是显示位：

```
' UNION SELECT 1, database(), 3 --           → 得到当前数据库名
' UNION SELECT 1, group_concat(table_name), 3 FROM information_schema.tables WHERE table_schema=database() --  → 得到所有表名
' UNION SELECT 1, group_concat(column_name), 3 FROM information_schema.columns WHERE table_name='users' --  → 得到列名
' UNION SELECT 1, group_concat(username,':',password), 3 FROM users --  → 拖取数据
```

**information_schema** 是 MySQL 自带的信息数据库，存着所有库、表、列、权限的元数据。注入攻击常利用它来"探路"。

> **防御提示**：这就是为什么应用账号不该有访问 information_schema 的权限不该太大——但根本防御还是参数化查询。

---

## 19.5 布尔盲注

如果页面**不显示数据**，只根据查询结果返回"真/假"两种状态（比如"登录成功/失败"），用布尔盲注。

原理：通过构造条件，逐字符猜测数据。

```
' AND SUBSTRING((SELECT database()),1,1)='s' -- 
```

如果页面返回"真"，说明数据库名第一个字符是 's'；否则换一个字符试。逐字符猜出完整数据。

常用函数：

- `SUBSTRING(str, pos, len)`：取子串
- `ASCII(char)`：字符的 ASCII 码
- `LENGTH(str)`：字符串长度
- `IF(cond, a, b)`：条件判断

示例：猜数据库名长度：

```
' AND LENGTH(database())=8 -- 
```

真则长度是 8。

批量自动化用 sqlmap 工具，但学习阶段建议手工理解原理。

---

## 19.6 时间盲注

如果页面**连真假状态都不显示**（永远返回一样），用时间盲注——通过延时判断条件真假。

```
' AND IF(SUBSTRING(database(),1,1)='s', SLEEP(5), 0) -- 
```

如果条件为真，数据库会 `SLEEP(5)` 秒，页面响应变慢；否则立即返回。通过响应时间判断条件真假，逐字符猜数据。

`SLEEP()`、`BENCHMARK()` 是常用的延时函数。

> **小白问**：这些盲注看起来很笨（一个字符一个字符猜），实际有用吗？
> 手工很慢，但用工具（sqlmap）自动化后很快。关键是理解原理——防御时你要知道攻击者能通过这些手段拿到什么。

---

## 19.7 其他注入类型（了解）

| 类型 | 说明 |
|------|------|
| 宽字节注入 | 利用 GBK 等多字节编码绕过转义 |
| 堆叠注入 | 用 `;` 分隔执行多条语句（`DROP TABLE`） |
| 二次注入 | 数据先存进去，后面取出时再拼接触发 |
| Header 注入 | 在 HTTP 头（User-Agent、Cookie、Referer）里注入 |
| 报错注入 | 通过构造报错让错误信息回显数据（updatexml、extractvalue） |

---

## 19.8 根本防御：预编译语句（参数化查询）

**这是最重要的一节。**

SQL 注入的根本原因是"拼接"。防御的根本方法是**不拼接**——用预编译语句（Prepared Statement），让 SQL 代码和数据彻底分离。

### 原理

```
1. 先发送 SQL 模板：SELECT * FROM users WHERE username = ?
   （数据库先编译这个模板，确定 SQL 结构）

2. 再单独发送参数值：admin' OR '1'='1
   （这个值只当作数据处理，不会再被解析成 SQL 代码）
```

即使参数里有 `' OR 1=1`，数据库也只把它当成一个普通的字符串值，不会改变 SQL 结构。

### Python 示例（PyMySQL）

```python
# 危险：拼接
sql = f"SELECT * FROM users WHERE username = '{username}'"
cursor.execute(sql)

# 安全：参数化（用 %s 占位符）
sql = "SELECT * FROM users WHERE username = %s"
cursor.execute(sql, (username,))
```

### Python 示例（SQLAlchemy）

```python
# 安全
result = conn.execute(
    text("SELECT * FROM users WHERE username = :name"),
    {"name": username}
)
```

### C/C++ 示例（MySQL Connector/C++）

```cpp
// 安全：预编译语句
sql::PreparedStatement* pstmt = conn->prepareStatement(
    "SELECT * FROM users WHERE username = ?");
pstmt->setString(1, username);
pstmt->executeQuery();
```

### Java 示例（JDBC）

```java
String sql = "SELECT * FROM users WHERE username = ?";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setString(1, username);
ResultSet rs = pstmt.executeQuery();
```

### Go 示例

```go
row := db.QueryRow("SELECT * FROM users WHERE username = ?", username)
```

### Rust 示例（sqlx）

```rust
let user = sqlx::query!("SELECT * FROM users WHERE username = $1", username)
    .fetch_one(&pool).await?;
```

**记住这个模式**：任何语言的数据库操作，都用参数化查询，永远不要拼接用户输入。

---

## 19.9 其他防御手段（纵深防御）

参数化查询是根本，但纵深防御要多层：

### 1. 输入验证

对输入做白名单校验（类型、长度、格式）：

```python
# 端口只能是数字
if not port.isdigit():
    reject()
```

注意：输入验证是**辅助**手段，不能替代参数化查询。

### 2. 最小权限

应用账号只有必要的权限（第 18 章），即使被注入，破坏也有限。

### 3. ORM 框架

现代 ORM（SQLAlchemy、Django ORM、GORM）默认用参数化查询，能减少注入风险。但 ORM 也能写出注入（比如用原生 SQL 拼接时），不能盲目依赖。

### 4. 存储过程

把查询封装在存储过程里，也能一定程度防注入（但存储过程内部如果拼接仍有问题）。

### 5. WAF（Web 应用防火墙）

在 Web 层检测和拦截注入攻击特征。是补充手段，不能替代代码层的防御。

### 6. 错误信息不回显

不要把数据库错误直接显示给用户——攻击者能通过报错获取信息。生产环境关闭详细报错。

### 7. 关闭不必要的函数

如 `SLEEP`、`LOAD_FILE` 等，减少盲注和文件读取风险。

---

## 19.10 靶场实战步骤（在授权环境）

1. 启动 sqli-labs，打开 Level 1
2. 输入 `'`，观察报错——确认注入点
3. 输入 `' OR 1=1 -- `，绕过登录
4. 用 ORDER BY 确定列数
5. 用 UNION SELECT 爆库、爆表、爆数据
6. 切换到盲注关卡（Level 5+），练习布尔盲注
7. 用 sqlmap 自动化（`sqlmap -u "url" --dbs`）
8. 把同样的漏洞代码改成参数化查询，验证注入失效

---

## 19.11 本章总结

| 知识点 | 内容 |
|--------|------|
| 注入本质 | 用户输入被当成 SQL 代码执行；代码与数据混淆 |
| 判断注入 | 加单引号看报错；`OR 1=1` 恒真；`--` 注释 |
| 联合注入 | UNION SELECT；information_schema 爆库表列 |
| 布尔盲注 | 通过真假状态逐字符猜 |
| 时间盲注 | 通过 SLEEP 延时判断真假 |
| 其他类型 | 宽字节、堆叠、二次、Header、报错注入 |
| 根本防御 | 参数化查询（Prepared Statement）——SQL 与数据分离 |
| 纵深防御 | 输入验证、最小权限、ORM、WAF、关闭报错回显 |
| 合规 | 仅在授权靶场练习；学攻击为更好地防御 |

---

## 本章练习

1. 在 sqli-labs Level 1 手工完成一次联合查询注入，爆出数据库名和表名。
2. 找到一处使用字符串拼接的代码，把它改成参数化查询。
3. 用 Python + PyMySQL 写一个有注入漏洞的例子，再写一个安全的版本，对比。
4. 在布尔盲注关卡，手工猜出数据库名的第一个字符。
5. 用 sqlmap 对一个靶场 URL 做自动化检测（仅在本地靶场！）。
6. 思考：为什么参数化查询能彻底防御注入？它的原理是什么？
7. 思考：输入验证能替代参数化查询吗？为什么？
8. 思考：如果必须用动态表名/列名（无法参数化），该怎么安全地处理？（提示：白名单映射）

---

**下一章预告**：数据库安全加固——从配置层面保护 MySQL：修改默认端口、禁用危险功能、网络隔离、文件权限、定期更新补丁。让数据库本身变得难攻破。
