# 第 6 章 SELECT：查询数据的基础

## 本章目标

读完这一章，你将能够：

- 用 SELECT 查询指定列、所有列、去重
- 给列起别名，用表达式计算
- 理解 SELECT 的执行顺序（逻辑顺序）
- 掌握 LIMIT 分页

---

## 6.1 SELECT 为什么是最重要的语句

在数据库的所有操作里，**查询（SELECT）占了 80% 以上**。安全员查日志、分析师查数据、后端程序读配置，全靠 SELECT。

SELECT 的基本结构：

```sql
SELECT 列名1, 列名2, ...
FROM 表名
WHERE 条件
GROUP BY 分组列
HAVING 分组后条件
ORDER BY 排序列
LIMIT 行数;
```

这一章先讲 SELECT 和 FROM，下一章讲 WHERE/ORDER BY/LIMIT，再下一章讲 GROUP BY/HAVING。一步步来。

---

## 6.2 查询所有列和指定列

```sql
USE security_lab;

-- 查询所有列
SELECT * FROM hosts;

-- 查询指定列
SELECT ip, status FROM hosts;
```

`SELECT *` 方便，但**生产代码不推荐**：

1. 返回不需要的列，浪费网络带宽
2. 表结构变了，返回列也变，程序可能出错
3. 无法利用"覆盖索引"优化（第 13、22 章讲）

**推荐：明确写出需要的列。**

```sql
-- 好的写法
SELECT id, ip, status FROM hosts;
```

---

## 6.3 列别名（AS）

```sql
SELECT
    ip AS '主机地址',
    status AS '状态'
FROM hosts;
```

`AS` 可以省略：

```sql
SELECT ip '主机地址', status '状态' FROM hosts;
```

别名的作用：

- 中文列名，结果更可读
- 给计算列起名字
- 多表查询时区分同名列

> **小白问**：别名会影响表里的列名吗？
> 不会。别名只是这一次查询结果的显示名，表里的数据没变。

---

## 6.4 去重：DISTINCT

```sql
SELECT DISTINCT status FROM hosts;
```

只返回不同的 status 值（UP、DOWN），重复的去掉。

多列去重：

```sql
SELECT DISTINCT os, status FROM hosts;
```

按 (os, status) 的组合去重——只有两列都相同才算重复。

实际场景：找出扫描结果里出现过的所有严重级别：

```sql
SELECT DISTINCT severity FROM scan_results;
```

---

## 6.5 表达式与计算列

SELECT 后面可以跟表达式：

```sql
SELECT
    ip,
    port,
    port * 2 AS 'port_x2'
FROM scan_results;
```

字符串拼接：

```sql
SELECT
    CONCAT(host, ':', port) AS '地址端口',
    severity
FROM scan_results;
```

时间计算：

```sql
SELECT
    target,
    created_at,
    DATEDIFF(NOW(), created_at) AS '已创建天数'
FROM scan_tasks;
```

条件表达式（CASE WHEN）——非常实用：

```sql
SELECT
    host,
    port,
    CASE severity
        WHEN 'CRITICAL' THEN '严重'
        WHEN 'HIGH' THEN '高'
        WHEN 'MEDIUM' THEN '中'
        WHEN 'LOW' THEN '低'
        ELSE '信息'
    END AS '风险等级'
FROM scan_results;
```

或者：

```sql
SELECT
    ip,
    CASE
        WHEN status = 'UP' THEN '在线'
        ELSE '离线'
    END AS '状态说明'
FROM hosts;
```

CASE WHEN 是 SQL 里的"if-else"，做数据分级、打标签特别好用。

---

## 6.6 分页：LIMIT

```sql
SELECT * FROM hosts LIMIT 3;           -- 前 3 行
SELECT * FROM hosts LIMIT 2, 3;        -- 从第 3 行开始，取 3 行（索引从 0 开始）
SELECT * FROM hosts LIMIT 3 OFFSET 2;  -- 同上，更清晰的写法
```

分页公式：`LIMIT (页码-1)*每页条数, 每页条数`

```sql
-- 第 1 页，每页 10 条
SELECT * FROM scan_results LIMIT 0, 10;
-- 第 2 页
SELECT * FROM scan_results LIMIT 10, 10;
-- 第 3 页
SELECT * FROM scan_results LIMIT 20, 10;
```

> **小白问**：LIMIT 1000000, 10 为什么很慢？
> 因为 MySQL 要先扫描过前 100 万行再取 10 行。深分页是大表查询的经典性能问题，第 22 章会讲优化方案（用游标/延迟关联）。

---

## 6.7 SELECT 的逻辑执行顺序

这是很多人搞不清的地方。你写的顺序 ≠ 执行顺序。

**书写顺序：**

```sql
SELECT ...
FROM ...
WHERE ...
GROUP BY ...
HAVING ...
ORDER BY ...
LIMIT ...;
```

**逻辑执行顺序：**

```
1. FROM       → 确定从哪张表读
2. WHERE      → 过滤行
3. GROUP BY   → 分组
4. HAVING     → 过滤分组
5. SELECT     → 选择列、计算表达式
6. DISTINCT   → 去重
7. ORDER BY   → 排序
8. LIMIT      → 限制行数
```

理解这个顺序能解释很多现象：

- **为什么 WHERE 里不能用 SELECT 的别名？** 因为 WHERE 在 SELECT 之前执行，别名还不存在。
- **为什么 ORDER BY 可以用别名？** 因为 ORDER BY 在 SELECT 之后执行。
- **为什么 HAVING 能用到聚合函数？** 因为分组在 WHERE 之后、HAVING 之前。

记住这个顺序，后面写复杂查询会清晰很多。

---

## 6.8 NULL 的处理

NULL 表示"未知/没有值"，它和空字符串 `''`、数字 0 都不一样。

```sql
SELECT * FROM hosts WHERE os IS NULL;      -- 查 os 为空的行
SELECT * FROM hosts WHERE os IS NOT NULL;  -- 查 os 不为空的行
```

**⚠️ 不能用 `= NULL`**：

```sql
SELECT * FROM hosts WHERE os = NULL;  -- 错误！永远返回空
SELECT * FROM hosts WHERE os != NULL; -- 同样错误
```

原因：NULL 参与的比较结果都是 UNKNOWN（既不是 TRUE 也不是 FALSE），WHERE 只保留 TRUE 的行。

用 `IFNULL` 给 NULL 一个替代值：

```sql
SELECT
    ip,
    IFNULL(os, '未知系统') AS os
FROM hosts;
```

> **小白问**：为什么设计这么反人类的 NULL？
> NULL 表达的是"不知道"，而不是"空"。`os = NULL` 的意思是"操作系统等于'不知道'"，这本身没法判断真假。SQL 用三值逻辑（TRUE/FALSE/UNKNOWN）处理它。习惯就好。

---

## 6.9 一个实用的查询示例

```sql
USE vulnscan;

-- 查询高危及以上的扫描结果，显示主机、端口、风险等级、发现时间
SELECT
    CONCAT(host, ':', port) AS '目标',
    CASE severity
        WHEN 'CRITICAL' THEN '严重'
        WHEN 'HIGH' THEN '高'
        ELSE '其他'
    END AS '风险等级',
    found_at AS '发现时间'
FROM scan_results
WHERE severity IN ('CRITICAL', 'HIGH')
LIMIT 20;
```

这条查询用到的知识点：CONCAT、CASE WHEN、别名、WHERE IN、LIMIT。把基础打牢，后面复杂的查询都是这些的组合。

---

## 6.10 本章总结

| 知识点 | 内容 |
|--------|------|
| SELECT 基础 | 指定列（推荐）vs `SELECT *` |
| 别名 | `AS`，可省略；只影响显示 |
| DISTINCT | 去重；多列按组合去重 |
| 表达式 | 计算列、CONCAT、DATEDIFF、CASE WHEN |
| LIMIT | 分页；`LIMIT offset, count`；深分页有性能问题 |
| 执行顺序 | FROM → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT |
| NULL | 用 IS NULL / IS NOT NULL；不能用 = NULL；IFNULL 给默认值 |

---

## 本章练习

1. 从 `hosts` 表查询所有在线（UP）主机的 ip 和 os，用中文别名显示。
2. 查询 `scan_results` 里出现过的所有不同 host（用 DISTINCT）。
3. 写一个查询，把 severity 翻译成中文，只显示高风险（HIGH、CRITICAL）的前 5 条。
4. 对 `scan_results` 做分页查询：每页 5 条，分别查出第 1、2、3 页。
5. 查询 `os` 为 NULL 的主机，用 IFNULL 显示为"未知"。
6. 思考：为什么 WHERE 里不能用 SELECT 定义的别名？结合执行顺序解释。
7. 思考：`SELECT *` 在生产环境为什么不好？至少说出三条理由。

---

**下一章预告**：查询加条件——WHERE 的各种运算符（比较、范围 IN/BETWEEN、模糊 LIKE、逻辑 AND/OR）、排序 ORDER BY、以及分页的更多细节。这是日常查询用得最多的部分。
