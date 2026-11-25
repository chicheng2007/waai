# 第 4 章 DDL：创建和管理库表

## 本章目标

读完这一章，你将能够：

- 用 SQL 创建、查看、修改、删除数据库和表
- 理解常见的列属性（NOT NULL、DEFAULT、AUTO_INCREMENT、COMMENT）
- 掌握 `ALTER TABLE` 的各种常用操作
- 知道删除数据和删除表的区别

---

## 4.1 DDL 是什么

DDL（Data Definition Language，数据定义语言）用来**定义数据结构**——建库、建表、改表、删表。它操作的是"骨架"，不是"数据"。

记住这个区别：

- DDL：创建/修改/删除**表结构**（CREATE / ALTER / DROP）
- DML：操作表里的**数据**（INSERT / UPDATE / DELETE）

本章我们用一个贯穿的案例：**搭建一个漏洞扫描平台的数据表**。

---

## 4.2 创建数据库

```sql
CREATE DATABASE vulnscan;
```

更严谨的写法（推荐）：

```sql
CREATE DATABASE IF NOT EXISTS vulnscan
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
```

逐项解释：

| 写法 | 含义 |
|------|------|
| `IF NOT EXISTS` | 如果库不存在才创建，存在则不报错（避免重复执行出错） |
| `DEFAULT CHARACTER SET utf8mb4` | 默认字符集用 utf8mb4（支持 emoji 和所有 Unicode 字符） |
| `DEFAULT COLLATE utf8mb4_unicode_ci` | 排序规则，ci 表示大小写不敏感 |

> **小白问**：为什么是 utf8mb4 而不是 utf8？
> MySQL 里的 `utf8` 是个历史遗留的"假 utf8"，每个字符最多 3 字节，存不了 emoji 和某些生僻字。`utf8mb4` 才是真正的 UTF-8（最多 4 字节）。**永远用 utf8mb4**，这是铁律。

查看现有数据库：

```sql
SHOW DATABASES;
```

查看某个库的创建语句：

```sql
SHOW CREATE DATABASE vulnscan;
```

---

## 4.3 创建表

先切换到这个库：

```sql
USE vulnscan;
```

创建"扫描任务表"：

```sql
CREATE TABLE IF NOT EXISTS scan_tasks (
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '任务ID' PRIMARY KEY,
    target VARCHAR(255) NOT NULL COMMENT '扫描目标（域名/IP）',
    scan_type ENUM('PORT', 'WEB', 'VULN') NOT NULL DEFAULT 'PORT' COMMENT '扫描类型',
    status ENUM('PENDING', 'RUNNING', 'DONE', 'FAILED') NOT NULL DEFAULT 'PENDING' COMMENT '任务状态',
    priority TINYINT NOT NULL DEFAULT 5 COMMENT '优先级1-10',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='扫描任务表';
```

这段代码信息量很大，逐行拆解：

| 代码 | 含义 |
|------|------|
| `BIGINT UNSIGNED` | 无符号大整数，范围更大（0 到 2^64-1） |
| `AUTO_INCREMENT` | 自动递增，插入时不给 id 就自动分配 |
| `COMMENT '任务ID'` | 列注释，方便维护 |
| `PRIMARY KEY` | 主键，唯一非空 |
| `VARCHAR(255) NOT NULL` | 最多 255 字符的字符串，不能为空 |
| `ENUM(...)` | 枚举，只能取括号里的值之一——很好的数据约束 |
| `DEFAULT 'PORT'` | 默认值，插入时不给就用默认值 |
| `DEFAULT CURRENT_TIMESTAMP` | 默认值为当前时间 |
| `ON UPDATE CURRENT_TIMESTAMP` | 行更新时自动刷新为当前时间 |
| `ENGINE=InnoDB` | 存储引擎用 InnoDB（支持事务） |
| `DEFAULT CHARSET=utf8mb4` | 表字符集 |
| `COMMENT='扫描任务表'` | 表注释 |

> **小白问**：`updated_at` 那个 `ON UPDATE` 是怎么自动更新的？
> 这是 MySQL 的一个贴心特性：只要这行数据被 UPDATE，这一列就会自动变成当前时间，不用你在 SQL 里手动写。做日志、审计特别好用。

再创建一张"扫描结果表"：

```sql
CREATE TABLE IF NOT EXISTS scan_results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT UNSIGNED NOT NULL COMMENT '关联任务ID',
    host VARCHAR(255) NOT NULL COMMENT '主机',
    port INT NOT NULL COMMENT '端口',
    service VARCHAR(64) COMMENT '服务名',
    severity ENUM('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL DEFAULT 'INFO' COMMENT '严重级别',
    detail TEXT COMMENT '详情',
    found_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发现时间',
    INDEX idx_task_id (task_id),
    INDEX idx_host_port (host, port)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='扫描结果表';
```

注意最后的 `INDEX`——这是**索引**，第 13 章会详细讲。现在只要知道它能让查询变快就行。

---

## 4.4 查看表结构

```sql
SHOW TABLES;                    -- 查看所有表
DESC scan_tasks;                -- 查看表结构
SHOW CREATE TABLE scan_tasks;   -- 查看完整建表语句
```

`SHOW CREATE TABLE` 特别有用——它能看到表的完整定义，包括引擎、字符集、索引。当你接手别人的数据库时，第一件事就是用它。

---

## 4.5 修改表：ALTER TABLE

表建好后，需求变了怎么办？用 `ALTER TABLE`。

**加一列：**

```sql
ALTER TABLE scan_tasks
ADD COLUMN scanner_version VARCHAR(32) COMMENT '扫描器版本' AFTER priority;
```

`AFTER priority` 指定新列放在 priority 后面。也可以 `FIRST` 放第一列。

**改列类型：**

```sql
ALTER TABLE scan_tasks
MODIFY COLUMN target VARCHAR(512) NOT NULL COMMENT '扫描目标';
```

注意 `MODIFY` 要写完整的列定义（包括 NOT NULL、COMMENT），否则会被覆盖掉。

**改列名：**

```sql
ALTER TABLE scan_tasks
CHANGE COLUMN scanner_version scanner_ver VARCHAR(32) COMMENT '扫描器版本';
```

`CHANGE` 能改名，且必须写新列类型。

**删一列：**

```sql
ALTER TABLE scan_tasks DROP COLUMN scanner_ver;
```

**加索引：**

```sql
ALTER TABLE scan_results ADD INDEX idx_severity (severity);
```

**改表名：**

```sql
ALTER TABLE scan_tasks RENAME TO tasks;
```

或者：

```sql
RENAME TABLE tasks TO scan_tasks;
```

> **注意**：在生产环境，`ALTER TABLE` 大表可能锁表、影响业务。MySQL 8.0 对很多 ALTER 操作做了优化（Online DDL），但大表变更仍需谨慎，最好在业务低峰期做。第 25 章会讲更多。

---

## 4.6 删除：DROP vs TRUNCATE vs DELETE

这三个都能"删",但差别很大：

| 语句 | 删除什么 | 可否回滚 | 速度 | 自增ID |
|------|---------|---------|------|--------|
| `DROP TABLE 表名` | 整张表（结构+数据） | 不可 | 快 | —— |
| `TRUNCATE TABLE 表名` | 表里所有数据（保留结构） | 不可 | 快 | 重置为 1 |
| `DELETE FROM 表名` | 表里的行（可带 WHERE） | 可（事务中） | 慢（逐行） | 不重置 |

```sql
DROP TABLE IF EXISTS scan_results;   -- 删表，慎用！
TRUNCATE TABLE scan_results;         -- 清空表数据
DELETE FROM scan_results WHERE severity = 'INFO';  -- 删符合条件的行
```

> **小白问**：`DELETE FROM 表名;`（不带 WHERE）会怎样？
> 会删掉表里所有行，效果和 TRUNCATE 类似，但慢很多，而且自增 ID 不会重置。**永远记得检查 WHERE 条件**——这是新手最常犯的致命错误之一。很多"删库跑路"事故就是一条没带 WHERE 的 DELETE。

---

## 4.7 一个完整案例：从零搭建扫描平台的表

把前面的知识串起来，写一个可以直接跑的完整脚本：

```sql
-- 1. 建库
CREATE DATABASE IF NOT EXISTS vulnscan
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 2. 用库
USE vulnscan;

-- 3. 建扫描任务表
CREATE TABLE IF NOT EXISTS scan_tasks (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    target VARCHAR(255) NOT NULL COMMENT '扫描目标',
    scan_type ENUM('PORT', 'WEB', 'VULN') NOT NULL DEFAULT 'PORT',
    status ENUM('PENDING', 'RUNNING', 'DONE', 'FAILED') NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 建扫描结果表
CREATE TABLE IF NOT EXISTS scan_results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT UNSIGNED NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    severity ENUM('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL DEFAULT 'INFO',
    found_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 验证
SHOW TABLES;
DESC scan_tasks;
DESC scan_results;
```

把它保存为 `vulnscan.sql`，以后用 `mysql -u root -p < vulnscan.sql` 一键建库建表。这就是**数据库迁移脚本**的雏形，工程化项目都这么干。

---

## 4.8 本章总结

| 知识点 | 内容 |
|--------|------|
| DDL | 定义结构：CREATE / ALTER / DROP |
| 建库 | `CREATE DATABASE IF NOT EXISTS ... CHARSET utf8mb4` |
| 字符集 | 永远用 utf8mb4，不用 utf8 |
| 建表 | 列定义 + 表选项（ENGINE/CHARSET/COMMENT） |
| 列属性 | NOT NULL / DEFAULT / AUTO_INCREMENT / COMMENT / ENUM |
| 时间戳 | `DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` |
| 改表 | `ALTER TABLE` 加列、改列、改名、加索引 |
| 删除对比 | DROP 删表 / TRUNCATE 清表 / DELETE 删行；前两者不可回滚 |
| 安全提醒 | DELETE 务必带 WHERE，谨防误删 |

---

## 本章练习

1. 创建数据库 `security_lab`（如果还没建），然后在里面创建 `hosts` 表和 `scan_results` 表。
2. 给 `hosts` 表加一列 `os_version VARCHAR(32)`，放在 `os` 后面。
3. 把 `os_version` 改名为 `os_ver`。
4. 用 `SHOW CREATE TABLE` 查看你建的某张表，理解输出的每一部分。
5. 分别用 DROP、TRUNCATE、DELETE 在测试表上实验，观察区别（在测试库里随便玩）。
6. 写一个 `.sql` 脚本文件，包含建库和建表语句，用 `mysql < 文件` 的方式一键执行。
7. 思考：为什么 `utf8mb4` 比 `utf8` 好？`ON UPDATE CURRENT_TIMESTAMP` 有什么实际用途？

---

**下一章预告**：表结构搭好了，接下来往里面填数据——INSERT 插入、UPDATE 更新、DELETE 删除，这就是 DML。我们会重点强调"别写没 WHERE 的 UPDATE/DELETE"这个安全习惯。
