# 附录 C：名词解释

| 术语 | 解释 |
| --- | --- |
| **CTF** | Capture The Flag，网络安全竞赛 |
| **PWN** | 通过漏洞利用控制程序执行流程 |
| **EXP / Exploit** | 漏洞利用脚本 |
| **Payload** | 利用时发送的恶意数据 |
| **Shellcode** | 用于获得 shell 的机器码 |
| **Getshell** | 成功获得交互式 shell |
| **ROP** | 面向返回编程，复用程序代码片段 |
| **Gadget** | 以 ret 结尾的短指令序列 |
| **NX / DEP** | 栈/堆不可执行保护 |
| **Canary** | 栈上的随机哨兵，检测栈溢出 |
| **ASLR** | 地址空间布局随机化 |
| **PIE** | 位置无关可执行文件 |
| **RELRO** | GOT 表保护机制 |
| **GOT** | 全局偏移表，存放外部函数地址 |
| **PLT** | 过程链接表，动态链接跳板 |
| **ret2text** | 返回到程序已有代码 |
| **ret2libc** | 返回到 libc 中的函数 |
| **ret2shellcode** | 返回到自定义 shellcode |
| **UAF** | Use After Free，释放后使用 |
| **Double Free** | 重复释放同一块内存 |
| **tcache / fastbin / bin** | glibc 管理空闲 chunk 的容器 |
| **Chunk** | glibc 堆内存块 |
| **Top Chunk** | 堆顶的剩余空间 |
| **ptmalloc** | glibc 的 malloc 实现 |
| **FSOP** | 面向文件结构的编程 |
| **IO_FILE** | C 标准库的 IO 结构体 |
| **vtable** | 虚函数表，C++ 多态的实现 |
| **hook** | libc 中的可劫持函数指针（如 __free_hook） |
| **seccomp** | Linux 系统调用过滤机制 |
| **ORW** | open/read/write，沙箱下的 flag 读取方式 |
| **SROP** | 基于信号帧的 ROP |
| **gadget** | 可利用的指令片段 |
| **cyclic** | pwntools 的偏移量计算模式 |
| **one_gadget** | libc 中一键 getshell 的地址 |
| **Safe Linking** | glibc 2.32+ 的指针编码保护 |
| **KASLR** | 内核地址随机化 |
| **cred** | 内核进程的权限结构体 |
