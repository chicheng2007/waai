# 第 8 关 · largebin attack：大柜子的秘密

## 🎬 游戏开场

unsorted bin attack(往任意地址写 bin 头地址)在 glibc 2.30 被堵了——large bin 插入时加了检查。但攻击者很快发现:**检查加在了 unsorted bin 那,却没完全保护 large bin 自己的插入排序过程**。

于是 **largebin attack** 诞生:利用大柜分类架(large bin)按大小排序插入时的链表操作,照样往任意地址写入一个堆地址。

它是现代堆利用最重要的"任意写原语"之一,也是 House of Apple 的标准前置。

---

## 🧠 核心概念（游戏版）

### 1. large bin 的特点

large bin(≥0x400 的柜子)不是简单链表,而是**按大小排序**的:大柜在前,小柜在后。每个 chunk 除了 fd/bk,还有两个额外指针:

```
large chunk 的字段:
  fd, bk        ← 双向链表指针
  fd_nextsize   ← 指向"下一个不同大小"的chunk
  bk_nextsize   ← 指向"上一个不同大小"的chunk
```

游戏翻译:大柜分类架不只记"前后柜子",还记"比它大一级/小一级的柜子是谁"——所以大柜子有 4 个指针。

### 2. 攻击点:插入排序时的写操作

当系统把一个大 chunk 插入 large bin(从 unsorted bin 整理过来时),会执行类似:

```c
// 简化
victim->fd_nextsize = fwd;          
victim->bk_nextsize = fwd->bk_nextsize;
fwd->bk_nextsize->fd_nextsize = victim;   // ← 写1
fwd->bk_nextsize = victim;                // ← 写2
```

游戏翻译:插入大柜时要通知"大小邻居"更新纸条,其中 `fwd->bk_nextsize->fd_nextsize = victim` 这一步会往 `bk_nextsize` 指向的地址写入 victim(堆地址)。

**利用**:如果我们能控制 `fwd->bk_nextsize`(通过伪造 chunk 的指针),让它指向 `target - 0x20`,那么这一步写操作就会把堆地址写到 `target`——**任意地址写一个堆地址**。

### 3. 攻击前提

- 能制造 large chunk 并让它被整理进 large bin。
- 能通过 UAF 或溢出篡改 large chunk 的 `bk_nextsize`/`fd_nextsize` 指针。
- 通常配合堆风水(第 22 关)布置两个大小不同的 large chunk。

### 4. 写进去的值有什么用?

写进去的是一个**堆地址**。经典用途:

- 改写 `_IO_list_all` 的一部分 → 指向 fake FILE(House of Apple 前置)。
- 改写 global_max_fast → 扩大 fastbin 范围。
- 伪造各种结构指针。

游戏翻译:largebin attack 给你"往指定地址写一个堆坐标"的能力——有了这个,你就能把"存档链表"指向你堆上的假存档卡。

### 5. 为什么没被堵?

glibc 2.30 加的检查主要在 `unsorted_chunks` 的 bk 校验,但 large bin 插入排序的这段写操作一直存在可用性(因为正常功能需要它)。攻击者不断找到新的利用角度——这就是军备竞赛的现实:完全堵死很难,因为要保留正常功能。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 大柜分类架 | large bin |
| 大小邻居指针 | fd_nextsize / bk_nextsize |
| 插入排序写值 | largebin attack |
| 写进去的堆地址 | 任意写原语 |

---

## 🎯 本关任务:理解写原语

用一句话总结:largebin attack 提供了什么能力?

> 答:往任意地址写入一个堆 chunk 的地址(arbitrary write of heap pointer)。

再想:这个能力配合 House of Apple,怎么串起来?

> largebin attack 改 `_IO_list_all` → 指向堆上 fake FILE → exit 触发 → House of Apple 拿 shell。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| large bin | 按大小排序,多两个nextsize指针 |
| largebin attack | 利用插入排序写堆地址到任意地址 |
| 地位 | 现代任意写主力,House of Apple前置 |
| 原因 | 检查没完全堵住排序写操作 |

---

## 🎬 下一关预告

**第 9 关 · 堆布局自动化：让脚本帮你摆柜子**

House of Apple 这种连招,堆布局极其复杂——手动算每个 chunk 的位置会让人崩溃。下一关我们学怎么让脚本(pwntools + 布局模板)帮你自动摆好堆,把繁琐的布局变成可复用的代码。
