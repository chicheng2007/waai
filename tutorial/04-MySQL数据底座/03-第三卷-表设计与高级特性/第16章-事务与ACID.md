# 第 16 章 事务与 ACID

## 本章目标

读完这一章，你将能够：

- 理解事务的概念——要么全做，要么全不做
- 掌握 ACID 四大特性
- 理解脏读、不可重复读、幻读
- 掌握四种隔离级别
- 知道 MySQL InnoDB 的默认隔离级别

---

## 16.1 为什么需要事务

经典例子：银行转账。

张三给李四转 100 元，需要两步：

```sql
UPDATE accounts SET balance = balance - 100 WHERE name = '张三';  -- 扣钱
UPDATE accounts SET balance = balance + 100 WHERE name = '李四';  -- 加钱
```

如果第一步成功，第二步失败（比如断电），张三少了 100，李四没收到——钱凭空消失了。

**事务（Transaction）** 解决这个问题：把两步绑成一个整体，**要么都成功，要么都失败**。

```sql
START TRANSACTION;

UPDATE accounts SET balance = balance - 100 WHERE name = '张三';
UPDATE accounts SET balance = balance + 100 WHERE name = '李四';

COMMIT;  -- 两步都成功，一起生效
-- 或 ROLLBACK;  -- 任一步失败，全部撤销
```

---

## 16.2 事务的基本操作

```sql
START TRANSACTION;       -- 或 BEGIN，开始事务
-- 或 SET autocommit = 0;  关闭自动提交

-- 执行若干 SQL
INSERT ...;
UPDATE ...;
DELETE ...;

COMMIT;                  -- 提交：所有修改永久生效
ROLLBACK;                -- 回滚：撤销所有修改
SAVEPOINT sp1;            -- 保存点
ROLLBACK TO sp1;          -- 回滚到保存点
```

### 保存点示例

```sql
START TRANSACTION;

INSERT INTO scan_tasks (target) VALUES ('1.1.1.1');
SAVEPOINT after_insert;

INSERT INTO scan_results (task_id, host, port) VALUES (1, '1.1.1.1', 80);
-- 结果插入失败了，回滚到保存点，保留任务插入
ROLLBACK TO after_insert;

COMMIT;
```

### autocommit

MySQL 默认 `autocommit = 1`——每条 SQL 执行完立即提交，无法回滚。

```sql
SELECT @@autocommit;       -- 查看，默认是 1
SET autocommit = 0;        -- 关闭自动提交（当前会话）
```

关闭后，所有 SQL 都在一个事务里，直到你 COMMIT 或 ROLLBACK。

> **注意**：`SET autocommit=0` 是会话级的，只影响当前连接。新连接还是默认 1。程序里通常用 `START TRANSACTION` 显式开启事务，更清晰。

---

## 16.3 ACID 四大特性

事务必须满足 ACID：

### A - Atomicity（原子性）

事务是最小单位，**不可再分**——要么全部成功，要么全部失败。

实现：靠 **undo log（回滚日志）**。事务失败时，用 undo log 把数据恢复到事务前的状态。

### C - Consistency（一致性）

事务执行前后，数据库都处于**合法状态**——满足所有约束和业务规则。

比如转账前后，两人的总余额不变。如果违反约束（如余额不能为负），事务会失败。

一致性是最终目标，靠其他三个特性（原子性、隔离性、持久性）共同保证。

### I - Isolation（隔离性）

多个事务并发执行时，**互相隔离**，一个事务的中间状态对其他事务不可见。

隔离性有级别之分（见 16.5），级别越高越安全但并发性能越低。

实现：靠锁和 MVCC（多版本并发控制）。

### D - Durability（持久性）

事务提交后，修改**永久保存**，即使断电也不丢失。

实现：靠 **redo log（重做日志）**。提交时先写 redo log，即使数据还没刷到磁盘，崩溃后也能从 redo log 恢复。

> **小白问**：ACID 是哪四个英文单词？
> Atomicity（原子性）、Consistency（一致性）、Isolation（隔离性）、Durability（持久性）。面试高频考点，务必记住。

---

## 16.4 并发事务的问题

如果不隔离，多个事务并发会出四种问题：

### 1. 脏读（Dirty Read）

事务 A 修改了数据**但未提交**，事务 B 读到了这个未提交的数据。如果 A 回滚，B 读到的就是"脏数据"（从未真正存在过）。

```
时间线：
A: 修改 balance=900（未提交）
B: 读到 balance=900       ← 脏读
A: 回滚，balance 还是 1000
B: 白高兴一场，900 是假的
```

### 2. 不可重复读（Non-repeatable Read）

事务 A 在一个事务内**多次读同一数据**，中间事务 B 修改了并提交，导致 A 两次读到的值不同。

```
A: 第一次读 balance=1000
B: 修改 balance=900，提交
A: 第二次读 balance=900   ← 不可重复读（同一事务内读同一数据，值变了）
```

### 3. 幻读（Phantom Read）

事务 A 按条件查询，事务 B **插入了新行**并提交，A 再查同样的条件，发现多了几行（像幻觉）。

```
A: SELECT * FROM users WHERE age>20  → 返回 3 行
B: 插入一个 age=25 的用户，提交
A: 再查同样条件 → 返回 4 行  ← 幻读
```

**不可重复读 vs 幻读**：

- 不可重复读：针对**同一行**的 UPDATE/DELETE，值变了
- 幻读：针对**新插入的行**，结果集行数变了

### 4. 丢失更新（Lost Update）

两个事务同时修改同一数据，后提交的覆盖先提交的。

---

## 16.5 四种隔离级别

SQL 标准定义了四种隔离级别，解决上面的问题：

| 隔离级别 | 脏读 | 不可重复读 | 幻读 | 并发性能 |
|---------|------|-----------|------|---------|
| READ UNCOMMITTED（读未提交） | ❌ 允许 | ❌ 允许 | ❌ 允许 | 最高 |
| READ COMMITTED（读已提交） | ✅ 解决 | ❌ 允许 | ❌ 允许 | 高 |
| REPEATABLE READ（可重复读） | ✅ 解决 | ✅ 解决 | ❌ 允许 | 中 |
| SERIALIZABLE（串行化） | ✅ 解决 | ✅ 解决 | ✅ 解决 | 最低 |

### 各级别说明

**READ UNCOMMITTED**：能读别人未提交的数据。实际几乎不用。

**READ COMMITTED**：只能读已提交的数据。解决脏读。Oracle、PostgreSQL 默认这个级别。

**REPEATABLE READ**：同一事务内多次读同一数据，结果一致。解决脏读和不可重复读。**MySQL InnoDB 默认这个级别**，而且通过 next-key lock 也基本解决了幻读。

**SERIALIZABLE**：所有事务串行执行，完全隔离，但并发性能极差。很少用。

### 查看和设置隔离级别

```sql
-- 查看全局隔离级别
SELECT @@global.transaction_isolation;

-- 查看当前会话隔离级别
SELECT @@session.transaction_isolation;

-- 设置会话隔离级别
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- 设置全局隔离级别
SET GLOBAL TRANSACTION ISOLATION LEVEL REPEATABLE READ;
```

> **MySQL 8.0 变量名**：`transaction_isolation`。老版本（5.7 及以前）用 `tx_isolation`。

> **小白问**：MySQL 默认 REPEATABLE READ，为什么不用 READ COMMITTED？
> 历史原因（早期 binlog 格式的兼容性）。REPEATABLE READ 更安全，InnoDB 用 MVCC + next-key lock 解决了大部分幻读问题。一般保持默认即可。

---

## 16.6 MVCC：多版本并发控制

InnoDB 用 **MVCC** 实现高并发的读写隔离，不用加锁就能保证"读已提交"和"可重复读"。

核心思想：

- 每行数据有多个版本（通过 undo log 保存历史版本）
- 事务读数据时，根据规则选择可见的版本
- 读操作不加锁，写操作加锁——读写不冲突，并发高

简化理解：

```
行 data = 1000，事务 A 改成 900（未提交）
  → undo log 保存旧版本 1000

事务 B 读这行：
  - READ COMMITTED：看最新已提交版本
  - REPEATABLE READ：看事务开始时的一致性快照
```

MVCC 是 InnoDB 高并发的基石。了解概念即可，深入实现（隐藏列 trx_id、roll_ptr、Read View）超出本教程范围。

---

## 16.7 事务的最佳实践

**1. 事务要短**

事务越长，持有的锁越久，并发越差。事务里别做网络请求、别做耗时计算。

```sql
-- 不好：事务里 doing 慢操作
START TRANSACTION;
-- ... 复杂计算或网络请求 ...
UPDATE ...;
COMMIT;

-- 好：先算完，事务里只做数据库操作
-- ... 复杂计算 ...
START TRANSACTION;
UPDATE ...;
COMMIT;
```

**2. 明确指定事务边界**

用 `START TRANSACTION` / `COMMIT` 明确控制，别依赖隐式行为。

**3. 出错要 ROLLBACK**

程序里捕获异常后要回滚：

```python
# Python 伪代码
try:
    cursor.execute("START TRANSACTION")
    cursor.execute("UPDATE ...")
    cursor.execute("UPDATE ...")
    conn.commit()
except Exception:
    conn.rollback()  # 出错回滚
```

**4. 避免长事务**

长事务会导致 undo log 堆积、锁等待、主从延迟。监控长事务：

```sql
SELECT * FROM information_schema.innodb_trx
WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 60;
```

---

## 16.8 完整案例：安全告警的事务处理

```sql
START TRANSACTION;

-- 1. 插入告警
INSERT INTO security_alerts (alert_type, ip, detail, created_at)
VALUES ('BRUTE_FORCE', '45.33.22.11', '失败次数312', NOW());

-- 2. 更新 IP 的威胁评分
UPDATE threat_intel
SET severity = LEAST(severity + 1, 5)
WHERE indicator = '45.33.22.11' AND type = 'IP';

-- 3. 记录操作日志
INSERT INTO audit_log (action, detail, created_at)
VALUES ('ADD_ALERT', '检测到暴力破解 45.33.22.11', NOW());

COMMIT;
-- 任何一步失败都应该 ROLLBACK，保证三个操作要么都做要么都不做
```

这就是事务在安全系统里的典型应用——告警、评分更新、审计记录必须一致。

---

## 16.9 本章总结

| 知识点 | 内容 |
|--------|------|
| 事务 | 一组 SQL 要么全成功要么全失败；START TRANSACTION / COMMIT / ROLLBACK |
| ACID | Atomicity 原子性、Consistency 一致性、Isolation 隔离性、Durability 持久性 |
| 实现 | 原子性靠 undo log，持久性靠 redo log，隔离性靠锁和 MVCC |
| 并发问题 | 脏读、不可重复读、幻读、丢失更新 |
| 隔离级别 | RU / RC / RR / Serializable；MySQL 默认 REPEATABLE READ |
| MVCC | 多版本并发控制；读写不冲突，高并发基石 |
| 最佳实践 | 事务要短、明确边界、出错回滚、避免长事务 |

---

## 本章练习

1. 用事务模拟一次转账：张三减 100，李四加 100，然后 COMMIT。
2. 在事务中故意执行一条错误 SQL，然后 ROLLBACK，验证数据未变。
3. 用 SAVEPOINT 做一个部分回滚的实验。
4. 查看你 MySQL 的默认隔离级别。
5. 开两个命令行窗口（两个会话），模拟脏读：一个事务修改未提交，另一个读，观察现象。
6. 用自己的话解释脏读、不可重复读、幻读的区别。
7. 思考：ACID 分别靠什么机制实现？为什么事务要尽量短？

---

**下一章预告**：锁机制——事务隔离的底层实现。共享锁、排他锁、行锁、表锁、间隙锁、死锁。理解了锁，你就能明白为什么有的操作会卡住，怎么避免。
