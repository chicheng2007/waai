# 第四篇 · 堆的奥秘

> 堆是 PWN 的分水岭。很多人在栈利用得心应手后，会在堆这里卡上很久——这是正常的。

**前置要求**：栈篇全部完成，理解指针与链表。

**学完你将**：理解 ptmalloc 的实现，掌握 UAF、Double Free、各类 Bin Attack。

## 章节

17. [堆基础：malloc 与 free 的世界](./ch17-堆基础.md)
18. [chunk 结构与 bin 体系](./ch18-chunk与bins.md)
19. [UAF：释放后的幽灵](./ch19-UAF.md)
20. [Double Free：一物两卖](./ch20-Double-Free.md)
21. [Fastbin Attack](./ch21-Fastbin-Attack.md)
22. [Tcache Attack](./ch22-Tcache-Attack.md)
23. [Unsorted Bin Attack](./ch23-Unsorted-Bin-Attack.md)
24. [off-by-one 与 House of 系列](./ch24-off-by-one与houseof.md)
25. [堆风水实战](./ch25-堆风水实战.md)

> 学习建议：画图！把 chunk 结构、bin 链表画出来，理解会深刻得多。同时注意 glibc 版本差异。
