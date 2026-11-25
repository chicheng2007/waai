# 第 22 章 EXPLAIN 执行计划与查询优化

## 本章目标

读完这一章，你将能够：

- 用 EXPLAIN 查看查询的执行计划
- 读懂 EXPLAIN 输出的每一列
- 理解 type 访问类型（从优到劣）
- 知道索引是否生效、是否回表
- 掌握常见的 SQL 优化技巧

---

## 22.1 为什么需要 EXPLAIN

一条 SQL 慢，为什么慢？是没走索引？是全表扫描？是排序耗时？还是回表太多？

光看 SQL 和结果猜不出来。**EXPLAIN** 让 MySQL 告诉你它"打算怎么执行"这条查询——这就是执行计划。

```sql
EXPLAIN SELECT * FROM login_logs WHERE ip = '45.33.22.11';
```

EXPLAIN 不会真正执行查询，只是分析执行方案。这是优化 SQL 的必备工具。

---

## 22.2 EXPLAIN 输出解读

```
+----+-------------+-------------+------------+------+---------------+------+---------+------+------+----------+-------------+
| id | select_type | table       | partitions | type | possible_keys | key  | key_len | ref  | rows | filtered | Extra       |
+----+-------------+-------------+------------+------+---------------+------+---------+------+------+----------+-------------+
|  1 | SIMPLE      | login_logs  | NULL       | ref  | idx_ip        | idx_ip| 259     | const| 100  | 100.00   | Using where |
+----+-------------+-------------+------------+------+---------------+------+---------+------+------+----------+-------------+
```

各列含义：

| 列 | 含义 | 关注点 |
|----|------|--------|
| id | 查询序号 | 子查询/UNION 会有多个 id |
| select_type | 查询类型 | SIMPLE/PRIMARY/SUBQUERY/DERIVED/UNION |
| table | 访问的表 | — |
| partitions | 匹配的分区 | — |
| **type** | **访问类型** | ⭐ 最重要，见 22.3 |
| possible_keys | 可能用的索引 | — |
| **key** | **实际用的索引** | ⭐ 如果是 NULL，说明没走索引 |
| key_len | 用的索引长度 | 联合索引用了几列 |
| ref | 与索引比较的值 | const 表示常量 |
| **rows** | **预估扫描行数** | ⭐ 越小越好 |
| filtered | 过滤比例 | — |
| **Extra** | **额外信息** | ⭐ Using filesort/Using temporary 要警惕 |

---

## 22.3 type 访问类型（从优到劣）

```
system > const > eq_ref > ref > range > index > ALL
```

| type | 含义 | 说明 |
|------|------|------|
| system | 表只有一行 | 极快，特殊情况 |
| const | 主键/唯一索引匹配一行 | 很快 |
| eq_ref | 联表时主键/唯一索引匹配 | 好 |
| ref | 普通索引匹配 | 好 |
| range | 范围查询（IN/BETWEEN/>） | 还行 |
| index | 扫描整个索引树 | 差（但比 ALL 好） |
| ALL | 全表扫描 | 最差，要优化 |

**优化目标**：至少达到 range 级别，最好 ref/const。**看到 ALL 就要警惕**。

示例：

```sql
-- const：主键查询
EXPLAIN SELECT * FROM hosts WHERE id = 1;

-- ref：普通索引查询
EXPLAIN SELECT * FROM login_logs WHERE ip = '1.1.1.1';

-- range：范围查询
EXPLAIN SELECT * FROM login_logs WHERE id > 100;

-- ALL：全表扫描（没索引或索引失效）
EXPLAIN SELECT * FROM login_logs WHERE username = 'admin';
```

---

## 22.4 Extra 列的危险信号

| Extra 值 | 含义 | 处理 |
|---------|------|------|
| Using filesort | 需要额外排序 | 给 ORDER BY 的列建索引 |
| Using temporary | 用了临时表（GROUP BY/DISTINCT） | 优化分组列索引 |
| Using where | 进行了 WHERE 过滤 | 正常 |
| Using index | 覆盖索引，无需回表 | ✅ 好！ |
| Using index condition | 索引条件下推 | ✅ 还行 |
| Using join buffer | 联表没用索引 | 给 JOIN 字段建索引 |

**看到 Using filesort 和 Using temporary 要重点优化**——它们在数据量大时很慢。

---

## 22.5 实战：分析一条慢查询

假设这条查询很慢：

```sql
SELECT * FROM login_logs
WHERE username = 'admin' AND login_time >= '2026-01-01'
ORDER BY login_time DESC;
```

用 EXPLAIN 分析：

```sql
EXPLAIN SELECT * FROM login_logs
WHERE username = 'admin' AND login_time >= '2026-01-01'
ORDER BY login_time DESC;
```

假设输出：`type=ALL`（全表扫描）、`Extra=Using where; Using filesort`。

**诊断**：username 没索引，导致全表扫描；排序又用 filesort。

**优化**：建联合索引：

```sql
CREATE INDEX idx_username_time ON login_logs(username, login_time);
```

再 EXPLAIN：

- type 变成 `ref`
- Extra 变成 `Using index condition`（或 Using where），filesort 消失

因为索引 `(username, login_time)`：username 等值匹配走索引，login_time 在索引里已有序，不用额外排序。

> **关键点**：联合索引的列顺序匹配了 WHERE 和 ORDER BY——这就是好的索引设计（结合第 13 章的最左前缀原则）。

---

## 22.6 常见优化技巧

### 1. 避免 SELECT *

```sql
-- 不好
SELECT * FROM login_logs WHERE ip='1.1.1.1';
-- 好：只查需要的列，可能用覆盖索引
SELECT ip, login_time, result FROM login_logs WHERE ip='1.1.1.1';
```

### 2. 给 WHERE / JOIN / ORDER BY 的列建索引

```sql
-- WHERE 用到的列
CREATE INDEX idx_ip ON login_logs(ip);
-- JOIN 用到的列（两边都要有）
CREATE INDEX idx_task_id ON scan_results(task_id);
-- ORDER BY 用到的列
CREATE INDEX idx_time ON login_logs(login_time);
```

### 3. 避免在索引列上做运算

```sql
-- 不好：索引失效
WHERE YEAR(login_time) = 2026
WHERE ip + 0 = 123
-- 好
WHERE login_time >= '2026-01-01' AND login_time < '2027-01-01'
```

### 4. 用 LIMIT 限制结果

```sql
SELECT * FROM login_logs ORDER BY login_time DESC LIMIT 100;
```

### 5. 优化分页（深分页问题）

```sql
-- 慢：扫描前 100 万行
SELECT * FROM login_logs LIMIT 1000000, 20;

-- 快：用主键定位（延迟关联）
SELECT * FROM login_logs
WHERE id > (SELECT id FROM login_logs ORDER BY id LIMIT 1000000, 1)
ORDER BY id LIMIT 20;
```

原理：先在主键索引上找到位置（覆盖索引，快），再回表取数据。

### 6. 用 EXISTS 代替 big IN

大结果集时 EXISTS 更高效（结合第 10 章）。

### 7. 拆分大 SQL

复杂的大 SQL 拆成几个简单的，可读性更好，也更容易利用索引。

### 8. 定期分析表

```sql
ANALYZE TABLE login_logs;
```

更新统计信息，让优化器做出正确决策。

---

## 22.7 索引失效自查表

结合第 13 章，写 SQL 后对照检查：

```
□ WHERE 里对索引列做函数/运算了吗？
□ 隐式类型转换了吗？（字符串列用数字比较）
□ LIKE 前面加 % 了吗？
□ OR 连接了没索引的列吗？
□ 违反最左前缀原则了吗？
□ 用了 != / NOT IN 导致优化器放弃索引了吗？
□ SELECT * 是否破坏了覆盖索引？
```

---

## 22.8 EXPLAIN ANALYZE（MySQL 8.0）

EXPLAIN 只是"预估"，EXPLAIN ANALYZE 会**真正执行**并显示实际耗时：

```sql
EXPLAIN ANALYZE SELECT * FROM login_logs WHERE ip = '45.33.22.11';
```

输出包含实际的行数、耗时、循环次数，比 EXPLAIN 更精确。优化时用它能看到真实效果。

---

## 22.9 本章总结

| 知识点 | 内容 |
|--------|------|
| EXPLAIN | 查看执行计划；不真正执行 |
| 关键列 | type（访问类型）、key（实际索引）、rows（扫描行数）、Extra |
| type 优劣 | system>const>eq_ref>ref>range>index>ALL；目标至少 range |
| Extra 警告 | Using filesort / Using temporary 要优化；Using index 是好事 |
| 优化技巧 | 避免 SELECT *、建索引、避免运算、LIMIT、优化分页、拆大 SQL、ANALYZE |
| 深分页 | 用主键延迟关联优化 |
| EXPLAIN ANALYZE | 真正执行，看实际耗时 |

---

## 本章练习

1. 对一条简单查询执行 EXPLAIN，逐列解释输出。
2. 找一条 `type=ALL` 的查询，给相关列建索引，再用 EXPLAIN 验证变成 ref。
3. 写一条 ORDER BY 产生 `Using filesort` 的查询，通过建索引消除它。
4. 用 EXPLAIN ANALYZE 对比优化前后的实际耗时。
5. 写一个深分页查询，用延迟关联优化，对比两种写法的 rows。
6. 思考：type 从 ALL 优化到 ref，为什么性能提升巨大？
7. 思考：Using index（覆盖索引）为什么是好事？和回表有什么关系？

---

**下一章预告**：备份与恢复——数据库的"保险"。mysqldump、binlog、全量/增量备份、误删数据恢复。数据无价，备份是最后的安全网。
