# 第 5 关 · bins 与反作弊检查机制演化

## 🎬 游戏开场

这一关是后台篇的收官。我们把两件事讲清楚:

1. **bins 的链表维护**:unsorted/small/large bin 到底怎么串,为什么能被 unsorted bin attack、largebin attack 利用。
2. **反作弊检查年表**:glibc 这些年加了哪些检查,堵了哪些老招,逼出了哪些新招。

理解这张"军备竞赛时间表",你就明白整个 PWN 堆利用的发展脉络——**攻击和防御是如何交替升级的**。

---

## 🧠 核心概念（游戏版）

### 1. bins 的链表结构

回顾基础篇:small/large/unsorted bin 都是**双向循环链表**,chunk 的 fd/bk 指针把柜子串起来。

```
   main_arena(bin头) 
   ┌──────┐
   │ fd   │──→ chunk A ──→ chunk B ──→ 回到bin头
   │ bk   │←──          ←──          ←──
   └──────┘
```

**关键**:fd/bk 指针存在 chunk 的**用户数据区**。如果通过 UAF 能写这些指针,就能操纵链表。

### 2. unsorted bin attack(经典)

unsorted bin attack 利用 malloc 整理 unsorted bin 时的 unlink 操作:

```c
// 取出victim时
bck = victim->bk;
unsorted_chunks(av)->bk = bck;
bck->fd = unsorted_chunks(av);   // ← 关键写!
```

如果伪造 victim->bk = `target - 0x10`,那么 `bck->fd = bin头` 就会把 bin 头地址写到 `target`。

游戏翻译:你伪造"上一个柜子"的门牌,系统整理时会往你指定的地址写"中转站的地址"——**任意地址写一个大数**。经典用途:改写 `global_max_fast`,让 fastbin 范围变大,开启后续攻击。

### 3. largebin attack(现代主力)

glibc 2.30 后,unsorted bin attack 被加检查堵住(largebin 里插入时有检查),但 attacker 转向 **largebin attack**:

利用 large bin 按大小排序插入时的链表操作,同样实现"往任意地址写一个堆地址"。这是 House of Apple 等现代套路的前置步骤。

游戏翻译:一条路堵了, attackers 找到另一条"分类架插入"的路,照样能往指定地址写值。

### 4. 反作弊检查演化年表(核心!)

| 版本 | 新增检查 | 堵住的招 | 逼出的新招 |
| --- | --- | --- | --- |
| 老版本 | 无 | — | 各种基础 attack |
| 2.26 | tcache 引入 | — | tcache poisoning(更快) |
| 2.28 | tcache 个数检查完善 | — | — |
| 2.29 | tcache key | 直接 double free | UAF 清 key |
| 2.30 | largebin 插入检查 | unsorted bin attack | largebin attack |
| 2.32 | safe-linking | 直接写 fd/next | 泄露堆址+编码 |
| 2.34 | 移除 malloc/free hook | hook 劫持 | IO_FILE / House of Apple |
| 2.35+ | vtable 检查加强 | 伪造 vtable | 用合法 vtable 偏移 |

游戏翻译:这是游戏公司的反作弊更新日志——每次更新堵一批外挂,外挂作者马上研究出新版本。这场军备竞赛至今还在继续。

### 5. 防御方的"检查"都是什么?

glibc 检查的本质,无外乎:

- **地址对齐检查**:chunk 地址必须 16 字节对齐。
- **size 检查**:取出的 chunk size 必须匹配 bin。
- **链表完整性检查**:fd/bk 是否互相指回(双向链表校验)。
- **盖章/编码**:key、safe-linking。

这些检查点,就是我们读源码时要盯的地方——**破解检查 = 构造能通过检查的假数据**。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 双向链表 | fd/bk 循环链表 |
| 整理时写值 | unsorted bin attack |
| 分类架插入写值 | largebin attack |
| 反作弊更新日志 | glibc 安全检查演化 |
| 军备竞赛 | 攻防对抗史 |

---

## 🎯 本关任务:画出你的年表

把上面那张"检查演化年表"抄到一个笔记里,然后针对你正在练习的 glibc 版本,标出:

1. 这个版本有哪些检查?
2. 哪些老招不能用?
3. 当前主流用什么招?

比如 2.35:有 key、有 safe-linking、无 hook → 主流是 House of Apple(FSOP)。

---

## 📌 本关小结 —— 后台篇毕业！

| 你学会了 | 一句话记忆 |
| --- | --- |
| bins链表 | fd/bk双向链,存在用户区 |
| unsorted attack | 伪造bk → 任意地址写bin头 |
| largebin attack | 现代任意写主力 |
| 检查年表 | 攻防军备竞赛,版本决定招式 |

**后台篇回顾(1-5关)**:你现在能从源码角度解释 malloc/free/tcache/bins 的每一行关键逻辑,也理解了为什么招式随版本变化。这是从"会打"到"懂原理"的蜕变。

---

## 🎬 下一关预告

**第二大关 · 现代连招开启!**

第 6 关 · **House of Apple:存档系统的终极连招**

hook 被移除后,glibc 2.35 时代怎么拿 shell?答案就是 House of Apple——利用 IO_FILE 结构的现代神技。下一关,我们用游戏比喻把这套复杂连招讲得明明白白。准备迎接现代堆利用的核心!
