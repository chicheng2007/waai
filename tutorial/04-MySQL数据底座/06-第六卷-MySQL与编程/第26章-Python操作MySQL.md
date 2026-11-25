# 第 26 章 Python 操作 MySQL（PyMySQL / SQLAlchemy）

## 本章目标

读完这一章，你将能够：

- 用 PyMySQL 连接 MySQL、执行 CRUD
- 理解参数化查询，防止 SQL 注入
- 用 SQLAlchemy ORM 操作数据库
- 管理连接池和事务

---

## 26.1 为什么用 Python 操作 MySQL

Python 是 AI + 安全领域的主力语言。实际项目里，几乎不可能只用命令行操作数据库——你要在程序里读写数据：

- 扫描器把结果写入 MySQL
- AI 脚本从 MySQL 读训练数据
- Web 后端用 MySQL 存用户和日志
- 分析脚本查数据生成报告

这一章讲 Python 操作 MySQL 的两种主流方式：**PyMySQL**（底层、灵活）和 **SQLAlchemy**（ORM、强大）。

---

## 26.2 安装 PyMySQL

```bash
pip install pymysql
```

> **说明**：还有 mysql-connector-python（Oracle 官方）、mysqlclient（C 扩展，快）。PyMySQL 是纯 Python、易安装、最常用之一。三者的 API 类似，学会一个其他都会。

---

## 26.3 连接数据库

```python
import pymysql

# 建立连接
conn = pymysql.connect(
    host='localhost',
    user='secapp',
    password='App@Pass2026!Secure',
    database='vulnscan',
    charset='utf8mb4',
    port=3306
)

# 创建游标
cursor = conn.cursor()

# 执行查询
cursor.execute("SELECT VERSION()")
version = cursor.fetchone()
print(f"MySQL 版本: {version[0]}")

# 关闭
cursor.close()
conn.close()
```

连接参数：

| 参数 | 说明 |
|------|------|
| host | 服务器地址 |
| user / password | 账号密码 |
| database | 数据库名 |
| charset | 字符集（用 utf8mb4） |
| port | 端口（默认 3306） |

> **安全提醒**：密码不要硬编码在代码里！用环境变量或配置文件（加入 .gitignore）。第 12 章讲过 `.gitignore` 和敏感信息保护。

```python
import os
password = os.environ.get('DB_PASSWORD')  # 从环境变量读
```

---

## 26.4 执行 CRUD

### 查询（SELECT）

```python
cursor.execute("SELECT id, host, port, severity FROM scan_results WHERE severity='HIGH'")

# fetchone()：取一行
row = cursor.fetchone()
print(row)  # (1, '192.168.1.10', 3306, 'HIGH')

# fetchall()：取所有行
rows = cursor.fetchall()
for r in rows:
    print(r)

# fetchmany(n)：取 n 行
rows = cursor.fetchmany(10)
```

返回的是元组，可以配合 `DictCursor` 返回字典：

```python
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT id, host, port FROM scan_results LIMIT 3")
for row in cursor.fetchall():
    print(row['host'], row['port'])  # 用列名访问，更清晰
```

### 插入（INSERT）

```python
# ⚠️ 危险：字符串拼接（绝不能这么做！）
# sql = f"INSERT INTO hosts (ip, os) VALUES ('{ip}', '{os}')"

# ✅ 安全：参数化查询
sql = "INSERT INTO hosts (ip, os, status) VALUES (%s, %s, %s)"
cursor.execute(sql, ('192.168.1.20', 'Ubuntu', 'UP'))
conn.commit()  # 增删改必须 commit！
print(f"插入了 {cursor.rowcount} 行，新ID: {cursor.lastrowid}")
```

**关键点**：

- 用 `%s` 作为占位符（不管什么类型都是 %s）
- 参数用元组传入，PyMySQL 会自动转义
- **增删改后必须 `conn.commit()`**，否则不生效
- 这第 19 章讲的 SQL 注入防御——参数化查询

### 批量插入

```python
sql = "INSERT INTO hosts (ip, os, status) VALUES (%s, %s, %s)"
data = [
    ('10.0.0.1', 'Linux', 'UP'),
    ('10.0.0.2', 'Windows', 'UP'),
    ('10.0.0.3', 'Linux', 'DOWN'),
]
cursor.executemany(sql, data)
conn.commit()
print(f"插入了 {cursor.rowcount} 行")
```

`executemany` 比循环 execute 快得多（减少网络往返）。

### 更新和删除

```python
# 更新
sql = "UPDATE hosts SET status=%s WHERE ip=%s"
cursor.execute(sql, ('DOWN', '192.168.1.20'))
conn.commit()

# 删除
sql = "DELETE FROM hosts WHERE ip=%s"
cursor.execute(sql, ('10.0.0.3',))
conn.commit()
```

再次强调：**永远用参数化查询，永远带 WHERE**。

---

## 26.5 事务管理

```python
try:
    conn.begin()  # 开启事务（或 cursor.execute("START TRANSACTION")）

    cursor.execute("UPDATE accounts SET balance=balance-%s WHERE id=%s", (100, 1))
    cursor.execute("UPDATE accounts SET balance=balance+%s WHERE id=%s", (100, 2))

    conn.commit()  # 都成功，提交
    print("转账成功")
except Exception as e:
    conn.rollback()  # 出错，回滚
    print(f"转账失败，已回滚: {e}")
```

培养"出错必回滚"的习惯。

---

## 26.6 完整的扫描器数据写入示例

```python
import pymysql
import os
from datetime import datetime

def save_scan_results(target, results):
    """把扫描结果存入数据库"""
    conn = pymysql.connect(
        host='localhost',
        user=os.environ.get('DB_USER', 'secapp'),
        password=os.environ.get('DB_PASSWORD'),
        database='vulnscan',
        charset='utf8mb4'
    )
    try:
        with conn.cursor() as cursor:
            # 1. 插入任务
            cursor.execute(
                "INSERT INTO scan_tasks (target, scan_type, status) VALUES (%s, %s, %s)",
                (target, 'PORT', 'DONE')
            )
            task_id = cursor.lastrowid

            # 2. 批量插入结果
            sql = """INSERT INTO scan_results (task_id, host, port, severity, detail)
                     VALUES (%s, %s, %s, %s, %s)"""
            data = [(task_id, r['host'], r['port'], r['severity'], r['detail'])
                    for r in results]
            cursor.executemany(sql, data)

        conn.commit()
        print(f"任务 {task_id} 保存成功，{len(results)} 条结果")
        return task_id
    except Exception as e:
        conn.rollback()
        print(f"保存失败: {e}")
        return None
    finally:
        conn.close()

# 使用
results = [
    {'host': '192.168.1.10', 'port': 22, 'severity': 'MEDIUM', 'detail': 'SSH开放'},
    {'host': '192.168.1.10', 'port': 3306, 'severity': 'HIGH', 'detail': 'MySQL暴露'},
]
save_scan_results('192.168.1.10', results)
```

这段代码用了：连接管理、参数化查询、批量插入、事务、异常处理——生产代码的标准结构。

---

## 26.7 SQLAlchemy：ORM 方式

**ORM（Object-Relational Mapping）** 把数据库表映射成 Python 类，用操作对象的方式操作数据库，不用手写 SQL。

安装：

```bash
pip install sqlalchemy
```

### 定义模型

```python
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Host(Base):
    __tablename__ = 'hosts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(64), nullable=False)
    os = Column(String(64))
    status = Column(String(16), default='UP')

# 创建引擎
engine = create_engine(
    'mysql+pymysql://secapp:密码@localhost:3306/security_lab?charset=utf8mb4',
    echo=False  # echo=True 会打印生成的 SQL，调试用
)

# 创建表（如果不存在）
Base.metadata.create_all(engine)

# 创建会话
Session = sessionmaker(bind=engine)
session = Session()
```

### CRUD 操作

```python
# 增
host = Host(ip='192.168.1.30', os='Ubuntu', status='UP')
session.add(host)
session.commit()

# 查
hosts = session.query(Host).filter(Host.status == 'UP').all()
for h in hosts:
    print(h.ip, h.os)

# 改
host = session.query(Host).filter(Host.ip == '192.168.1.30').first()
host.status = 'DOWN'
session.commit()

# 删
session.delete(host)
session.commit()

session.close()
```

ORM 的优点：代码更像 Python、不用记 SQL、跨数据库方便、防注入（自动生成参数化 SQL）。缺点：复杂查询不如原生 SQL 直观、有学习成本、性能略低（一般可忽略）。

> **小白问**：PyMySQL 和 SQLAlchemy 选哪个？
> 简单脚本、需要精细控制 SQL → PyMySQL。大型项目、复杂数据模型、想少写 SQL → SQLAlchemy。两者都值得学。很多项目混用：简单操作用 ORM，复杂查询用原生 SQL。

---

## 26.8 连接池

频繁创建/关闭连接很耗资源。连接池复用连接：

```python
from sqlalchemy import create_engine

engine = create_engine(
    'mysql+pymysql://user:pass@host/db',
    pool_size=10,          # 连接池大小
    max_overflow=20,       # 超出池大小最多再建 20 个
    pool_recycle=3600      # 连接回收时间（秒），防止连接断开
)
```

PyMySQL 本身没有连接池，可以配合 `DBUtils` 或用 SQLAlchemy 的连接池。生产项目一定要用连接池——直接每次新建连接在高并发下会拖垮数据库（第 25 章讲过 max_connections）。

---

## 26.9 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| Access denied | 账号密码错/权限不足 | 检查账号，GRANT 权限 |
| 中文乱码 | 字符集不对 | 连接加 charset='utf8mb4' |
| 修改没生效 | 忘了 commit | 增删改后 conn.commit() |
| 连接断开 | 空闲太久 | pool_recycle 或重连机制 |
| Too many connections | 连接数满 | 用连接池，检查泄露 |

---

## 26.10 本章总结

| 知识点 | 内容 |
|--------|------|
| PyMySQL | 纯 Python 驱动；connect / cursor / execute |
| 参数化查询 | `%s` 占位符 + 元组参数；防 SQL 注入（呼应第 19 章） |
| CRUD | execute / executemany；增删改后 commit |
| DictCursor | 返回字典，按列名访问 |
| 事务 | begin / commit / rollback；出错必回滚 |
| SQLAlchemy | ORM；模型类 + session；免写 SQL |
| 连接池 | pool_size / max_overflow / pool_recycle；生产必备 |
| 安全 | 密码放环境变量；参数化查询；带 WHERE |

---

## 本章练习

1. 用 PyMySQL 连接数据库，查询 `hosts` 表并打印所有行。
2. 用参数化查询插入一条数据，验证 SQL 注入输入（如 `1' OR '1'='1`）不会生效。
3. 用 executemany 批量插入 10 条数据。
4. 写一个带事务的函数：插入任务 + 插入结果，任一失败回滚。
5. 用 SQLAlchemy 定义 Host 模型，完成增删改查。
6. 配置 SQLAlchemy 连接池，理解 pool_size 和 pool_recycle。
7. 思考：PyMySQL 的参数化查询为什么能防注入？和第 19 章的关系？
8. 思考：ORM 的优缺点是什么？什么场景下该用原生 SQL？

---

**下一章预告**：用 C/C++ 操作 MySQL——通过 MySQL Connector/C API，理解底层是怎么和数据库通信的。这是 AI 推理引擎和高性能工具的常见做法。
