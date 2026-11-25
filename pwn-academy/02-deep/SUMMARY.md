# 目录

> 进阶版教程，面向已掌握基础 PWN 技能的读者。共 20 章 + 附录。

## 第一篇 · glibc 堆源码剖析

[篇目简介](./01-glibc-internals/README.md)

1. [从 malloc 到 _int_malloc：一次分配的完整旅程](./01-glibc-internals/ch01-malloc源码.md)
   - __libc_malloc 的入口逻辑
   - tcache 的尝试与 arena 的获取
   - _int_malloc 的全流程（fastbin/smallbin/unsorted/largebin/top）
   - request2size 与空间计算的细节
2. [free 的真相：_int_free 与 chunk 回收路径](./01-glibc-internals/ch02-free源码.md)
   - __libc_free 与 tcache 的优先处理
   - 各种 bin 的插入逻辑
   - 向前/向后合并（consolidate）的源码
3. [tcache 源码全解：从 key 到 safe-linking](./01-glibc-internals/ch03-tcache源码.md)
   - tcache 结构的演进（2.26 → 2.29 → 2.32）
   - key 检查的实现与绕过
   - safe-linking 的异或编码原理与解码
4. [bins 的维护：解链与入链的源码细节](./01-glibc-internals/ch04-bins源码.md)
   - unlink 宏的条件检查
   - unsorted bin 的遍历与归类
   - largebin 的排序插入
5. [堆检查机制与绕过思路总览](./01-glibc-internals/ch05-检查与绕过.md)
   - glibc 各版本新增的检查一览
   - 检查与绕过的「猫鼠游戏」规律

## 第二篇 · 现代堆利用

[篇目简介](./02-modern-heap/README.md)

6. [House of Apple 完整实战](./02-modern-heap/ch06-houseofapple.md)
   - glibc 2.35 下的 IO_FILE 利用
   - _IO_wfile_overflow 的二次跳转
   - 从 tcache poisoning 到 getshell
7. [FSOP：从原理到 getshell](./02-modern-heap/ch07-FSOP实战.md)
   - _IO_flush_all_lockp 的调用链
   - 伪造 FILE 链表的完整构造
8. [largebin attack 深入](./02-modern-heap/ch08-largebin深入.md)
   - fd_nextsize/bk_nextsize 的利用
   - 修改 _IO_list_all 的实战
9. [堆布局自动化技巧](./02-modern-heap/ch09-堆布局自动化.md)
   - 用脚本规划 malloc/free 序列
   - 常见的布局模式速查
10. [真实比赛堆题复盘](./02-modern-heap/ch10-堆题复盘.md)
    - 一道 2.35 题目的完整分析
    - 多技术组合的解题思路

## 第三篇 · IO_FILE 深度剖析

[篇目简介](./03-iofile-deep/README.md)

11. [FILE 结构体源码全解析](./03-iofile-deep/ch11-FILE源码.md)
    - struct _IO_FILE 每个字段的含义
    - _IO_FILE_plus 与 vtable
12. [vtable 检查的演化与绕过](./03-iofile-deep/ch12-vtable演化.md)
    - 2.24 之前的任意 vtable
    - 2.24~2.27 的检查与绕过
    - 2.28+ 的 IO_validate_vtable
    - House of Apple 为什么能绕
13. [stdout 泄露的多种姿势](./03-iofile-deep/ch13-stdout泄露.md)
    - 修改 _IO_write_base/_IO_write_ptr
    - 不同场景下的 flags 构造

## 第四篇 · 自动化与工具

[篇目简介](./04-automation/README.md)

14. [angr 符号执行入门](./04-automation/ch14-angr入门.md)
    - 符号执行的基本原理
    - 用 angr 求解输入约束
15. [AFL 模糊测试实战](./04-automation/ch15-AFL实战.md)
    - AFL 的工作原理
    - 用 AFL 挖出一个栈溢出
16. [利用脚本工程化](./04-automation/ch16-脚本工程化.md)
    - 模块化 exp 设计
    - 多环境适配与远程调试

## 第五篇 · 内核与跨平台

[篇目简介](./05-kernel-cross/README.md)

17. [内核 PWN 深入](./05-kernel-cross/ch17-内核深入.md)
    - kernel 堆与 slab/slub
    - userfaultfd 与堆喷
18. [kernel ROP 与提权实战](./05-kernel-cross/ch18-kernel提权.md)
    - swapgs/iretq 返回用户态
    - 绕过 SMEP/SMAP/KASLR
19. [Windows PWN 入门](./05-kernel-cross/ch19-WindowsPWN.md)
    - PE 格式与 Windows 堆
    - Windows 下的漏洞利用特点
20. [ARM/AArch64 PWN 简介](./05-kernel-cross/ch20-ARMPWN.md)
    - ARM 架构与指令特点
    - 移动端 PWN 的注意事项

## 附录

- [各版本 glibc 源码索引](./appendix/source-index.md)
- [绕过手法速查表](./appendix/bypass-table.md)
- [高级调试技巧](./appendix/debug-tips.md)
- [进阶环境配置](./appendix/environment.md)
