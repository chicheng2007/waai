# 第 6 章 文本处理三剑客：grep / sed / awk

## 本章目标

读完这一章，你将能够：

- 用 `grep` 精准搜索文本，掌握正则、排除、上下文等技巧
- 用 `sed` 做文本替换、删除、插入
- 用 `awk` 按列提取、统计、格式化数据
- 把三剑客组合起来，完成复杂的日志分析任务
- 理解为什么"文本处理"是安全分析的看家本领

---

## 6.1 为什么三剑客如此重要

Linux 里几乎所有重要信息都是文本：日志、配置、进程列表、网络状态。安全分析 80% 的工作，本质是"从海量文本里找到异常"。三剑客就是为这件事而生的：

| 工具 | 擅长 | 类比 |
|------|------|------|
| `grep` | **找**：按模式搜索、过滤行 | 搜索引擎 |
| `sed` | **改**：替换、删除、插入文本 | 查找替换编辑器 |
| `awk` | **算**：按列处理、统计、报表 | 表格处理器 / 编程语言 |

三者配合管道（第 7 章），能写出极其强大的一行命令。学会它们，你会从"一条条看日志"升级到"一秒钟分析百万行"。

---

## 6.2 grep：搜索过滤

### 6.2.1 基本用法

```bash
grep "关键词" 文件
```

```bash
grep "Failed password" /var/log/auth.log
```

在文件里找含 "Failed password" 的行并输出。

不指定文件时，从标准输入读取（配合管道）：

```bash
cat /var/log/auth.log | grep "Failed"
```

### 6.2.2 常用选项

| 选项 | 作用 |
|------|------|
| `-i` | 忽略大小写（ignore case） |
| `-n` | 显示行号 |
| `-v` | 反向匹配（输出**不含**关键词的行） |
| `-c` | 只统计匹配的行数 |
| `-l` | 只列出包含匹配的文件名 |
| `-r` | 递归搜索目录 |
| `-E` | 使用扩展正则表达式 |
| `-w` | 全词匹配 |
| `-A n` | 显示匹配行之后的 n 行（After） |
| `-B n` | 显示匹配行之前的 n 行（Before） |
| `-C n` | 前后各显示 n 行（Context） |

### 6.2.3 安全实战示例

```bash
# 统计暴力破解尝试次数
grep -c "Failed password" /var/log/auth.log

# 找出成功登录的记录（排除 failed）
grep "Accepted password" /var/log/auth.log

# 找出来自特定 IP 的所有记录，并显示行号
grep -n "192.168.1.100" /var/log/auth.log

# 递归搜索 /var/log 下所有含 "ERROR" 的文件
grep -rl "ERROR" /var/log/

# 显示匹配行前后各 2 行（看上下文）
grep -C 2 "Failed password" /var/log/auth.log

# 排除注释和空行（看配置文件真正生效的内容）
grep -v "^#" /etc/ssh/sshd_config | grep -v "^$"
```

### 6.2.4 正则表达式入门

`grep` 的强大在于支持**正则表达式**（第 14 章详讲，这里先入门）：

| 符号 | 含义 | 示例 |
|------|------|------|
| `.` | 任意一个字符 | `a.c` 匹配 abc、a1c |
| `*` | 前一个字符重复 0 次或多次 | `ab*` 匹配 a、ab、abb |
| `^` | 行首 | `^root` 匹配以 root 开头的行 |
| `$` | 行尾 | `bash$` 匹配以 bash 结尾的行 |
| `[]` | 字符集合 | `[0-9]` 匹配任意数字 |
| `\|` | 或（基本正则需转义） | `grep "error\|warn" log` |

示例：

```bash
# 找出以 root 开头的用户行
grep "^root" /etc/passwd

# 找出以 /bin/bash 结尾的行（可登录的用户）
grep "/bin/bash$" /etc/passwd

# 扩展正则（用 grep -E，\| 直接写 |）
grep -E "error|warn|fail" /var/log/syslog
```

> **小白问**：什么是正则表达式？
>
> 正则表达式（regex）是一种"描述文本模式"的语言。比如 `\d{3}` 表示"三个数字"，`^A` 表示"以 A 开头"。用它能精确描述"我要找什么样的文本"，比普通关键词强大得多。第 14 章会系统学习。

---

## 6.3 sed：流编辑器

`sed` 是"流编辑器"（stream editor），逐行读取文本、按指令处理、输出结果。最常用的是**替换**。

### 6.3.1 替换

语法：

```bash
sed 's/旧内容/新内容/' 文件
```

```bash
# 把文件里的 foo 替换成 bar（每行只替换第一个）
sed 's/foo/bar/' file.txt

# 全局替换（每行所有匹配都替换）
sed 's/foo/bar/g' file.txt

# 直接修改文件（-i，in-place）
sed -i 's/foo/bar/g' file.txt

# 修改前备份（-i.bak 会生成 file.txt.bak 备份）
sed -i.bak 's/foo/bar/g' file.txt
```

> ⚠️ `sed -i` 直接改文件，不可逆。生产环境先用 `-i.bak` 备份，或先不加 `-i` 预览结果。

### 6.3.2 定界符替换

当内容里有 `/` 时（如路径），可以用其他字符做定界符：

```bash
sed 's#/bin/bash#/usr/bin/zsh#g' file.txt
```

用 `#` 代替 `/`，避免转义地狱。

### 6.3.3 删除行

```bash
sed '1d' file.txt          # 删除第 1 行
sed '$d' file.txt          # 删除最后一行
sed '/pattern/d' file.txt  # 删除含 pattern 的行
sed '2,5d' file.txt        # 删除第 2 到 5 行
```

### 6.3.4 打印指定行

```bash
sed -n '1,5p' file.txt           # 只打印 1-5 行
sed -n '/pattern/p' file.txt     # 只打印匹配的行
```

`-n` 是"静默模式"，默认不输出，配合 `p` 命令只打印指定的行。

### 6.3.5 安全实战示例

```bash
# 去掉配置文件的注释和空行，看生效配置
sed '/^#/d; /^$/d' /etc/ssh/sshd_config

# 提取日志里的 IP（假设 IP 在第 4 个字段，用 sed 配合正则）
grep "Failed password" /var/log/auth.log | sed -E 's/.*from ([0-9.]+).*/\1/'

# 批量改配置：把实验环境所有的 8080 端口改成 8081
sed -i 's/8080/8081/g' /etc/myapp/*.conf
```

---

## 6.4 awk：文本分析的编程语言

`awk` 不只是命令，是一门完整的文本处理语言。它把每一行按"字段"切开，让你对列做操作。

### 6.4.1 按列提取

默认以空白（空格/制表符）分隔字段：

```bash
awk '{print $1}' file.txt          # 打印第 1 列
awk '{print $1, $3}' file.txt      # 打印第 1、3 列
awk '{print $NF}' file.txt         # 打印最后一列（NF = 字段数）
awk '{print NR, $0}' file.txt      # 打印行号和整行
```

```bash
# 看当前用户列表（/etc/passwd 用冒号分隔，第一列是用户名）
awk -F: '{print $1}' /etc/passwd
```

`-F:` 指定分隔符为冒号。

> **小白问**：`$1`、`$NF` 是什么？
>
> awk 把每行切成若干字段，`$1` 是第 1 个，`$2` 是第 2 个……`$0` 是整行，`$NF` 是最后一个字段（NF = Number of Fields，字段总数）。这是 awk 最核心的概念。

### 6.4.2 条件过滤

```bash
awk '$3 > 100 {print $1, $3}' data.txt          # 第 3 列大于 100 的行
awk '$1 == "root" {print $0}' /etc/passwd       # 第 1 列等于 root
awk '/Failed/ {print $1}' /var/log/auth.log     # 含 Failed 的行，打印第 1 列
```

### 6.4.3 BEGIN 和 END

```bash
awk 'BEGIN {print "开始处理"} {print $1} END {print "处理完毕"}' file.txt
```

- `BEGIN`：处理第一行之前执行一次
- 中间的块：对每行执行
- `END`：处理完所有行后执行一次

### 6.4.4 统计与计算

这是 awk 的杀手锏：

```bash
# 统计文件总行数
awk 'END {print NR}' file.txt

# 求和（假设第 2 列是数字）
awk '{sum += $2} END {print sum}' data.txt

# 统计每个 IP 出现的次数
awk '{count[$1]++} END {for (ip in count) print ip, count[ip]}' access.log

# 找出访问量最大的 IP（排序配合）
awk '{count[$1]++} END {for (ip in count) print ip, count[ip]}' access.log | sort -rn | head
```

`count[$1]++` 是关联数组（用 IP 作 key 计数），`for (ip in count)` 遍历结果。这就是用几行代码写出的统计程序。

### 6.4.5 格式化输出

```bash
awk '{printf "%-20s %10d\n", $1, $2}' data.txt
```

`printf` 能精确控制格式，`%-20s` 是左对齐宽 20 的字符串，`%10d` 是宽 10 的整数。

### 6.4.6 安全实战示例

```bash
# 从认证日志里提取所有失败登录的 IP，统计次数，排序
grep "Failed password" /var/log/auth.log \
  | awk '{print $11}' \
  | sort | uniq -c | sort -rn | head

# 找出登录成功的用户和时间
grep "Accepted password" /var/log/auth.log | awk '{print $1, $2, $9, $11}'

# 统计每个用户的失败登录次数
grep "Failed password" /var/log/auth.log | awk '{for(i=1;i<=NF;i++) if($i=="for") print $(i+1)}' | sort | uniq -c
```

---

## 6.5 三剑客组合：经典日志分析

来看一个完整的实战：分析 Web 访问日志，找出可疑行为。

假设日志格式（Nginx combined）：

```bash
192.168.1.10 - - [25/Nov/2026:10:30:00 +0800] "GET /index.html HTTP/1.1" 200 1234 ...
```

任务：找出访问量前 10 的 IP。

```bash
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head
```

拆解这条命令的数据流：

1. `awk '{print $1}'` → 提取每行的第一个字段（IP）
2. `sort` → 排序（让相同 IP 相邻）
3. `uniq -c` → 统计每个 IP 出现次数
4. `sort -rn` → 按次数数字倒序排（-r 逆序，-n 按数字）
5. `head` → 取前 10

任务：找出状态码 404 最多的 URL（可能在扫描）：

```bash
awk '$9 == 404 {print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head
```

任务：找出 1 分钟内请求超过 100 次的 IP（疑似 CC 攻击）：

```bash
awk '{print $1, $4}' /var/log/nginx/access.log | cut -d: -f1 | sort | uniq -c | sort -rn | head
```

这些命令是安全分析师日常工作的缩影——**一条命令，百万行日志，秒级出结果**。

---

## 6.6 相关小工具

| 命令 | 作用 |
|------|------|
| `sort` | 排序；`-n` 数字排序，`-r` 逆序，`-k` 按列排 |
| `uniq` | 去重（通常配合 sort）；`-c` 计数，`-d` 只显示重复 |
| `cut` | 按列/字符切分；`-d` 分隔符，`-f` 字段 |
| `tr` | 字符转换/删除；如 `tr 'a-z' 'A-Z'` |
| `paste` | 按行合并文件 |

```bash
# cut 示例：取 /etc/passwd 的用户名和 shell
cut -d: -f1,7 /etc/passwd

# tr 示例：把逗号换成换行
echo "a,b,c" | tr ',' '\n'
```

---

## 6.7 常见报错与解决

| 报错 | 原因 | 解决 |
|------|------|------|
| grep 无输出 | 关键词不匹配 / 大小写 / 空格 | 加 `-i`；检查原文；用正则放宽 |
| `sed: -e expression #1` | 替换语法错误 | 检查 `s///` 的斜杠和引号 |
| awk 输出整行 | 忘了写 `{print $n}` | 补上 print 动作 |
| 正则不生效 | 用了基本正则的 `|` | 改用 `grep -E` 或转义 |

---

## 6.8 本章总结

| 工具 | 核心用法 |
|------|---------|
| `grep` | `grep -i/-n/-v/-c/-E/-A/-B/-C "模式" 文件`；正则搜索过滤 |
| `sed` | `sed 's/旧/新/g'` 替换；`/pattern/d` 删行；`-i` 直接改文件 |
| `awk` | `awk -F: '{print $1, $NF}'` 按列提取；`BEGIN/END` 统计计算 |
| 正则 | `^` 行首、`$` 行尾、`.` 任意、`*` 重复、`[]` 集合、`|` 或 |
| 组合 | `grep → awk → sort → uniq -c → sort -rn → head` 是日志分析黄金流水线 |

---

## 本章练习

1. 用 grep 统计 `/var/log/auth.log` 里 "Failed password" 的次数。
2. 用 `grep -E` 一次搜索 error、warn、fail 三种关键词。
3. 复制一个配置文件，用 sed 批量替换里面的某个值，先用预览、再用 `-i.bak` 修改。
4. 用 awk 提取 `/etc/passwd` 里所有能登录（shell 是 /bin/bash）的用户名。
5. 用 awk 统计一个文本文件里每个单词出现的次数，按次数倒序排。
6. 用 `awk '{print $1}' 日志 | sort | uniq -c | sort -rn | head` 分析你系统里某个日志的 IP 分布。
7. 思考：为什么"文本处理三剑客"对安全分析师特别重要？

---

**下一章预告**：我们将学习管道、重定向与通配符——这些是把命令"连接成流水线"的胶水。掌握了它们，三剑客的威力才能完全释放。
