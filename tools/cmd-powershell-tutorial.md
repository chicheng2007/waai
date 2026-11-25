# CMD 与 PowerShell 实战教程：Windows 命令行从入门到顺手

> 写给"只会双击图标、一让敲命令就慌"的 Windows 用户。从零讲清 CMD 和 PowerShell 是什么、该学哪个、常用命令怎么用，并结合网安、Python、Git 的真实场景。
> 你不需要背下所有命令——**理解思路 + 常用命令查表**就够了。

**导航**：[仓库 README](../README.md) · [Git 教程](git-tutorial.md) · [Python 路线](python-roadmap.md) · [14 天实战](../START-HERE.md) · [硬件环境](../reference/hardware-setup.md)

---

## 目录

- [一、CMD 和 PowerShell 是什么，该学哪个](#一cmd-和-powershell-是什么该学哪个)
- [二、怎么打开命令行](#二怎么打开命令行)
- [三、先建立思路：命令行的三个基本概念](#三先建立思路命令行的三个基本概念)
- [四、CMD 常用命令](#四cmd-常用命令)
- [五、PowerShell 常用命令](#五powershell-常用命令)
- [六、文件与目录操作对照表](#六文件与目录操作对照表)
- [七、路径、通配符与中文目录](#七路径通配符与中文目录)
- [八、管道与重定向](#八管道与重定向)
- [九、环境变量](#九环境变量)
- [十、PowerShell 执行策略与常见报错](#十powershell-执行策略与常见报错)
- [十一、配合 Git / Python / pip 的实用命令](#十一配合-git--python--pip-的实用命令)
- [十二、网安场景实用例子](#十二网安场景实用例子)
- [十三、命令速查表](#十三命令速查表)
- [十四、练手](#十四练手)

---

## 一、CMD 和 PowerShell 是什么，该学哪个

### 1.1 一句话区分

| | CMD（命令提示符） | PowerShell |
|---|---|---|
| 全称 | Command Prompt，命令提示符 | PowerShell |
| 年龄 | 老（DOS 时代延续） | 新（微软 2006 年推出） |
| 能力 | 基础文件操作、跑程序 | 更强：脚本、对象、系统管理 |
| 命令风格 | `dir`、`copy`、`echo` | `Get-ChildItem`、`Copy-Item`、`Write-Output`（但兼容 CMD 别名） |
| 状态 | 遗留工具，能干基础活 | **微软主推，未来主流** |

### 1.2 该学哪个

**结论：日常主力用 PowerShell，偶尔遇到老教程用 CMD。**

理由：

- 微软现在所有新功能、新工具都优先支持 PowerShell，CMD 基本不再更新。
- PowerShell 能干 CMD 所有事，还多出很多能力（管道传对象、系统管理 cmdlet、脚本）。
- 网上很多新教程、官方文档默认给 PowerShell 命令。
- 但老教程、批处理（`.bat`）、一些老脚本还是 CMD——所以 CMD 常用命令也要认得。

> **好消息**：PowerShell 里可以直接敲 `dir`、`cd`、`copy` 这些 CMD 命令（它们是 PowerShell 的"别名"），所以你从 CMD 过渡到 PowerShell 几乎没有门槛。下文会标出哪些是别名、哪些是 PowerShell 原生命令。

### 1.3 还要认识 Windows Terminal

**Windows Terminal** 是微软的新一代终端窗口，能在一个窗口里开多个标签页（PowerShell、CMD、Git Bash 都能开），界面好看、支持复制粘贴、分屏。Win11 自带，Win10 可从微软商店装。

建议：**用 Windows Terminal 作为"壳"，里面跑 PowerShell**。开始菜单搜 "Terminal" 打开即可。

---

## 二、怎么打开命令行

几种方式，任选：

1. **最快**：`Win + R` → 输入 `powershell` 或 `cmd` → 回车。
2. **开始菜单**：点开始 → 输入 "PowerShell" / "cmd" / "Terminal" → 回车。
3. **在文件夹里直接开**（超实用）：在文件资源管理器地址栏输入 `powershell` 或 `cmd` 后回车，命令行会**直接在当前文件夹打开**——省去 `cd` 半天路径。
4. **PyCharm 里**：底部 **Terminal** 标签就是命令行，默认在项目目录。你装库 `pip install` 就在这里敲。
5. **管理员权限**：开始菜单搜 PowerShell → 右键 → 以管理员身份运行。装系统级工具、改 hosts、跑需要权限的命令时用。

> 看提示符判断当前是什么：
> - CMD：`C:\Users\你的用户名>`
> - PowerShell：`PS C:\Users\你的用户名>`
> - Git Bash：`用户名@电脑 MINGW64 ~ $`

---

## 三、先建立思路：命令行的三个基本概念

### 3.1 命令 = 动词 + 参数

命令行就是"用文字指挥电脑做事"：

```
命令名   参数1   参数2   ...
```

例如：

```powershell
Get-ChildItem -Path C:\ -Force
```

- `Get-ChildItem` 是命令（列出文件）
- `-Path C:\` 和 `-Force` 是参数（指定路径、显示隐藏文件）

CMD 里参数常用 `/` 开头（如 `dir /a`），PowerShell 用 `-` 开头（如 `Get-ChildItem -Force`）。

### 3.2 当前目录（工作目录）

命令行任何时候都"站在"某个文件夹里，这叫**当前目录**。你的命令默认对它操作。

```powershell
Get-Location      # PowerShell：显示当前在哪
cd                # 别名，也能显示当前目录
```

CMD 里直接敲 `cd` 就显示当前路径。

### 3.3 绝对路径 vs 相对路径

- **绝对路径**：从盘符开始的完整路径，如 `C:\Users\me\Desktop\a.txt`——不管你在哪都能定位。
- **相对路径**：相对于当前目录，如 `.\a.txt`（当前目录下的 a.txt）、`..\b.txt`（上一级目录的 b.txt）。

```
.    = 当前目录
..   = 上一级目录
\    = 根目录（当前盘）
```

> 例子：你在 `C:\Users\me\project`，`cd ..` 会到 `C:\Users\me`；`cd .\src` 会进入 project 下的 src 文件夹。

---

## 四、CMD 常用命令

虽然主力用 PowerShell，但这些 CMD 命令你一定会遇到（很多是别名，PowerShell 里也能用）。

### 4.1 目录与文件

| 命令 | 作用 | 例子 |
|---|---|---|
| `dir` | 列出当前目录内容 | `dir` |
| `cd` | 切换目录 / 显示当前目录 | `cd D:\project` |
| `md` / `mkdir` | 新建文件夹 | `mkdir test` |
| `rd` / `rmdir` | 删除空文件夹 | `rmdir test` |
| `copy` | 复制文件 | `copy a.txt b.txt` |
| `move` | 移动 / 重命名 | `move a.txt ..\` |
| `del` | 删除文件 | `del a.txt` |
| `ren` / `rename` | 重命名 | `ren a.txt b.txt` |
| `type` | 显示文本文件内容 | `type a.txt` |
| `cls` | 清屏 | `cls` |

### 4.2 系统与网络

| 命令 | 作用 |
|---|---|
| `echo` | 显示文字 / 开关回显 |
| `where 程序名` | 查找程序在哪（如 `where python`） |
| `tasklist` | 查看正在运行的进程 |
| `taskkill /PID 1234 /F` | 强制结束进程 |
| `ipconfig` | 查看网络配置（IP、网关、DNS） |
| `ping 地址` | 测试网络连通性 |
| `netstat -ano` | 查看端口和连接（网安常用） |
| `tracert 地址` | 追踪路由路径 |
| `nslookup 域名` | 查询 DNS 解析 |
| `systeminfo` | 查看系统详细信息 |
| `findstr "关键词" 文件` | 在文件里搜文本（网安日志分析常用） |

### 4.3 CMD 实用技巧

```cmd
:: 一次执行多个命令用 &
cd D:\project & dir

:: 上一个命令成功才执行下一个用 &&
pip install requests && python test.py

:: 把命令输出存到文件用 >
dir > list.txt

:: 追加到文件用 >>
echo 日志一行 >> log.txt

:: 通配符 * 匹配任意字符
del *.tmp
```

> `::` 是 CMD 注释（也可写 `REM`）。

---

## 五、PowerShell 常用命令

PowerShell 的命令叫 **cmdlet**（读作 command-let），命名规律是"动词-名词"，如 `Get-ChildItem`（获取-子项）、`Set-Location`（设置-位置）。**看懂动词就大概知道命令干嘛**。

### 5.1 常用动词

| 动词 | 含义 | 例子 |
|---|---|---|
| `Get-` | 获取 / 查看 | `Get-Content`（看文件内容） |
| `Set-` | 设置 / 修改 | `Set-Location`（切换目录） |
| `New-` | 新建 | `New-Item`（新建文件/文件夹） |
| `Remove-` | 删除 | `Remove-Item` |
| `Copy-` | 复制 | `Copy-Item` |
| `Move-` | 移动 | `Move-Item` |
| `Rename-` | 重命名 | `Rename-Item` |
| `Test-` | 测试 / 判断 | `Test-Path`（路径是否存在） |
| `Select-` | 筛选 | `Select-String`（搜文本） |

### 5.2 必会的 PowerShell cmdlet

| 命令 | 作用 | CMD 别名 / 对应 |
|---|---|---|
| `Get-ChildItem` | 列出文件 | `dir` / `ls` |
| `Set-Location` | 切换目录 | `cd` |
| `Get-Location` | 显示当前路径 | `pwd` |
| `New-Item` | 新建文件或文件夹 | `md` |
| `Remove-Item` | 删除 | `del` |
| `Copy-Item` | 复制 | `copy` / `cp` |
| `Move-Item` | 移动 | `move` / `mv` |
| `Rename-Item` | 重命名 | `ren` / `mv` |
| `Get-Content` | 看文件内容 | `type` / `cat` |
| `Set-Content` | 写文件 | — |
| `Add-Content` | 追加内容 | — |
| `Clear-Host` | 清屏 | `cls` / `clear` |
| `Write-Output` | 输出文字 | `echo` |
| `Get-Command` | 查命令在哪 / 有哪些命令 | `where` |
| `Get-Help` | 看命令帮助 | — |
| `Get-Process` | 查看进程 | `tasklist` |
| `Stop-Process` | 结束进程 | `taskkill` |
| `Test-NetConnection` | 测试网络端口连通 | — |
| `Resolve-DnsName` | DNS 查询 | `nslookup` |

### 5.3 PowerShell 的几个杀手锏

**① 管道传的是"对象"，不是纯文本**

这是 PowerShell 比 CMD 强的核心。CMD 的管道传来传去是文字，PowerShell 传的是结构化对象，能直接按属性筛选：

```powershell
# 列出当前目录文件，只看大于 1MB 的，按大小排序
Get-ChildItem | Where-Object Length -GT 1MB | Sort-Object Length -Descending
```

**② 通配符与递归**

```powershell
Get-ChildItem -Recurse -Filter *.log     # 递归找所有 log 文件
```

**③ 查看命令帮助**

```powershell
Get-Help Get-ChildItem          # 基本帮助
Get-Help Get-ChildItem -Full    # 完整帮助
Get-ChildItem -?                # 快捷键形式
```

**④ Tab 补全**

敲命令或路径的一部分，按 `Tab` 自动补全——PowerShell 里这是救命功能，路径再长也不怕。

**⑤ 别名**

```powershell
Get-Alias dir        # 查看 dir 是什么命令的别名（答案是 Get-ChildItem）
Get-Alias            # 列出所有别名
```

### 5.4 PowerShell 里执行 Python / pip

和 CMD 一样直接敲：

```powershell
python --version
pip install requests
python script.py
```

> 如果提示"无法将 python 识别为 cmdlet"，说明 Python 没加进 PATH，见 [第九节环境变量](#九环境变量)。

---

## 六、文件与目录操作对照表

一张表看懂"同一件事在两边怎么写"：

| 想做的事 | CMD | PowerShell |
|---|---|---|
| 列出文件 | `dir` | `Get-ChildItem`（或 `dir`/`ls`） |
| 切换目录 | `cd 路径` | `Set-Location 路径`（或 `cd`） |
| 显示当前目录 | `cd` | `Get-Location`（或 `pwd`） |
| 新建文件夹 | `md 名字` | `New-Item -ItemType Directory 名字` |
| 新建空文件 | `type nul > 文件名` | `New-Item -ItemType File 文件名` |
| 删除文件 | `del 文件` | `Remove-Item 文件`（或 `del`） |
| 删除文件夹（含内容） | `rd /s /q 文件夹` | `Remove-Item 文件夹 -Recurse -Force` |
| 复制文件 | `copy 源 目标` | `Copy-Item 源 目标` |
| 移动文件 | `move 源 目标` | `Move-Item 源 目标` |
| 重命名 | `ren 旧 新` | `Rename-Item 旧 新` |
| 看文件内容 | `type 文件` | `Get-Content 文件`（或 `cat`） |
| 搜索文本 | `findstr "关键词" 文件` | `Select-String "关键词" 文件` |
| 清屏 | `cls` | `Clear-Host`（或 `cls`） |

> **删除是可怕的操作**：`Remove-Item -Recurse -Force` 和 `rd /s /q` 会连带子文件夹一起删且**不进回收站**。删之前用 `Get-ChildItem` 确认一遍路径对不对。

---

## 七、路径、通配符与中文目录

### 7.1 路径写法

Windows 路径用反斜杠 `\`：

```
C:\Users\me\Desktop\file.txt
```

- 盘符：`C:\`、`D:\`
- 当前目录：`.`
- 上一级：`..`
- 上两级：`..\..`

> PowerShell 里正斜杠 `/` 通常也能用（它会自动转换），但反斜杠更标准。

### 7.2 路径有空格怎么办

**用引号包起来**：

```powershell
cd "C:\Program Files\Python"
Remove-Item "C:\我的 文件夹\文件.txt"
```

不包引号的话，空格会被当成参数分隔符，命令会报错——这是新手最常见的坑之一。

### 7.3 通配符

| 符号 | 含义 | 例子 |
|---|---|---|
| `*` | 任意多个字符 | `*.log` 所有 log 文件 |
| `?` | 单个字符 | `file?.txt` 匹配 file1.txt |
| `[ ]` | 字符范围 | `[a-z]*.txt` |

### 7.4 中文目录与编码

- PowerShell 现在对中文路径支持很好，直接 `cd "D:\中文目录"` 即可。
- Python 脚本读写中文文件时，建议在代码里指定 `encoding="utf-8"`（见 [Python 路线](python-roadmap.md)）。
- CMD 默认编码可能乱码，可在 CMD 里先敲 `chcp 65001` 切到 UTF-8。

---

## 八、管道与重定向

### 8.1 管道 `|`：把一个命令的输出交给下一个

```powershell
# PowerShell：列出文件 → 只保留 .py → 数一数有几个
Get-ChildItem | Where-Object Extension -EQ ".py" | Measure-Object
```

```cmd
:: CMD：在文件里搜关键词
findstr "admin" access.log
```

管道是命令行的"组合技"，把简单命令串成强大功能。

### 8.2 重定向 `>` 和 `>>`

```powershell
python analyze.py > result.txt      # 输出写入文件（覆盖）
python analyze.py >> result.txt     # 输出追加到文件末尾
```

**常见用途**：把脚本的运行结果、报错存成文件留档——取证和分析工作里经常要这么做。

错误输出也想存：

```powershell
python analyze.py 2>&1 > all.txt    # 把标准输出和错误输出都存进去
```

---

## 九、环境变量

### 9.1 什么是环境变量

环境变量是系统级的"全局变量"，存着 PATH、临时目录、用户名等信息。程序靠它找到 Python、Git 这些工具在哪。

### 9.2 查看

```powershell
$env:PATH                    # PowerShell：查看 PATH
Get-ChildItem Env:           # 查看所有环境变量
echo %PATH%                  # CMD：查看 PATH
```

### 9.3 PATH 是什么，为什么重要

PATH 是一串文件夹路径列表。当你在命令行敲 `python`，系统会**按 PATH 里的顺序**逐个文件夹找 `python.exe`，找到就执行。

- 装 Python 时如果没勾"Add Python to PATH"，敲 `python` 就会"无法识别"——因为系统不知道去哪找。
- 解决：把 Python 安装目录（和 `Scripts` 目录）加到 PATH。

### 9.4 临时添加 PATH（当前窗口有效）

```powershell
$env:PATH += ";C:\Python311"
```

### 9.5 永久修改 PATH（图形界面最稳）

设置 → 系统 → 关于 → 高级系统设置 → 环境变量 → 在 Path 里添加。改完**重新打开命令行**才生效。

> 用 `setx` 命令也能永久设置，但容易截断旧值，新手建议用图形界面。

---

## 十、PowerShell 执行策略与常见报错

### 10.1 执行策略：脚本跑不了

PowerShell 默认限制运行 `.ps1` 脚本，双击或运行时会报"无法加载文件，因为在此系统上禁止运行脚本"。

查看当前策略：

```powershell
Get-ExecutionPolicy
```

改成允许本地脚本（推荐这样设置，兼顾安全）：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

- `RemoteSigned`：本地写的脚本能跑，网上下载的要有签名才能跑——安全与方便的平衡。
- 改完不用重启，但要用**管理员权限**或限定 `-Scope CurrentUser`（当前用户）。

### 10.2 其他常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| "无法将 xxx 识别为 cmdlet" | 命令不存在或没在 PATH 里 | 检查拼写；确认软件装好并加了 PATH |
| "拒绝访问" | 权限不够 | 用管理员身份运行命令行 |
| "系统找不到指定的路径" | 路径写错 / 有空格没加引号 | 用 `Get-Location` 确认位置，路径加引号 |
| "another process is using the file" | 文件被别的程序占用 | 关掉占用程序（PyCharm、Excel 等） |
| 中文乱码 | 编码不一致 | PowerShell 用 UTF-8；CMD 用 `chcp 65001` |

---

## 十一、配合 Git / Python / pip 的实用命令

### 11.1 Git（详见 [Git 教程](git-tutorial.md)）

```powershell
git status              # 看状态
git add .               # 暂存
git commit -m "说明"    # 提交
git push                # 推送
git pull                # 拉取
```

PowerShell 里 `git` 命令完全通用。注意：如果提交信息含特殊字符（如 `!`、引号），用双引号包起来。

### 11.2 Python / pip

```powershell
python --version
pip install requests pandas
pip list                        # 看装了哪些库
pip freeze > requirements.txt   # 导出依赖清单
python -m venv venv             # 建虚拟环境
.\venv\Scripts\activate         # 激活虚拟环境（Windows）
```

> PowerShell 里激活虚拟环境要用 `.\venv\Scripts\activate`（前面有 `.\`），直接敲 `venv\Scripts\activate` 可能没反应——这是 PowerShell 的安全机制。

### 11.3 快速判断命令在哪

```powershell
Get-Command python       # PowerShell：显示 python 可执行文件位置
where python             # CMD / Git Bash：同样功能
```

---

## 十二、网安场景实用例子

> ⚠️ 以下命令只用于**自己的机器 / 授权靶场**，别拿去扫别人。

### 12.1 查看本机网络配置

```powershell
ipconfig                    # 看 IP、网关、DNS
ipconfig /flushdns          # 清空 DNS 缓存
Get-NetIPAddress            # PowerShell：看所有 IP 地址
```

### 12.2 查看端口和连接（排查后门 / 找服务）

```cmd
netstat -ano                # CMD：列出所有连接和监听端口，带 PID
```

```powershell
Get-NetTCPConnection -State Listen   # PowerShell：看正在监听的端口
```

结合 `tasklist` / `Get-Process` 能查出"哪个进程占了某个端口"：

```powershell
# 找占用 8080 端口的进程 PID，再查进程名
netstat -ano | findstr ":8080"
tasklist | findstr "进程PID"
```

### 12.3 在日志里搜可疑关键词

```powershell
Select-String -Path access.log -Pattern "admin","wp-login","UNION SELECT"
```

```cmd
findstr /i "admin wp-login" access.log
```

这正是你日志分析项目里正则/关键词筛查的命令行版本。

### 12.4 测试目标端口通不通（授权环境）

```powershell
Test-NetConnection 192.168.1.1 -Port 80
```

### 12.5 批量重命名取证文件

```powershell
# 把当前目录所有 .jpg 按序号重命名
$i = 1
Get-ChildItem *.jpg | ForEach-Object { Rename-Item $_ ("evidence_" + $i++ + ".jpg") }
```

### 12.6 查看进程和数字签名（排查可疑程序）

```powershell
Get-Process | Select-Object Name, Id, Path
Get-ChildItem C:\Windows\System32\*.exe | Get-AuthenticodeSignature
```

---

## 十三、命令速查表

| 想做的事 | PowerShell | CMD |
|---|---|---|
| 列文件 | `ls` / `Get-ChildItem` | `dir` |
| 进目录 | `cd 路径` | `cd 路径` |
| 回上一级 | `cd ..` | `cd ..` |
| 当前路径 | `pwd` | `cd` |
| 建文件夹 | `mkdir 名` | `md 名` |
| 删文件 | `del 文件` | `del 文件` |
| 删文件夹(含内容) | `rm -r 文件夹` | `rd /s /q 文件夹` |
| 复制 | `cp 源 目标` | `copy 源 目标` |
| 移动/改名 | `mv 源 目标` | `move` / `ren` |
| 看文件内容 | `cat 文件` | `type 文件` |
| 搜文本 | `Select-String "词" 文件` | `findstr "词" 文件` |
| 清屏 | `cls` | `cls` |
| 看进程 | `Get-Process` / `ps` | `tasklist` |
| 杀进程 | `Stop-Process -Id 号` | `taskkill /PID 号 /F` |
| 看端口 | `Get-NetTCPConnection` | `netstat -ano` |
| 查 IP | `ipconfig` | `ipconfig` |
| 查命令位置 | `Get-Command 名` | `where 名` |
| 看帮助 | `Get-Help 命令` / `命令 -?` | `命令 /?` |
| 环境变量 | `$env:PATH` | `echo %PATH%` |
| 清 DNS 缓存 | `ipconfig /flushdns` | 同左 |

---

## 十四、练手

### 练习 1：文件操作（5 分钟）

1. 打开 PowerShell，在桌面建文件夹：`cd ~/Desktop` 然后 `mkdir cmd-practice`。
2. 进去：`cd cmd-practice`。
3. 建个文件写点东西：`"hello" > test.txt`，再 `cat test.txt` 看。
4. 复制：`cp test.txt test2.txt`，用 `ls` 确认。
5. 改名：`mv test2.txt renamed.txt`。
6. 删除：`del renamed.txt`，`ls` 确认没了。

### 练习 2：管道与筛选（5 分钟）

1. 在项目目录执行 `ls | Select-Object Name, Length`（只看文件名和大小）。
2. 试 `ls | Where-Object Length -GT 10000`（只看大于 10KB 的）。
3. 把结果存起来：`ls > filelist.txt`，然后 `cat filelist.txt`。

### 练习 3：查看本机网络（5 分钟）

1. `ipconfig` 找到自己的 IP。
2. `netstat -ano | findstr "LISTENING"` 看本机监听端口。
3. `Get-Process` 看进程列表，理解每行含义。

### 练习 4：Git + 命令行组合（10 分钟）

在你自己的项目目录里，打开 PowerShell 完成一次完整提交：

```powershell
git status
git add .
git commit -m "命令行练习：第一次提交"
git log --oneline
```

---

## 最后几句

- **主力用 PowerShell，CMD 命令认得就行**——它们是别名，大部分能直接在 PowerShell 里用。
- **多用 Tab 补全和 `Get-Help`**：忘了命令怎么写，问它比问搜索引擎快。
- **危险操作前先看清路径**：尤其 `Remove-Item -Recurse -Force`，删之前 `ls` 一遍。
- **命令行是网安的基本功**：Wireshark、Nmap、Metasploit、各种脚本最终都要落到命令行上。现在练熟，后面玩靶场会顺很多。

> 从今天起，试着每天用命令行做一件事——哪怕是 `cd` 到项目目录再 `python script.py`。敲得多了，命令行会从"害怕"变成"顺手"。

---

*配套：Git 见 [git-tutorial.md](git-tutorial.md)，Python 见 [python-roadmap.md](python-roadmap.md)，学习路线见 [README](../README.md)。*
