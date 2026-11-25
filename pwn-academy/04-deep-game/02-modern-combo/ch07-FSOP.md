# 第 7 关 · FSOP：改写游戏的"退出动画清单"

## 🎬 游戏开场

你注意到没有:游戏结束时会播放一段"退出动画"——保存进度、关闭存档、清场。程序也一样,`exit()` 时会依次"刷新"所有打开的文件流(把缓冲区的数据写出去)。

这个"刷新清单"就是 `_IO_list_all`——一张把所有 FILE 结构串起来的链表。程序 `exit` 时会遍历它,对每个 FILE 执行刷新操作,而刷新要通过 vtable 调用写函数。

**FSOP**(File Structure Oriented Programming,面向 FILE 结构的编程)的思想:

> 篡改这张"退出动画清单",让程序在退出时,按我们伪造的方式执行操作——最终劫持控制流。

它是 House of Apple 等一系列技术的理论母体。

---

## 🧠 核心概念（游戏版）

### 1. exit 时发生了什么?

```c
exit()
  → _IO_cleanup()
    → _IO_flush_all_lockp()      // 刷新所有流
      → 遍历 _IO_list_all 链表
        → 对每个 FILE 调用 vtable 里的 _IO_file_overflow / _IO_file_xsputn
```

游戏翻译:游戏退出 → 保存所有存档 → 挨个刷卡 → 每张卡按"技能清单"上的"写"按钮。

**关键**:如果链表里有一张"假存档卡"(我们伪造的 FILE),程序也会老老实实刷它,按我们给的"技能清单"按钮。

### 2. FSOP 的三要素

```
① 控制 _IO_list_all 或某个 FILE 结构
   (通过 largebin attack 等任意写手段)
② 伪造 FILE 结构的关键字段
   - flags, write_ptr, write_end 等(要满足刷新的条件判断)
   - vtable 指针
③ 让程序走到 exit / 触发刷新的路径
```

**条件判断**:`_IO_flush_all_lockp` 刷新一个 FILE 前,会检查一堆条件(如 `write_ptr > write_base` 表示有数据要写)。伪造 FILE 时要满足这些条件,否则程序不会"刷卡"。这就像假存档卡要做得够逼真,管理员才会去刷它。

### 3. 传统 FSOP vs House of Apple

- **传统 FSOP**:伪造整个 vtable(指向我们控制的内存,里面放 system)。但 vtable 检查加强后失效。
- **House of Apple**:不伪造 vtable,用合法表偏移(第 6 关)。

FSOP 是"框架",House of Apple 是"在新时代实现框架的具体招式"。

### 4. 另一种触发:puts/printf 也能刷

除了 exit,`puts`、`printf` 等输出函数在刷新缓冲区时,也会走 vtable。所以有些攻击不走 exit,而是劫持 `puts` 的输出过程——这就是 House of Apple 2/3 的思路。

游戏翻译:不一定等游戏退出刷卡——你打印一句话时也会刷卡,抓住那个时机同样能触发。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 退出动画清单 | `_IO_list_all` 链表 |
| 保存存档 | `_IO_flush_all_lockp` |
| 假存档卡 | fake FILE |
| 刷卡条件 | 刷新前的 flags/write_ptr 检查 |

---

## 🎯 本关任务:观察 FILE 链表

```bash
gdb ./程序
(gdb) p _IO_list_all
(gdb) p *(struct _IO_FILE_plus*)_IO_list_all
(gdb) p _IO_2_1_stdout_
```

看看链表里有哪些 FILE 结构,stdout 的 vtable 指针指向哪里。建立"链表 → FILE → vtable"的直观认识。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| FSOP | 篡改FILE链表,exit/输出时劫持控制流 |
| 三要素 | 控制链表 + 伪造FILE + 触发刷新 |
| 与传统关系 | FSOP是框架,House of Apple是新时代实现 |
| 触发时机 | exit 或 puts/printf 刷新 |

---

## 🎬 下一关预告

**第 8 关 · largebin attack：大柜子的秘密**

House of Apple 和 FSOP 的前置都是"任意地址写一个堆地址"——这靠 largebin attack 实现。下一关我们拆解这个现代任意写技术:large bin 插入排序时的链表操作怎么被利用。搞懂它,House of Apple 的前半段就通了。
