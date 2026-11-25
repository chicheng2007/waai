# Git 从入门到实战：网安学生的代码管理手册

> 这是一份写给"只会点点点、没系统用过 Git"的人的中文教程。不讲玄学，从"为什么要用 Git"讲起，到能独立管理自己的 GitHub 仓库、每天打卡、做项目版本管理。
> 你不需要背命令——**理解模型 + 常用命令查表**就够了。

**导航**：[仓库 README](../README.md) · [14 天实战](../START-HERE.md) · [每日打卡](../checkin-log.md) · [Python 路线](python-roadmap.md) · [硬件环境](../reference/hardware-setup.md)

---

## 目录

- [一、Git 到底是什么，为什么你必须会](#一git-到底是什么为什么你必须会)
- [二、先建立心智模型：三个区 + 一次提交](#二先建立心智模型三个区--一次提交)
- [三、第一次使用：安装与配置](#三第一次使用安装与配置)
- [四、本地最常用的 10 个命令](#四本地最常用的-10-个命令)
- [五、连接 GitHub：clone / push / pull](#五连接-githubclone--push--pull)
- [六、每天怎么用它：两种真实工作流](#六每天怎么用它两种真实工作流)
- [七、分支：大胆试错而不弄坏主线](#七分支大胆试错而不弄坏主线)
- [八、PyCharm 里用 Git（图形界面）](#八pycharm-里用-git图形界面)
- [九、常见报错与急救](#九常见报错与急救)
- [十、.gitignore 与隐私红线](#十gitignore-与隐私红线)
- [十一、命令速查表](#十一命令速查表)
- [十二、练手：用 Git 管理你的打卡和项目](#十二练手用-git-管理你的打卡和项目)

---

## 一、Git 到底是什么，为什么你必须会

### 1.1 一句话理解 Git

**Git 是一个"给文件拍照片"的工具**：每当你完成一个阶段，就拍一张照片（提交），以后任何时候都能回到那张照片的状态。

想象你写一篇课程报告：

- 不用 Git：你会存成 `报告_初稿.docx`、`报告_改1.docx`、`报告_最终版.docx`、`报告_最终版2.docx`、`报告_真的最终版.docx`……一周后你自己都分不清哪个是最新的。
- 用 Git：只有一个 `报告.docx`，但每次改动都记下来，随时能看"第三版改了什么""回到第二版"。

**Git 就是代码的"时光机 + 版本相册"。**

### 1.2 Git 和 GitHub 不是一回事（新手最容易混）

| 名词 | 是什么 | 类比 |
|---|---|---|
| **Git** | 装在你电脑上的版本管理软件 | 相机 |
| **GitHub** | 把 Git 拍的照片存到云端的网站 | 云相册 |

- Git 可以**完全离线**用：不联网也能拍照片、回看历史。
- GitHub 只是把你的"照片"同步到网上，方便备份、展示、协作。
- 你用的 `https://github.com/chicheng2007/waai` 就是 GitHub 上的一个仓库网页。

### 1.3 为什么网安学生尤其要会

1. **作品集就是简历**：GitHub 主页是你技术能力最直接的证明。面试时"我做过一个 AI 日志研判工具，代码在这"比说一百句都管用。
2. **打卡可视化**：每天 commit 一次，绿色方格连成一片，坚持看得见——这是最好的自律反馈。
3. **实验可回退**：做 CTF、写攻击脚本、调模型时，改崩了能一键回到能跑的版本，不至于推倒重来。
4. **协作基础**：以后参加 CTF 战队、护网演练、团队项目，全靠 Git 协作。
5. **职业必备**：安全开发、SOC、逆向岗位，Git 是面试必问的基础技能。

> 你已经用 GitHub 管理这个学习仓库了——学会 Git 能让你从"靠工具网页手动传文件"升级到"命令行/图形界面高效管理"。

---

## 二、先建立心智模型：三个区 + 一次提交

这是理解 Git 的关键，搞懂这一节，后面所有命令都顺了。

### 2.1 三个区

Git 把你的文件分成三个"区域"：

```
  工作区              暂存区              本地仓库
(working dir)      (staging area)       (repository)
 你正在改的文件  →  git add 放进来  →  git commit 拍照片
   .py / .md         准备拍照的           已存档的历史
                     改动清单
```

1. **工作区**：你电脑硬盘上能看到的文件夹，你用 PyCharm 改的就是这里。
2. **暂存区（Stage）**：一个"待提交清单"。你 `git add` 就是把改动放进这个清单，表示"这些我要拍进照片"。
3. **本地仓库（Repository）**：`.git` 隐藏文件夹里存的历史记录。`git commit` 把暂存区的内容正式拍成一张照片。

### 2.2 一个完整流程长这样

```bash
# 1. 你改了 checkin-log.md（工作区变了）
# 2. 把改动放进暂存区
git add checkin-log.md

# 3. 拍一张照片（提交），附上一句说明
git commit -m "打卡：完成第3天日志分析"

# 此时工作区改动已存档，随时能回看
```

**为什么要"暂存区"这一步？** 因为它让你能**精确控制**每次提交包含哪些改动。你今天改了 3 个文件，但只想先提交其中 1 个，就只 `add` 那 1 个。这是 Git 比"整文件夹备份"强大的地方。

### 2.3 用生活比喻记牢

把 Git 想象成**做饭拍照发朋友圈**：

- **工作区** = 你在厨房炒菜（正在改文件）
- **暂存区** = 摆盘、挑选要拍进照片的菜（`git add`）
- **commit** = 按快门，并写一句配文"今日晚餐"（`-m "说明"`）
- **push** = 发到朋友圈（`git push` 到 GitHub）

**记住这条主线**：改文件 → add → commit → push。所有命令都是围绕它展开的。

---

## 三、第一次使用：安装与配置

### 3.1 安装 Git

- **Windows**：去 [git-scm.com](https://git-scm.com/download/win) 下载安装包，一路默认安装即可。装完后开始菜单有 **Git Bash**（一个命令行窗口）。
- **macOS**：`brew install git` 或安装 Xcode 命令行工具。
- **Linux**：`sudo apt install git`（Ubuntu/Debian）。

验证装好了：

```bash
git --version
# 输出类似 git version 2.45.1 就成功
```

### 3.2 第一次必须配置的身份

Git 每次提交都要知道"是谁提交的"，所以第一次用要设置用户名和邮箱：

```bash
git config --global user.name "你的用户名"
git config --global user.email "你的邮箱@example.com"
```

> ⚠️ **隐私提示**：`user.email` 会显示在提交记录里。如果你在意隐私，可以用 GitHub 提供的 noreply 邮箱（在 GitHub 设置 → Emails 里能找到），或在本地用一个不暴露真实身份的邮箱。**别用能反查到你真实身份的邮箱提交公开仓库**。

查看配置：

```bash
git config --list
```

### 3.3 让命令行显示中文不乱码（Windows）

```bash
git config --global core.quotepath false
```

---

## 四、本地最常用的 10 个命令

不用背，用多了自然记住。每个都给出"什么时候用"。

### 4.1 `git init` —— 把一个文件夹变成 Git 仓库

```bash
cd 你的项目文件夹
git init
```

执行后文件夹里多出一个隐藏的 `.git` 目录——从这一刻起，这个文件夹就被 Git 管起来了。

### 4.2 `git status` —— 我现在是什么状态（最常用！）

```bash
git status
```

它告诉你：哪些文件改了、哪些已暂存、哪些还没跟踪。**不确定下一步该干嘛时，先敲这个。**

### 4.3 `git add` —— 把改动放进暂存区

```bash
git add 文件名              # 添加单个文件
git add .                  # 添加当前目录所有改动（最常用）
git add *.py               # 添加所有 .py 文件
```

### 4.4 `git commit` —— 拍照片存档

```bash
git commit -m "这次改了什么"
```

**`-m` 后面的说明要写清楚**，这是给你自己和别人看的。好的说明："修复登录状态码统计错误"；差的说明："更新""123""xxx"。

### 4.5 `git log` —— 看历史照片

```bash
git log                    # 完整历史
git log --oneline          # 每条压缩成一行（推荐）
```

能看到每次提交的哈希值、作者、时间、说明。

### 4.6 `git diff` —— 看我改了什么

```bash
git diff                   # 工作区 vs 暂存区
git diff --staged          # 暂存区 vs 上次提交
```

提交前扫一眼，确认没把不该改的改了。

### 4.7 `git restore` —— 撤销没提交的改动

```bash
git restore 文件名          # 把某个文件恢复到上次提交的状态
git restore .              # 撤销所有未提交的改动（谨慎！）
```

**救命命令**：改崩了、想推倒重来时用。注意：一旦 `restore`，未提交的改动就找不回来了。

### 4.8 `git reset` —— 把文件从暂存区拿出来

```bash
git reset HEAD 文件名       # add 错了，把它从暂存区撤下来
```

### 4.9 `git show` —— 看某次提交改了啥

```bash
git show 提交哈希
```

### 4.10 `.gitignore` —— 告诉 Git 别管某些文件

创建一个叫 `.gitignore` 的文件，写进去的文件名 Git 会自动忽略（不跟踪、不提交）。详见 [第十节](#十gitignore-与隐私红线)。

---

## 五、连接 GitHub：clone / push / pull

### 5.1 三个动作

| 命令 | 方向 | 什么时候用 |
|---|---|---|
| `git clone 仓库地址` | 云端 → 本地 | 第一次把别人的/自己的仓库下载下来 |
| `git push` | 本地 → 云端 | 提交后同步到 GitHub |
| `git pull` | 云端 → 本地 | 拉取别人/其他设备上的新改动 |

### 5.2 第一次把本地项目推到 GitHub

假设你在 PyCharm 里建了个项目 `sec-log-analyzer`，想放到 GitHub：

**第 1 步：在 GitHub 网页上新建一个空仓库**（点右上角 `+` → New repository），命名 `sec-log-analyzer`，**不要**勾选 README / .gitignore（保持空仓库）。

**第 2 步：本地初始化并提交**

```bash
cd sec-log-analyzer
git init
git add .
git commit -m "first commit: 日志分析工具初版"
```

**第 3 步：关联远程仓库并推送**

```bash
git remote add origin https://github.com/你的用户名/sec-log-analyzer.git
git push -u origin main
```

- `origin` 是远程仓库的默认别名（可以改成别的，但约定俗成叫 origin）。
- `-u` 把本地分支和远程分支关联起来，以后直接 `git push` 就行，不用再带参数。
- `main` 是主分支名（老仓库可能叫 `master`，以你仓库实际分支名为准）。

### 5.3 以后每天的"改完推上去"

一旦关联过远程仓库，日常就是三步：

```bash
git add .
git commit -m "今天完成了什么"
git push
```

### 5.4 从 GitHub 下载仓库到本地

```bash
git clone https://github.com/chicheng2007/waai.git
cd waai
```

这会把整个仓库（包括所有历史）下载到本地一个叫 `waai` 的文件夹。**注意**：clone 下来的是完整仓库，带 `.git`，可以直接接着改和提交。

### 5.5 多设备同步：先 pull 再改

如果你在手机/另一台电脑也改了仓库，回到这台电脑继续前，**先 pull**：

```bash
git pull
# 然后才开始改文件
```

记住口诀：**动手前先 pull，改完立刻 push**。这样不会漏掉别人的改动，也不容易冲突。

### 5.6 关于认证：HTTPS vs SSH

GitHub 现在**不再接受账号密码**推送，必须用以下之一：

| 方式 | 说明 | 适合 |
|---|---|---|
| **Personal Access Token（PAT）** | 在 GitHub 设置里生成一串令牌，当密码用 | 新手、临时用 |
| **SSH 密钥** | 本地生成密钥对，公钥加到 GitHub | 长期、常用，最省心 |

**Token 方式**：推送时用户名填 GitHub 用户名，密码处粘贴 token（不是账号密码）。

> 🔴 **红线**：token 等于你的账号密码，**绝对不能**写进代码、README、截图发到公开仓库！一旦泄露别人能操作你的仓库。如果怀疑泄露，立刻去 GitHub 设置里撤销并重新生成。你之前遇到过的 403 权限错误，就是 token 权限没勾对——classic token 要勾 `repo` 才有推送权限。

**SSH 方式**（推荐长期用，配一次以后免密）：

```bash
ssh-keygen -t ed25519 -C "你的邮箱"
# 一路回车，生成 ~/.ssh/id_ed25519（私钥）和 id_ed25519.pub（公钥）
# 把 id_ed25519.pub 的内容复制到 GitHub 设置 → SSH and GPG keys → New SSH key
# 之后用 SSH 地址 clone：git@github.com:用户名/仓库.git
```

---

## 六、每天怎么用它：两种真实工作流

### 6.1 工作流 A：维护你的学习仓库（waai）

你维护 `waai` 这个学习仓库时，典型的改动是：加一篇笔记、更新打卡、调整目录。流程：

```bash
# 1. 开工前，先同步云端最新状态（尤其你在多个设备改过）
git pull

# 2. 改文件：比如更新 checkin-log.md、加一篇资源
#    （在 PyCharm 里改）

# 3. 看看改了什么，确认无误
git status
git diff

# 4. 暂存 + 提交
git add .
git commit -m "更新打卡：第5天完成正则提取"

# 5. 推送到 GitHub
git push
```

`git log --oneline` 能看到一串绿色方格背后的每一次努力——这就是你的成长轨迹。

### 6.2 工作流 B：做一个新项目（如 14 天实战的日志分析器）

```bash
# 项目开始时
git init

# 每天做完一个功能就提交一次（小步快跑，别攒一周）
git add .
git commit -m "day1: 实现IP出现次数统计"

# 功能做完，建远程仓库推上去（步骤见 5.2）
git remote add origin https://github.com/你的用户名/sec-log-analyzer.git
git push -u origin main

# 以后继续开发：add → commit → push 循环
```

**关键点：提交要小而频繁**。每天一个功能=一次提交，出问题能精确定位到"是哪天改坏的"。攒一周提交一次，出了问题只能整个回退。

### 6.3 一句话记住日常循环

```
改东西 → git add . → git commit -m "说明" → git push
     （开工前先 git pull）
```

---

## 七、分支：大胆试错而不弄坏主线

### 7.1 分支是什么

**分支（branch）就是平行世界**。你在主线（`main`）上开一条新分支去做实验，改崩了删掉分支就行，主线毫发无损；做成了再合并回主线。

```
main:  ●───●──────────────●───●  (稳定主线)
            \            /
feature:      ●───●───●        (实验分支，做完合并回来)
```

### 7.2 什么时候用分支

- 想试一个 risky 的改动（重构代码、换模型），怕弄坏能跑的版本
- 做 CTF 时想试一种攻击思路，不影响已有的解题脚本
- 团队协作时各做各的功能，最后合并

### 7.3 分支命令

```bash
git branch                    # 查看所有分支
git branch 分支名              # 新建分支
git checkout 分支名            # 切换到该分支
git checkout -b 分支名         # 新建并切换（最常用）

# 在分支上改完、提交后，切回主线合并
git checkout main
git merge 分支名               # 把分支的改动合并进 main

git branch -d 分支名           # 合并完删除分支
```

> 新版 Git 推荐用 `git switch 分支名` 代替 `git checkout 分支名`（语义更清晰），但 checkout 依然通用。

### 7.4 新手最小实践

在你自己的项目里，试试"开分支做实验"：

```bash
git checkout -b try-new-feature
# 随便改点东西
git add . && git commit -m "实验：试试新方案"
git checkout main            # 切回主线，你会发现刚才的改动"消失"了——因为它在另一条分支
git branch -d try-new-feature # 实验不要了，删掉
```

亲手做一遍，你就理解分支的隔离性了。

---

## 八、PyCharm 里用 Git（图形界面）

你用 PyCharm，其实**大部分操作可以点鼠标完成**，不用记命令。

### 8.1 初次设置

PyCharm → File → Settings → Version Control → Git，确认 Git 可执行文件路径正确（一般自动识别）。

如果你已经 `git init` 过，PyCharm 打开项目时会自动识别 Git 仓库。

### 8.2 常用图形操作

| 我想做什么 | 怎么点 |
|---|---|
| **看改了哪些文件** | 左侧 **Git** 工具窗口（或 Alt+9），列出所有改动 |
| **提交（add + commit）** | Git 窗口里选中文件 → 右键 **Commit**，填说明 → 点 Commit。PyCharm 的 commit 一步完成 add+commit |
| **推送** | 顶部工具栏 ↑ 箭头，或 Git → Push（Ctrl+Shift+K） |
| **拉取** | 顶部工具栏 ↓ 箭头，或 Git → Pull |
| **看历史** | Git 窗口的 **Log** 标签，能看到每次提交和改动 |
| **撤销未提交改动** | 文件上右键 → Git → Revert |
| **切换/新建分支** | 右下角状态栏的分支名（如 `main`），点它 → New Branch / 切换 |
| **解决冲突** | 冲突文件双击，PyCharm 提供图形化的"接受我的/接受对方的"合并界面 |

### 8.3 命令行 vs 图形界面，怎么选

- **日常 add/commit/push/pull**：图形界面更快，点对点。
- **看状态、处理复杂情况、写脚本自动化**：命令行更灵活。
- **推荐**：两者都懂——图形界面处理日常，命令行处理疑难。这也是本教程命令和图形都讲的原因。

> 一个常见坑：PyCharm 的 Commit 按钮有时是灰的——通常是因为没选中文件，或者没填提交说明。检查这两处。

---

## 九、常见报错与急救

### 9.1 `git push` 报 403 / Permission denied

**原因**：token 权限不够，或没配认证。
**解决**：
- 用 token：确认 classic token 勾了 `repo` 权限（fine-grained token 要对仓库有 Contents 写权限）。
- 用 SSH：确认公钥已加到 GitHub，且用的是 `git@github.com:` 开头的地址。

### 9.2 `git push` 报 `failed to connect` / 超时

**原因**：国内访问 GitHub 网络不稳定。
**解决**：
- 重试几次；
- 配置代理或 git 的 http 代理；
- 换网络环境（手机热点）；
- 实在不行，先 `git commit` 本地存档，网络好了再 push（本地提交不会丢）。

### 9.3 `git pull` 报冲突（Conflict）

**原因**：本地和远程改了同一个文件的同一处，Git 不知道听谁的。
**解决**：
1. 打开冲突文件，会看到 `<<<<<<<`、`=======`、`>>>>>>>` 标记。
2. 手动编辑，保留你想要的内容，删掉标记。
3. `git add 文件名` → `git commit -m "解决冲突"` → `git push`。
4. PyCharm 用户：双击冲突文件，用图形化合并界面点选更省事。

### 9.4 `git add` 提示 "LF will be replaced by CRLF"

**原因**：Windows 和 Linux/macOS 换行符不同，Git 在自动转换。
**解决**：这是**正常提示，不是错误**，可以忽略。想彻底配置：

```bash
git config --global core.autocrlf true    # Windows
```

### 9.5 提交信息写错了，想改

```bash
git commit --amend -m "正确的说明"
```

（仅适用于还没 push 的最近一次提交。）

### 9.6 手滑 commit 了不该提交的文件

```bash
git reset --soft HEAD~1     # 撤销上次 commit，但保留改动在工作区
# 然后把不该提交的文件加进 .gitignore 或删掉，重新 add/commit
```

### 9.7 想彻底回到某个历史版本

```bash
git log --oneline                    # 找到目标版本的哈希
git reset --hard 哈希                # 工作区、暂存区全部回到那个版本（危险！会丢弃之后的改动）
```

> ⚠️ `--hard` 会丢弃之后的改动，用前确认真的不要了。

### 9.8 提交了敏感信息（token / 密码）怎么办

1. **立刻去 GitHub 撤销/轮换那个 token**（第一优先级，先止血）。
2. 从代码里删除，并加入 `.gitignore`。
3. 但历史里仍有残留——需要用 `git filter-repo` 或 BFG 工具清理历史，或删仓库重建。**仅从最新提交删除不够，历史里还能翻出来。**

> 这也是为什么第十节的隐私红线那么重要——**预防远比补救容易**。

---

## 十、.gitignore 与隐私红线

### 10.1 什么是 .gitignore

一个文本文件，列出"Git 不要跟踪的文件/文件夹"。创建在项目根目录：

```gitignore
# 依赖和虚拟环境
venv/
.venv/
__pycache__/
*.pyc

# 环境和密钥（重中之重！）
.env
config.py
*.pem
token.txt

# IDE 和编辑器
.idea/
.vscode/
*.swp

# 数据和输出（按需）
*.log
result.csv
*.png
```

写好 `.gitignore` 后，`git add .` 会自动跳过里面列的文件。

### 10.2 网安学生的隐私红线（必读）

你的仓库是**公开的**，任何人都能看。提交前务必确认没有以下内容：

- 🔴 **个人敏感身份信息**（真实姓名+学校+身份的组合等）
- 🔴 **GitHub token、API key、密码**
- 🔴 **未脱敏的真实日志 / 真实取证数据 / 真实 IP 和用户数据**
- 🔴 **授权凭据、内网地址、真实资产清单**

> 你之前特别在意公开仓库不能出现敏感字样——这个警惕性完全正确，提交前养成 `git diff` 扫一眼的习惯。

### 10.3 全局忽略（可选）

有些文件（如 `.DS_Store`、`.idea`）你希望所有项目都忽略，可以配全局 ignore：

```bash
git config --global core.excludesfile ~/.gitignore_global
# 然后在 ~/.gitignore_global 里写规则
```

---

## 十一、命令速查表

收藏这一张表，日常够用：

| 场景 | 命令 |
|---|---|
| 初始化仓库 | `git init` |
| 下载仓库 | `git clone 地址` |
| 看状态 | `git status` |
| 看改动 | `git diff` |
| 暂存全部 | `git add .` |
| 暂存单个 | `git add 文件` |
| 提交 | `git commit -m "说明"` |
| 撤销未提交改动 | `git restore 文件` |
| 从暂存区撤回 | `git reset HEAD 文件` |
| 看历史 | `git log --oneline` |
| 看某次提交 | `git show 哈希` |
| 推到远程 | `git push` |
| 拉远程更新 | `git pull` |
| 关联远程 | `git remote add origin 地址` |
| 建分支 | `git checkout -b 分支名` |
| 切换分支 | `git checkout 分支名` |
| 合并分支 | `git merge 分支名` |
| 改上次提交说明 | `git commit --amend -m "新说明"` |
| 回到历史版本 | `git reset --hard 哈希` |
| 配置身份 | `git config --global user.name/email` |

---

## 十二、练手：用 Git 管理你的打卡和项目

光学不练等于没学。给你三个循序渐进的练习：

### 练习 1：给现有仓库做一次完整提交（5 分钟）

1. 打开你的 `waai` 仓库文件夹。
2. 在 `checkin-log.md` 末尾加一行今天的记录。
3. 依次执行：
   ```bash
   git status
   git add checkin-log.md
   git commit -m "打卡：今天学了Git"
   git push
   ```
4. 刷新 GitHub 网页，看到新提交就成了。

### 练习 2：建立一个新项目仓库（15 分钟）

把 [14 天实战](../START-HERE.md) 的项目用 Git 管理起来：

1. 在 PyCharm 建项目，写个 `hello.py`。
2. `git init` → `git add .` → `git commit -m "init"`。
3. 在 GitHub 建空仓库，`git remote add origin 地址` → `git push -u origin main`。
4. 再改一次代码，重复 add/commit/push。

### 练习 3：体验分支与回退（15 分钟）

1. 在项目里 `git checkout -b experiment`。
2. 故意把代码改崩，`git add . && git commit -m "故意改崩"`。
3. `git checkout main` —— 代码恢复原样（因为崩的那版在 experiment 分支）。
4. `git log --oneline` 观察两条分支的历史。
5. `git branch -d experiment` 删掉实验分支。

做完这三个练习，你就已经超过大多数"只会点提交按钮"的人了。

---

## 最后几句

- **别怕犯错**：Git 的强大就在于"几乎一切都能回退"。放心试，大不了 `git reset`。
- **别背命令**：理解"工作区→暂存区→仓库→远程"这条主线，命令用多了自然记。忘了就回来查速查表。
- **小而频繁的提交** > 大而稀疏的提交。每次提交讲清楚"改了什么"。
- **提交前扫一眼 `git diff`**，尤其公开仓库——守住隐私红线。

> 从今天起，把你的每一次学习都变成一个 commit。几个月后，`git log` 里那一串记录，就是你努力过的最好证明。

---

*配套：本仓库的学习路线见 [README](../README.md)，14 天实战见 [START-HERE](../START-HERE.md)，每日打卡见 [checkin-log](../checkin-log.md)。*
