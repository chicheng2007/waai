# 第 5 章 DML：插入、更新、删除数据

## 本章目标

读完这一章，你将能够：

- 用 INSERT 插入单行、多行数据
- 用 UPDATE 更新数据（并牢记 WHERE 的重要性）
- 用 DELETE 删除数据（并牢记 WHERE 的重要性）
- 理解事务 basics，知道怎么回滚误操作

---

## 5.1 DML 是什么

DML（Data Manipulation Language，数据操作语言）用来**操作表里的数据**：增（INSERT）、改（UPDATE）、删（DELETE）。

上一章我们搭好了骨架，这一章往里填血肉。

先准备环境：

```sql
USE vulnscan;
```

---

## 5.2 INSERT：插入数据

### 插入单行（指定列）

```sql
INSERT INTO scan_tasks (target, scan_type, status, priority)
VALUES ('192.168.1.0/24', 'PORT', 'PENDING', 8);
```

注意：

- 列名单独一行，VALUES 里按同样顺序写值
- `id` 没写——因为它是 AUTO_INCREMENT，自动分配
- `created_at`、`updated_at` 没写——有默认值，自动填

只写你要指定的列，其他列用默认值，这是最推荐的方式。

### 插入多行

```sql
INSERT INTO scan_tasks (target, scan_type, status) VALUES
('example.com', 'WEB', 'PENDING'),
('10.0.0.1', 'VULN', 'RUNNING'),
('test.local', 'PORT', 'DONE');
```

一次插入多行，比多次单行插入快得多（减少网络往返）。批量导入数据时一定要用这种写法。

### 不指定列（不推荐）

```sql
INSERT INTO scan_tasks VALUES (NULL, '1.1.1.1', 'PORT', 'PENDING', 5, NOW(), NOW());
```

必须给每一列都提供值，顺序还得和表结构一致。一旦表结构改了就会出错。**生产代码别这么写**。

### 插入时处理重复

有时你不想重复插入相同数据。用 `ON DUPLICATE KEY UPDATE`：

```sql
INSERT INTO hosts (ip, os, status)
VALUES ('192.168.1.10', 'Ubuntu 22.04', 'UP')
ON DUPLICATE KEY UPDATE os = VALUES(os), status = VALUES(status);
```

如果 ip 是唯一键且已存在，就更新而不是插入。这在同步数据时很常用。

### 插入查询结果

```sql
INSERT INTO archive_tasks (target, scan_type, status)
SELECT target, scan_type, status FROM scan_tasks WHERE status = 'DONE';
```

把查询结果直接插进另一张表，数据归档、备份常用。

---

## 5.3 UPDATE：更新数据

```sql
UPDATE scan_tasks
SET status = 'RUNNING'
WHERE id = 1;
```

**⚠️ 黄金法则：UPDATE 必须带 WHERE！**

不带 WHERE 会更新整张表：

```sql
UPDATE scan_tasks SET status = 'DONE';  -- 危险！所有任务都变成 DONE 了
```

### 更新多列

```sql
UPDATE scan_tasks
SET status = 'FAILED', priority = priority - 1
WHERE target = '10.0.0.1';
```

`priority = priority - 1` 这种"基于当前值更新"是允许的，常用于计数器。

### 用表达式更新

```sql
UPDATE scan_results
SET severity = 'HIGH'
WHERE port IN (22, 3389) AND severity = 'MEDIUM';
```

把 22、3389 端口的中危结果提升为高危——安全场景里很实用的批量调整。

### 安全更新技巧：先 SELECT 再 UPDATE

专业习惯：写 UPDATE 前，先用同样的 WHERE 跑一遍 SELECT，确认会影响哪些行：

```sql
-- 第一步：看清楚要改哪些
SELECT id, target, status FROM scan_tasks WHERE status = 'PENDING';

-- 第二步：确认无误后再改
UPDATE scan_tasks SET status = 'RUNNING' WHERE status = 'PENDING';
```

这个"先看后改"的习惯能救命。

> **小白问**：MySQL 有没有"安全模式"防止不带 WHERE 的 UPDATE？
> 有。`SET SQL_SAFE_UPDATES = 1;` 开启后，不带 WHERE（或 WHERE 不用索引）的 UPDATE/DELETE 会报错。图形工具（Workbench）默认开启。命令行默认关闭。建议学习时开着，养成好习惯。

---

## 5.4 DELETE：删除数据

```sql
DELETE FROM scan_results WHERE id = 5;
```

**⚠️ 同样：DELETE 必须带 WHERE！**

```sql
DELETE FROM scan_results;  -- 危险！清空整张表
```

### 删除符合条件的行

```sql
DELETE FROM scan_results
WHERE severity = 'INFO' AND found_at < '2026-01-01';
```

删除 2026 年以前的低危结果——清理旧数据。

### 用子查询删除

```sql
DELETE FROM scan_results
WHERE task_id IN (
    SELECT id FROM scan_tasks WHERE status = 'FAILED'
);
```

删除所有失败任务的扫描结果。

### DELETE vs TRUNCATE（回顾）

| 对比 | DELETE | TRUNCATE |
|------|--------|----------|
| 可带 WHERE | ✅ | ❌ |
| 逐行删除 | ✅ | ❌（整表重建） |
| 可回滚 | ✅（事务中） | ❌ |
| 触发触发器 | ✅ | ❌ |
| 重置自增ID | ❌ | ✅ |
| 速度 | 慢 | 快 |

清空测试表用 TRUNCATE，按条件删除用 DELETE。

---

## 5.5 事务：误操作的后悔药

### 什么是事务

**事务（Transaction）** 是一组 SQL 操作，要么全部成功，要么全部失败。这是数据库保证数据一致性的核心机制（第 16 章详解）。

基本用法：

```sql
START TRANSACTION;   -- 开始事务

UPDATE accounts SET balance = balance - 100 WHERE user_id = 1;
UPDATE accounts SET balance = balance + 100 WHERE user_id = 2;

COMMIT;              -- 提交，所有修改生效
```

如果中间出错：

```sql
START TRANSACTION;

UPDATE scan_tasks SET status = 'DONE' WHERE id = 1;
-- 哎呀，改错了！

ROLLBACK;            -- 回滚，撤销所有修改
```

> **注意**：MySQL 默认开启**自动提交**（autocommit=1）——每条 SQL 执行完立即生效，无法回滚。要手动控制事务，必须先 `START TRANSACTION`。

### 用事务保护批量操作

```sql
START TRANSACTION;

DELETE FROM scan_results WHERE task_id = 10;
DELETE FROM scan_tasks WHERE id = 10;

-- 检查影响行数，确认没问题
SELECT ROW_COUNT();

COMMIT;  -- 确认无误后提交；如有问题用 ROLLBACK
```

做危险操作时，包一层事务，出错了还能 ROLLBACK。这是专业习惯。

---

## 5.6 完整案例：一次扫描的完整数据生命周期

把 INSERT / UPDATE / DELETE / 事务串起来：

```sql
USE vulnscan;

-- 1. 插入一个扫描任务
INSERT INTO scan_tasks (target, scan_type, status, priority)
VALUES ('192.168.1.10', 'PORT', 'PENDING', 7);

-- 拿到刚插入的 id
SELECT LAST_INSERT_ID();

-- 2. 更新任务状态为运行中
UPDATE scan_tasks SET status = 'RUNNING' WHERE id = LAST_INSERT_ID();

-- 3. 插入扫描结果（假设发现 3 个开放端口）
INSERT INTO scan_results (task_id, host, port, severity, detail) VALUES
(1, '192.168.1.10', 22, 'MEDIUM', 'SSH 服务开放'),
(1, '192.168.1.10', 80, 'INFO', 'HTTP 服务开放'),
(1, '192.168.1.10', 3306, 'HIGH', 'MySQL 服务暴露');

-- 4. 更新任务为完成
UPDATE scan_tasks SET status = 'DONE' WHERE id = 1;

-- 5. 查看结果
SELECT * FROM scan_results WHERE task_id = 1;

-- 6. 清理：删除这个任务及其结果（用事务保护）
START TRANSACTION;
DELETE FROM scan_results WHERE task_id = 1;
DELETE FROM scan_tasks WHERE id = 1;
COMMIT;
```

这就是一个扫描器写数据库的典型流程。第六卷讲编程时，你会用 Python/C++/Go 做同样的事，只是把 SQL 换成程序里的调用。

---

## 5.7 本章总结

| 知识点 | 内容 |
|--------|------|
| INSERT | 指定列插入（推荐）、多行插入、INSERT...SELECT、ON DUPLICATE KEY UPDATE |
| UPDATE | 必须带 WHERE；先 SELECT 确认再改；SQL_SAFE_UPDATES 保护 |
| DELETE | 必须带 WHERE；可用子查询；与 TRUNCATE 的区别 |
| 黄金法则 | UPDATE/DELETE 永远先检查 WHERE 条件 |
| 事务 | START TRANSACTION / COMMIT / ROLLBACK；默认 autocommit=1 |
| 后悔药 | 危险操作包事务，出错可 ROLLBACK |
| 安全习惯 | 先看（SELECT）后改（UPDATE/DELETE）；开启安全更新模式 |

---

## 本章练习

1. 在 `scan_tasks` 表插入 3 个任务，用一次 INSERT 多行完成。
2. 把所有 `priority` 大于 8 的任务状态改成 'RUNNING'，改之前先用 SELECT 确认影响哪些行。
3. 删除 `scan_results` 里 severity='INFO' 的所有记录。
4. 开启 `SET SQL_SAFE_UPDATES = 1;`，然后故意写一条不带 WHERE 的 UPDATE，观察报错。
5. 用事务包住一次删除操作，先 ROLLBACK 验证数据还在，再重新执行并 COMMIT。
6. 思考：为什么"先 SELECT 再 UPDATE"是专业习惯？它在什么场景下能救命？

---

**下一章预告**：数据进去了，最重要的是"查出来"。我们开始学 SELECT——SQL 里最强大、最常用的语句。从最简单的 `SELECT *` 到各种花样查询。
