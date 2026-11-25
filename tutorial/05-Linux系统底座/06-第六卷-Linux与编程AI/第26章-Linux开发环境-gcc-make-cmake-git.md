# 第 26 章 Linux 开发环境：gcc / make / cmake / git

## 本章目标

读完这一章，你将能够：

- 理解编译型语言的构建流程（预处理→编译→汇编→链接）
- 掌握 gcc/g++ 的使用
- 掌握 make 与 Makefile 的编写
- 理解并使用 cmake 管理跨平台构建
- 掌握 git 版本控制的基本工作流
- 理解这些工具与 AI/安全的关系

---

## 26.1 编译过程回顾

在系统语言卷我们讲过编译过程，这里结合 Linux 实操再梳理一遍：

```bash
源代码(.c) → 预处理 → 编译 → 汇编 → 链接 → 可执行文件
```

| 阶段 | 工具 | 产物 | 做什么 |
|------|------|------|--------|
| 预处理 | cpp | `.i` | 展开 `#include`、`#define` |
| 编译 | gcc -S | `.s` | 转成汇编代码 |
| 汇编 | as | `.o` | 转成机器码目标文件 |
| 链接 | ld | 可执行文件 | 合并目标文件和库 |

一步到位编译：

```bash
gcc hello.c -o hello
./hello
```

分步编译（理解过程）：

```bash
gcc -E hello.c -o hello.i      # 预处理
gcc -S hello.i -o hello.s      # 编译成汇编
gcc -c hello.s -o hello.o      # 汇编成目标文件
gcc hello.o -o hello           # 链接
```

> **小白问**：gcc 和 g++ 区别？
>
> gcc 是 C 编译器，g++ 是 C++ 编译器（自动链接 C++ 标准库）。编译 C++ 程序用 g++。

---

## 26.2 gcc 详解

### 26.2.1 常用选项

```bash
gcc -o hello hello.c           # 指定输出文件名
gcc -Wall hello.c -o hello     # 开启所有警告（强烈建议）
gcc -g hello.c -o hello        # 加入调试信息（gdb 需要）
gcc -O2 hello.c -o hello       # 优化级别 2（发布用）
gcc -c hello.c                 # 只编译不链接，生成 hello.o
gcc -I/path/to/include ...     # 指定头文件搜索路径
gcc -L/path/to/lib -lfoo ...   # 指定库路径和链接库
```

### 26.2.2 静态库与动态库

```bash
# 创建静态库
ar rcs libmylib.a a.o b.o
gcc main.c -L. -lmylib -o app

# 创建动态库（共享库）
gcc -shared -fPIC -o libmylib.so a.o b.o
gcc main.c -L. -lmylib -o app
# 运行时需要 LD_LIBRARY_PATH 包含库路径
```

> **安全关联**：动态库劫持是常见的提权/持久化手法（如通过 `LD_PRELOAD` 注入恶意库）。理解动态链接机制，才能理解这类攻击。第 27 章会再提到。

### 26.2.3 调试：gdb

```bash
gcc -g hello.c -o hello
gdb ./hello
```

gdb 常用命令：`break main`（断点）、`run`（运行）、`next`（单步）、`print var`（查看变量）、`backtrace`（调用栈）、`quit`（退出）。

gdb 也是二进制安全分析、漏洞利用的基础工具（系统语言卷讲过）。

---

## 26.3 make 与 Makefile

### 26.3.1 为什么需要 make

项目有很多源文件和依赖关系，手动一个个编译很繁琐。make 根据 Makefile 自动判断哪些文件需要重新编译，实现增量构建。

### 26.3.2 Makefile 基础

```makefile
# 变量
CC = gcc
CFLAGS = -Wall -g -O2

# 目标: 依赖
# 命令（必须用 Tab 缩进）
hello: main.o utils.o
	$(CC) $(CFLAGS) main.o utils.o -o hello

main.o: main.c utils.h
	$(CC) $(CFLAGS) -c main.c

utils.o: utils.c utils.h
	$(CC) $(CFLAGS) -c utils.c

clean:
	rm -f *.o hello
```

运行：

```bash
make           # 构建默认目标（第一个目标）
make clean     # 清理
make -j4       # 4 个任务并行编译（加快速度）
```

核心概念：

- **目标（target）**：要生成的东西
- **依赖（prerequisites）**：生成目标需要的文件
- **命令（recipe）**：如何生成（必须以 Tab 开头）

make 的逻辑：如果依赖比目标新，就重新执行命令。这就是增量构建。

> **小白问**：Makefile 里命令必须用 Tab，不能用空格——这是新手最常踩的坑。如果报错 "missing separator"，检查缩进是不是 Tab。

---

## 26.4 cmake：跨平台构建

### 26.4.1 为什么需要 cmake

make 依赖具体平台，cmake 生成平台无关的构建配置，能跨平台（Linux/Mac/Windows）生成 Makefile 或 Visual Studio 项目。大型项目（如很多 AI 框架）都用 cmake。

### 26.4.2 CMakeLists.txt 示例

```cmake
cmake_minimum_required(VERSION 3.10)
project(MyApp)

# 指定 C++ 标准
set(CMAKE_CXX_STANDARD 17)

# 添加可执行文件
add_executable(myapp main.cpp utils.cpp)

# 链接库
target_link_libraries(myapp pthread)

# 查找依赖包
find_package(OpenSSL REQUIRED)
target_link_libraries(myapp OpenSSL::SSL)
```

### 26.4.3 构建流程

```bash
mkdir build && cd build    # 推荐 out-of-source 构建，保持源码干净
cmake ..                   # 生成 Makefile
make -j$(nproc)            # 编译
sudo make install          # 安装（可选）
```

`cmake ..` 的 `..` 指向上级源码目录（CMakeLists.txt 所在处）。

---

## 26.5 git 版本控制

### 26.5.1 为什么用 git

git 是分布式版本控制系统，用于：

- 记录代码历史、随时回退
- 多人协作
- 分支开发（实验新功能不影响主线）
- 上传 GitHub/GitLab

### 26.5.2 基本工作流

```bash
# 初始化/克隆
git init                          # 在当前目录新建仓库
git clone https://github.com/user/repo.git   # 克隆现有仓库

# 查看状态
git status

# 暂存与提交
git add file.txt                  # 暂存单个文件
git add .                         # 暂存所有改动
git commit -m "说明信息"          # 提交

# 查看历史
git log
git log --oneline --graph         # 简洁图形化

# 远程操作
git remote add origin URL         # 添加远程仓库
git push -u origin main           # 推送
git pull                          # 拉取
```

### 26.5.3 分支管理

```bash
git branch                        # 查看分支
git branch feature-x              # 创建分支
git checkout feature-x            # 切换分支
git checkout -b feature-y         # 创建并切换
git merge feature-x               # 合并分支到当前
git branch -d feature-x           # 删除分支
```

### 26.5.4 回退与撤销

```bash
git diff                          # 查看未暂存的改动
git checkout -- file.txt          # 撤销文件改动（未暂存）
git reset HEAD file.txt           # 取消暂存
git reset --hard HEAD~1           # 回退到上一个提交（危险，丢弃后续改动）
git log --oneline                 # 找提交 ID
git checkout 提交ID -- file.txt   # 恢复某文件的历史版本
```

### 26.5.5 .gitignore 与安全

`.gitignore` 指定不纳入版本控制的文件：

```bash
# .gitignore 示例
*.o
*.so
build/
env/
__pycache__/
.env                  # 环境变量文件（常含密钥）
*.pem                 # 私钥
config Secret*        # 敏感配置
```

> ⚠️ **安全警告**：**永远不要把密钥、密码、token 提交到 git**！一旦提交，即使后续删除，历史记录里依然存在。用 `.gitignore` 排除敏感文件，用环境变量或 secrets 管理。GitHub 有自动扫描，发现泄露的密钥会通知你——但那时可能已经被盗用了。
>
> 如果误提交了密钥，立即**轮换（更换）密钥**，而不只是删除文件。

---

## 26.6 与 AI / 安全的关联

- **AI 框架**：PyTorch、TensorFlow 的核心用 C++/CUDA 编写，通过 cmake 构建；编译安装 Python 包时用这些工具。
- **AI 算子**：高性能算子用 C++/CUDA 写，编译成扩展供 Python 调用（呼应混合编程卷）。
- **安全工具**：Nmap、Metasploit、Suricata 等大量安全工具是 C/C++ 编写的，需要编译安装。
- **漏洞研究**：gdb、objdump、readelf 分析二进制，理解编译产物是漏洞挖掘的基础。

---

## 26.7 本章总结

| 知识点 | 内容 |
|--------|------|
| 编译过程 | 预处理→编译→汇编→链接；gcc -E/-S/-c/-o |
| gcc | -Wall 警告、-g 调试、-O2 优化、-I/-L/-l 库 |
| 库 | 静态库 .a（ar）、动态库 .so（-shared -fPIC） |
| gdb | 断点、单步、查看变量、调用栈 |
| make | Makefile：目标:依赖 + Tab 命令；增量构建；make -j |
| cmake | CMakeLists.txt；跨平台；out-of-source 构建 |
| git | init/clone/add/commit/push/pull；分支、回退 |
| 安全 | .gitignore 排除密钥；误提交要轮换密钥；动态库劫持 |

---

## 本章练习

1. 写一个 hello.c，用 gcc 编译运行，再用 `-Wall -g` 重新编译。
2. 用分步编译（-E、-S、-c）观察各阶段的产物。
3. 写一个简单的 Makefile，实现增量构建，用 `make clean` 清理。
4. 安装 cmake，写一个 CMakeLists.txt 构建一个小项目。
5. 用 git init 创建仓库，做一次 add + commit，查看 git log。
6. 创建一个分支，修改文件后在分支提交，再切回主分支。
7. 写一个 .gitignore，把密钥文件（.env、*.pem）排除掉。
8. 思考：为什么误把密钥提交到 git 后，仅仅删除文件是不够的？为什么要"轮换密钥"？

---

**下一章预告**：我们将学习 Linux 下的 Python / C/C++ / Rust / Go——把前四套教程的语言知识落到 Linux 这个主场上，理解各语言的开发环境与 Linux 特性的结合。
