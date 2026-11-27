# 目录

> 全教程规划约 30 万字，共 35 章 + 4 篇附录，分六篇。以下章节链接均已可点击阅读。

## 第一篇 · 筑基篇：新手村

[篇目简介](./01-foundation/README.md)

1. [写在前面的话：为什么学 PWN](./01-foundation/ch01-为什么学pwn.md)
   - 什么是 CTF，什么是 PWN
   - PWN 在 CTF 中的地位
   - 常见误解答疑（数学不好能学吗？英语差能学吗？）
   - 本教程的使用说明
2. [搭建你的第一次犯罪现场：环境配置](./01-foundation/ch02-环境搭建.md)
   - 虚拟机与 Linux 发行版选择
   - 安装 gcc / gdb / python3 / pwntools
   - pwndbg / gef 调试插件
   - checksec / ROPgadget / one_gadget
   - 编译第一个 32 位与 64 位程序
   - 关闭 ASLR 的正确姿势
3. [C 语言与内存模型](./01-foundation/ch03-C语言与内存.md)
   - 从 Hello World 到指针
   - 指针的本质：地址与类型
   - 数组、字符串与内存布局
   - 结构体与内存对齐
   - 函数调用与参数传递
   - 缓冲区溢出的 C 语言视角
   - 大端与小端
4. [汇编基础：与机器对话](./01-foundation/ch04-汇编基础.md)
   - x86-64 寄存器全景
   - 常见指令速查（mov / push / pop / call / ret / lea ...）
   - 栈的操作与栈顶指针
   - 函数调用约定（cdecl / System V AMD64）
   - 用 objdump 反汇编自己的 C 代码
   - 手写一小段 shellcode
5. [ELF 文件与程序加载](./01-foundation/ch05-ELF与程序加载.md)
   - ELF 头、程序头、节头
   - 段与节：TEXT / DATA / BSS / GOT / PLT
   - 静态链接与动态链接
   - PLT 与 GOT 的协作
   - 程序从 execve 到 main 的旅程
   - 动态链接器 ld.so
6. [栈与函数调用的真相](./01-foundation/ch06-栈与函数调用.md)
   - 栈的生长方向与栈帧
   - call / ret 指令做了什么
   - 栈帧的建立与销毁（prologue / epilogue）
   - 局部变量与返回地址的位置关系
   - 用 gdb 观察一次完整的函数调用
7. [二进制保护机制全家福](./01-foundation/ch07-保护机制.md)
   - checksec 怎么看
   - NX / DEP：栈不可执行
   - Canary：栈上的哨兵
   - PIE / ASLR：地址随机化
   - RELRO / FORTIFY：GOT 与格式化字符串防护
   - 每种保护对利用思路的影响

## 第二篇 · 栈上功夫

[篇目简介](./02-stack/README.md)

8. [栈溢出：第一个漏洞](./02-stack/ch08-栈溢出原理.md)
   - 一个没有任何保护的 gets 程序
   - 覆盖返回地址的原理
   - 计算偏移量的三种方法
   - 用 pwntools 发送第一个 payload
   - 控制 EIP/RIP 的意义
9. [ret2text 与 ret2shellcode](./02-stack/ch09-ret2text与shellcode.md)
   - 程序里有后门函数怎么办
   - 直接返回到 system("/bin/sh")
   - 在栈上写 shellcode 并执行
   - NX 开启时的应对
10. [ret2libc：借别人的代码用](./02-stack/ch10-ret2libc.md)
    - 动态链接库里的宝藏
    - 泄露 libc 基地址
    - 计算 system 与 /bin/sh 的真实地址
    - one_gadget 一键 getshell
    - ret2csu 与通用 gadget
11. [ROP：搭建自己的指令大厦](./02-stack/ch11-ROP进阶.md)
    - ROP 的思想：以彼之矛攻彼之盾
    - 寻找 gadget（ROPgadget / ropper）
    - 构造调用约定（64 位参数传递）
    - 栈对齐问题（movaps 崩溃的真相）
    - ret2syscall 与 SROP
12. [Canary 绕过：与哨兵周旋](./02-stack/ch12-Canary绕过.md)
    - Canary 的工作原理
    - 泄露 Canary 的经典手法
    - 格式化字符串泄露 Canary
    - 逐字节爆破 Canary
    - 伪造 Canary 与异常处理
13. [栈迁移：当栈不够用时](./02-stack/ch13-栈迁移.md)
    - leave / ret 的妙用
    - 把栈迁移到 BSS 段
    - 栈迁移 + ROP 的组合拳
    - 实战例题

## 第三篇 · 格式化字符串的魔法

[篇目简介](./03-format-string/README.md)

14. [格式化字符串漏洞原理](./03-format-string/ch14-格式化字符串原理.md)
    - printf 家族的可变参数机制
    - 为什么 %n 是危险的
    - 栈上的参数是怎么被读取的
15. [泄露与任意地址写](./03-format-string/ch15-泄露与任意写.md)
    - 用 %p / %s 泄露栈内容与内存
    - 用 %n 实现任意地址写
    - 偏移计算与 pwntools 的 fmtstr_payload
    - 64 位下的地址截断问题
16. [格式化字符串实战](./03-format-string/ch16-格式化字符串实战.md)
    - 改写 GOT 表
    - 泄露 Canary 与 libc
    - 综合例题复盘

## 第四篇 · 堆的奥秘

[篇目简介](./04-heap/README.md)

17. [堆基础：malloc 与 free 的世界](./04-heap/ch17-堆基础.md)
    - 什么是堆，为什么需要堆
    - brk 与 mmap
    - main_arena 与 arena
18. [chunk 结构与 bin 体系](./04-heap/ch18-chunk与bins.md)
    - malloc_chunk 结构体全解
    - used / free chunk 的差异
    - tcache / fastbin / smallbin / largebin / unsorted bin
    - bins 的链表结构（FD / BK / fd_nextsize）
19. [UAF：释放后的幽灵](./04-heap/ch19-UAF.md)
    - Use After Free 的成因
    - 堆块的重分配与类型混淆
    - 实战：从 UAF 到 getshell
20. [Double Free：一物两卖](./04-heap/ch20-Double-Free.md)
    - 重复释放的原理
    - tcache double free（2.31 前后差异）
    - fastbin double free
21. [Fastbin Attack](./04-heap/ch21-Fastbin-Attack.md)
    - fastbin 的单向链表特性
    - fd 指针劫持
    - House of Spirit
    - 分配到 GOT 附近
22. [Tcache Attack](./04-heap/ch22-Tcache-Attack.md)
    - tcache 的结构与检查（2.31 的 key 字段）
    - tcache poisoning
    - tcache dup
    - tcache stashing unlink attack
23. [Unsorted Bin Attack](./04-heap/ch23-Unsorted-Bin-Attack.md)
    - unsorted bin 的 FIFO 特性
    - Largebin Attack
    - 修改 global_max_fast
24. [off-by-one 与 House of 系列](./04-heap/ch24-off-by-one与houseof.md)
    - off-by-one 漏洞（null byte poisoning）
    - shrink free chunk
    - House of Einherjar / Force / Lore / Apple
25. [堆风水实战](./04-heap/ch25-堆风水实战.md)
    - 堆布局的规划思路
    - 综合例题复盘
    - libc 2.35 新机制初探

## 第五篇 · 进阶之路

[篇目简介](./05-advanced/README.md)

26. [IO_FILE 利用：Stream 的黑暗面](./05-advanced/ch26-IO_FILE利用.md)
    - FILE 结构体与 vtable
    - _IO_2_1_stdout_ 的利用
    - FSOP 与 _IO_list_all
    - House of Apple
27. [House of 系列进阶](./05-advanced/ch27-House系列进阶.md)
    - House of Orange
    - House of Rabbit
    - glibc 2.35 下的新思路
28. [沙箱与 seccomp 绕过](./05-advanced/ch28-沙箱绕过.md)
    - seccomp 是什么
    - 如何检测沙箱（prctl / seccomp-tools）
    - ORW（open/read/write）代替 system
29. [ORW 与 shellcode 进阶](./05-advanced/ch29-ORW与shellcode.md)
    - 手写 ORW shellcode
    - mprotect 改变内存权限
    - 用 ROP 实现 ORW
30. [内核 PWN 入门](./05-advanced/ch30-内核pwn入门.md)
    - 内核态与用户态
    - syscall 与内核数据结构
    - 一个简单的内核漏洞题

## 第六篇 · 工具与实战

[篇目简介](./06-tools-practice/README.md)

31. [pwntools 精通](./06-tools-practice/ch31-pwntools.md)
    - 常用模块速查
    - ELF / Process / Remote / GDB 调试
    - fmtstr / ROP / shellcraft
    - 写一份优雅的 exp
32. [gdb 与 pwndbg 调试技巧](./06-tools-practice/ch32-gdb调试.md)
    - 断点、单步、观察点
    - 查看栈与寄存器
    - 调试 PIE 与剥离符号的程序
    - 堆调试专用命令
33. [二进制审计方法论](./06-tools-practice/ch33-二进制审计.md)
    - 从 which functions 入手（危险函数清单）
    - 逆向思路与伪代码还原
    - 常见漏洞模式速查
34. [真题实战（一）：栈与格式化字符串](./06-tools-practice/ch34-真题实战一.md)
35. [真题实战（二）：堆](./06-tools-practice/ch35-真题实战二.md)

## 附录

- [常用命令速查](./appendix/cheatsheet.md)
- [漏洞利用模板集](./appendix/templates.md)
- [名词解释](./appendix/glossary.md)
- [推荐资源（书籍、靶场、博客、题目平台）](./appendix/resources.md)

## 写作规范

- 贡献指南：[CONTRIBUTING.md](./CONTRIBUTING.md)
- 开源协议：[LICENSE](./LICENSE)
