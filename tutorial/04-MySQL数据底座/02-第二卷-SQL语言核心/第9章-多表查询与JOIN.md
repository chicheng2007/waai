# 第 9 章 多表查询与 JOIN

## 本章目标

读完这一章，你将能够：

- 理解为什么需要多表查询（范式与冗余）
- 掌握 INNER JOIN / LEFT JOIN / RIGHT JOIN
- 理解 ON 与 WHERE 的区别
- 做多表联查、自连接
- 避免 JOIN 的常见坑

---

## 9.1 为什么要多表查询

假设你在 scan_results 表里既存漏洞信息，又存任务的所有信息（目标、扫描器版本、创建人、创建时间……）。每条结果都要重复写一遍任务信息——这就是**数据冗余**。

冗余的问题：

- 浪费空间
- 改任务信息时要改很多行（容易不一致）
- 逻辑混乱

正确做法：**分表**。任务信息放 `scan_tasks`，结果放 `scan_results`，用 `task_id` 关联。查的时候再"拼起来"——这就是 JOIN。

> **小白问**：分表是不是总是对的？
> 不一定。有时为了避免 JOIN 的性能开销，会故意冗余一些字段（叫"反范式"）。第 11 章讲范式时会细说。初学者先按范式设计，规范最重要。

---

## 9.2 准备数据

先建几张表并插入示例数据：

```sql
USE vulnscan;

-- 任务表
INSERT INTO scan_tasks (target, scan_type, status, priority) VALUES
('192.168.1.10', 'PORT', 'DONE', 8),
('example.com', 'WEB', 'DONE', 6),
('10.0.0.5', 'VULN', 'RUNNING', 9);

-- 结果表（task_id 关联任务）
INSERT INTO scan_results (task_id, host, port, severity) VALUES
(1, '192.168.1.10', 22, 'MEDIUM'),
(1, '192.168.1.10', 3306, 'HIGH'),
(2, 'example.com', 80, 'INFO'),
(2, 'example.com', 443, 'LOW'),
(3, '10.0.0.5', 8080, 'CRITICAL');

-- 新建一张扫描器表
CREATE TABLE scanners (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    version VARCHAR(32)
);
INSERT INTO scanners (name, version) VALUES
('Nmap', '7.94'),
('Nikto', '2.1.6'),
('OpenVAS', '22.4');

-- 给任务表加个 scanner_id 列并填值
ALTER TABLE scan_tasks ADD COLUMN scanner_id INT;
UPDATE scan_tasks SET scanner_id = 1 WHERE id = 1;
UPDATE scan_tasks SET scanner_id = 2 WHERE id = 2;
UPDATE scan_tasks SET scanner_id = 3 WHERE id = 3;
```

现在三张表通过 task_id、scanner_id 关联起来了。

---

## 9.3 INNER JOIN（内连接）

内连接只返回**两边都匹配**的行。

```sql
SELECT
    t.id AS task_id,
    t.target,
    r.port,
    r.severity
FROM scan_tasks t
INNER JOIN scan_results r ON t.id = r.task_id;
```

解读：

- `FROM scan_tasks t`：`t` 是表别名（简化书写）
- `INNER JOIN scan_results r`：连接结果表，别名 `r`
- `ON t.id = r.task_id`：连接条件——任务的 id 等于结果的 task_id
- SELECT 里挑需要的列

结果：每个任务及其对应的漏洞结果。如果某个任务没结果，或某条结果没有对应任务，都不会出现。

> **小白问**：表别名可以不加 AS 吗？
> 可以，`FROM scan_tasks t` 等价于 `FROM scan_tasks AS t`。但列别名建议加 AS 更清晰。

### 三表连接

```sql
SELECT
    t.target,
    s.name AS scanner,
    s.version,
    r.port,
    r.severity
FROM scan_tasks t
INNER JOIN scanners s ON t.scanner_id = s.id
INNER JOIN scan_results r ON t.id = r.task_id
ORDER BY t.target, r.port;
```

一次查出：任务目标、用哪个扫描器、扫出什么漏洞。JOIN 可以串很多张表。

---

## 9.4 LEFT JOIN（左连接）

左连接返回**左表的所有行** + 右表匹配的行。右表没匹配的，用 NULL 填充。

```sql
SELECT
    t.target,
    r.port,
    r.severity
FROM scan_tasks t
LEFT JOIN scan_results r ON t.id = r.task_id;
```

即使某个任务没有扫描结果，这个任务也会出现（port 和 severity 是 NULL）。

**典型用途：找出没有结果的任务**

```sql
SELECT t.id, t.target
FROM scan_tasks t
LEFT JOIN scan_results r ON t.id = r.task_id
WHERE r.id IS NULL;
```

这是 LEFT JOIN 的经典技巧：**左连接 + 右表主键 IS NULL = 找出左表中没有对应右表记录的行**。安全场景里常用来找"没有告警的主机""没有结果的扫描任务"。

---

## 9.5 RIGHT JOIN（右连接）

右连接返回**右表的所有行** + 左表匹配的行。

```sql
SELECT t.target, r.port
FROM scan_tasks t
RIGHT JOIN scan_results r ON t.id = r.task_id;
```

实际中 RIGHT JOIN 用得少，因为可以换成 LEFT JOIN（交换表顺序）：

```sql
SELECT t.target, r.port
FROM scan_results r
LEFT JOIN scan_tasks t ON t.id = r.task_id;
```

结果一样。习惯上只用 LEFT JOIN，代码更统一。

---

## 9.6 JOIN 类型对比图

```
INNER JOIN:    只取交集
    [ A ∩ B ]

LEFT JOIN:     取 A 全部 + 交集
    [ A 全部 ][ A∩B ]

RIGHT JOIN:    取 B 全部 + 交集
    [ A∩B ][ B 全部 ]
```

| 类型 | 返回行 |
|------|--------|
| INNER JOIN | 两表都匹配的行 |
| LEFT JOIN | 左表全部 + 匹配的右表（不匹配填 NULL） |
| RIGHT JOIN | 右表全部 + 匹配的左表（不匹配填 NULL） |

MySQL 还支持 CROSS JOIN（笛卡尔积）和 FULL OUTER JOIN（MySQL 不直接支持，需用 UNION 模拟），初学阶段先掌握三种。

---

## 9.7 ON 与 WHERE 的区别

这是个容易混淆的点。以 LEFT JOIN 为例：

```sql
-- 条件放 ON 里
SELECT t.target, r.port
FROM scan_tasks t
LEFT JOIN scan_results r ON t.id = r.task_id AND r.severity = 'HIGH';

-- 条件放 WHERE 里
SELECT t.target, r.port
FROM scan_tasks t
LEFT JOIN scan_results r ON t.id = r.task_id
WHERE r.severity = 'HIGH';
```

**结果不同！**

- 第一个：左表所有任务都保留，只有 severity='HIGH' 的结果被连接进来；没有 HIGH 结果的任务，port 是 NULL
- 第二个：先左连接，再用 WHERE 过滤——只剩有 HIGH 结果的任务，变成了事实上的 INNER JOIN

**原则**：

- 连接条件（两表怎么关联）放 ON
- 过滤右表的条件，如果想保留左表全部行，放 ON；如果不过滤左表，放 WHERE

> **小白问**：这个区别什么时候重要？
> 当你要"列出所有任务，并标出其中高危漏洞"时，必须用 ON。用 WHERE 会把没高危漏洞的任务过滤掉，结果就不全了。

---

## 9.8 自连接（Self Join）

一张表和自己连接。典型场景：员工表里的上下级关系。

```sql
CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64),
    manager_id INT
);
INSERT INTO employees (name, manager_id) VALUES
('张三', NULL),      -- 老板
('李四', 1),         -- 张三的下属
('王五', 1);         -- 张三的下属

-- 查出每个员工及其经理
SELECT
    e.name AS 员工,
    m.name AS 经理
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;
```

同一张表用了两次，用别名 `e`（员工）和 `m`（经理）区分。

---

## 9.9 多表查询的性能注意

1. **ON 条件字段要有索引**：`t.id` 是主键有索引，`r.task_id` 要有索引（第 4 章建表时加了 `INDEX idx_task_id`）。
2. **小表驱动大表**：MySQL 优化器一般会自己选，但理解原理有帮助。
3. **避免笛卡尔积**：JOIN 忘了写 ON 条件，会产生两表行数的乘积——几行变几万行。
4. **只 SELECT 需要的列**：减少数据传输。

```sql
-- 危险：没写 ON，产生笛卡尔积
SELECT * FROM scan_tasks, scan_results;
```

---

## 9.10 完整案例：安全分析的多表查询

```sql
-- 查询：每个任务的目标、扫描器名称、发现的漏洞数、最高危级别
SELECT
    t.target,
    s.name AS scanner,
    COUNT(r.id) AS vuln_count,
    MAX(CASE r.severity
        WHEN 'CRITICAL' THEN 5
        WHEN 'HIGH' THEN 4
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 2
        ELSE 1
    END) AS max_severity_level
FROM scan_tasks t
LEFT JOIN scanners s ON t.scanner_id = s.id
LEFT JOIN scan_results r ON t.id = r.task_id
GROUP BY t.id, t.target, s.name
ORDER BY max_severity_level DESC, vuln_count DESC;
```

这条查询用了：三表 LEFT JOIN、聚合 COUNT、CASE WHEN、GROUP BY、ORDER BY。这就是工作中真实会写的分析查询。

---

## 9.11 本章总结

| 知识点 | 内容 |
|--------|------|
| 为什么分表 | 避免冗余、保证一致性 |
| INNER JOIN | 只返回两表都匹配的行 |
| LEFT JOIN | 左表全部 + 匹配的右表；不匹配填 NULL |
| RIGHT JOIN | 右表全部 + 匹配的左表；可用 LEFT JOIN 替代 |
| ON vs WHERE | 连接条件放 ON；保留左表全部时右表过滤也放 ON |
| 找无对应记录 | LEFT JOIN + 右表主键 IS NULL |
| 自连接 | 表自己和自己连，用别名区分 |
| 性能 | ON 字段建索引、避免笛卡尔积、只查需要的列 |

---

## 本章练习

1. 用 INNER JOIN 查询每个任务的目标和对应的漏洞端口。
2. 用 LEFT JOIN 列出所有任务（包括没有漏洞结果的），显示目标和高危漏洞数。
3. 用 LEFT JOIN + IS NULL 找出没有扫描结果的任务。
4. 做三表连接：任务 + 扫描器 + 结果，显示任务目标、扫描器名、漏洞严重级别。
5. 写一条自连接查询：找出所有有下属的经理（提示：员工表自连接，manager_id 匹配 id）。
6. 对比 ON 和 WHERE 放条件的区别：写两条 SQL，观察结果差异。
7. 思考：为什么 JOIN 的 ON 字段要建索引？不建会怎样？

---

**下一章预告**：子查询——把一条查询的结果作为另一条查询的条件。它和 JOIN 有什么区别？什么时候用哪个？我们还会讲 EXISTS、ANY、ALL 这些高级玩法。
