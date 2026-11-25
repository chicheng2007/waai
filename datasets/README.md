# 练习用日志数据集

> 250 份模拟 Web 访问日志，专门用于练《[3 天语法急救包](../guides/SYNTAX-BOOTCAMP.md)》和《[14 天实战计划](../START-HERE.md)》里的日志分析代码。
> **全是模拟数据，IP 均为示例地址，不对应任何真实攻击。**

---

## 文件说明

| 文件 | 是什么 | 怎么用 |
|---|---|---|
| `generate_logs.py` | 生成脚本 | 右键 Run，重新生成 250 份日志（结果固定可复现）|
| `access-logs.zip` | 250 份日志的压缩包 | 下载解压，得到 `access_001.log` ~ `access_250.log` |
| `access-logs/` | 解压后的目录（本地） | 你的分析代码读这里的文件 |

**为什么打包成 zip**：250 个小文件全塞进 GitHub 又乱又难翻，打包成一个 zip 下载后解压即可。想改数据构成（攻击比例、路径、IP）就改 `generate_logs.py` 再跑一遍。

---

## 每份日志长什么样

Apache/Nginx combined 格式，每份 40~90 行，示例：

```text
45.33.22.11 - - [25/Nov/2026:03:12:44 +0800] "GET /wp-login.php HTTP/1.1" 404 178 "-" "nikto/2.1.6"
192.168.1.100 - - [25/Nov/2026:03:15:02 +0800] "GET /index.html HTTP/1.1" 200 1234 "-" "Mozilla/5.0 ..."
```

一行按空格切开，字段依次是：**IP、时间、请求方法+路径+协议、状态码、响应大小、来源、User-Agent**。

---

## 数据里藏了什么（练习目标）

数据里混了正常流量和 4 类攻击，等你来分析揪出来：

| 恶意 IP | 行为 | 特征 |
|---|---|---|
| `45.33.22.11` | 敏感路径扫描 | 狂访问 `/admin`、`/wp-login.php` |
| `103.76.50.180` | 敏感文件探测 | `/.git/config`、`.env`、`backup.sql` |
| `185.220.101.45` | SQL 注入 | URL 里有 `UNION SELECT`、`OR '1'='1` |
| `91.240.118.172` | 暴力破解 | 大量 `POST /login` 且状态码 `401` |

另外还有**攻击工具 UA**：`sqlmap`、`nikto`、`python-requests`、`masscan`——只看 User-Agent 也能发现异常。

> ⚠️ 想先看答案就别往下翻。练完再对。

<details>
<summary>点击展开：参考答案 / 分析思路</summary>

**1. 访问次数最多的 IP 往往是攻击者**（用 `Counter` 统计）
```python
from collections import Counter
ips = []
for line in open("access_001.log", encoding="utf-8"):
    ips.append(line.split()[0])
print(Counter(ips).most_common(5))
```

**2. 敏感路径命中**（`"/admin" in line or "/wp-login" in line`）

**3. 状态码 401 大量出现** = 暴力破解信号

**4. User-Agent 是工具名**（`"sqlmap" in line`）几乎是实锤

**5. SQL 注入特征**（`"UNION SELECT" in line` 或 `%27` 这种编码的引号）

</details>

---

## 配套练习（按难度）

| 难度 | 任务 | 对应 |
|---|---|---|
| ⭐ | 统计单个文件里每个 IP 访问次数，找出 Top 5 | 急救包第 2 天 / 实战第 1 天 |
| ⭐⭐ | 找出所有访问 `/admin`、`/wp-login.php` 的可疑 IP | 实战第 3 天 |
| ⭐⭐ | 统计状态码分布，看 401/404 占比 | 实战第 6 天 |
| ⭐⭐⭐ | 批量扫描全部 250 个文件，汇总出"跨文件高频恶意 IP" | 实战第 8 天 |
| ⭐⭐⭐⭐ | 把可疑记录喂给本地 Qwen3.5-9B，让它研判攻击类型 | 实战第 10 天 |

**批量读所有文件的起手式**（用到 `for` + `glob`）：
```python
import glob
for path in glob.glob("access-logs/*.log"):
    with open(path, encoding="utf-8") as f:
        for line in f:
            pass  # 在这里分析每一行
```

---

## 法律声明

本数据集为程序随机生成的模拟数据，IP 地址为文档示例地址，仅用于编程与数据分析学习，不构成任何真实攻击行为，也不得用于任何未授权场景。

---

*生成脚本：`generate_logs.py`（固定随机种子 42，结果可复现）· 生成日期：2026-11-25*
