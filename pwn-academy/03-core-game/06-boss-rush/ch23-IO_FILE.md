# 第 23 关 · IO_FILE：游戏的存档系统

## 🎬 游戏开场

游戏里有个不起眼但无处不在的系统:**存档/日志系统**。

每次程序打印文字(`printf`)、读取输入(`scanf`)、在退出时清理现场(`exit`),都在跟这个系统打交道。它用一个叫 **FILE 结构体**的"存档文件"记录每个输入输出通道的状态(stdin、stdout、stderr 都是一个个 FILE 结构)。

你可能会问:一个打印系统,怎么变成攻击入口?

答案:**这个"存档文件"里也藏着函数指针(技能表 vtable)**。当你能篡改 FILE 结构里的内容时,就能在程序`exit`或刷新输出时,让它调用你指定的函数——这就是 **FSOP**(File Structure Oriented Programming)。

游戏比喻:你没攻击游戏的战斗系统,而是偷偷改了"存档文件"里的"退出时要执行的动作",游戏一保存退出,就执行了你的作弊指令。

这在**栈和堆的主流招式都被封死**(Full RELRO 改不了 GOT、NX 不能执行代码)时,是最后的杀手锏,也是现代 CTF 堆题的标配收尾方式。

---

## 🧠 核心概念（游戏版）

### 1. FILE 结构体是什么?

每个打开的文件/流,都对应一个 `_IO_FILE` 结构体,里面有一堆字段。关键的几个:

```
struct _IO_FILE {
    int flags;           ← 状态标志(读/写/缓冲模式)
    char* read_ptr;      ← 读指针
    char* write_base;    ← 写缓冲区起点
    char* write_ptr;     ← 写缓冲区当前位置
    ...
    void* vtable;        ← 技能表指针！（指向一堆函数指针）
}
```

**vtable(虚表)**:一张"技能清单",里面是各种操作函数的指针(如 `_IO_file_overflow`、`_IO_file_xsputn` 等)。程序操作 FILE 时,会通过 vtable 调用对应函数。

游戏比喻:FILE 结构是"存档卡",vtable 是这张卡背面的"技能按钮清单"——刷卡时会按清单上的按钮执行动作。

### 2. 攻击思路:伪造 FILE + FSOP

**FSOP 的核心**:

1. 系统有个全局链表 `_IO_list_all`,把所有 FILE 结构串起来(stdout 在里面)。
2. 程序 `exit` 时会遍历这个链表,对每个 FILE 调用 `_IO_flush_all_lockp` → 通过 vtable 调用写函数。
3. 如果你能伪造一个 FILE 结构,把 `_IO_list_all` 指向它,并把它的 vtable 改成你构造的假技能表(里面放 `system`),那么 exit 时就会调用 system!

游戏比喻:你在"存档系统"的链表里塞了一张假存档卡,卡的技能按钮被你重画成"打开 shell";系统退出时挨个刷卡,刷到你的假卡,就按了你画的按钮。

### 3. vtable 检查的演化(为什么要"House of Apple")

glibc 后来加了检查:调用 vtable 前,验证 vtable 指针必须指向合法的只读区域(`__libc_IO_vtables`),随便伪造会被拦。

于是黑客们找到绕过办法:不伪造整个 vtable,而是**在合法的 vtable 区域里找一个"偏移"**——把 vtable 指针指向合法表的中间某个位置,让调用的"按钮"恰好是一个有用的函数(如 `_IO_wfile_jumps` 配合特定字段可以劫持控制流)。

**House of Apple** 就是 glibc 2.35 时代最流行的这种绕过技术——进阶版第 6 关会完整讲。基础版你只需知道这个演进逻辑:

> 检查越严 → 骗局越精巧 → 从"随便伪造"进化到"借合法表的偏移"。

### 4. 更简单的入口:改 stdout 泄露 / 改 vtable 指针

难度递进:

- **低难度**:利用 FILE 结构泄露 libc(stdout 的结构里有 libc 指针)。
- **中难度**:改 `_IO_2_1_stdout_` 的 flags,让它打印出内存(配合黑科技)。
- **高难度**:完整 FSOP → House of Apple → get shell。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 存档系统 | IO_FILE / stdio |
| 存档卡 | `_IO_FILE` 结构体(`_IO_FILE_plus`) |
| 技能清单 | vtable |
| 存档链表 | `_IO_list_all` |
| 退出刷卡 | `_IO_flush_all_lockp` (exit 时) |
| 假技能表 | fake vtable / House of Apple |

---

## 🎯 闯关任务:观察 stdout 结构

```bash
gdb ./任意程序
(gdb) p _IO_2_1_stdout_     # 查看stdout的FILE结构
(gdb) p/x &_IO_2_1_stdout_  # 它的地址(libc里)
```

观察里面有没有 libc 地址、vtable 指针长什么样。感受一下这个"存档卡"的结构。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| IO_FILE | 程序的存档/日志系统,含函数指针 |
| vtable | FILE 的技能清单,可被劫持 |
| FSOP | 伪造 FILE + 改链表 → exit 时劫持控制流 |
| vtable 检查 | 越来越严 → House of Apple 等绕过 |

---

## 🎬 下一关预告

**第 24 关 · 沙箱与 ORW：禁魔模式怎么通关**

有些题目更狠:程序开了 **seccomp 沙箱**,直接把 `execve`(开 shell 用的系统调用)禁掉了。这意味着就算你拿到 system,也开不了 shell——游戏进入"禁魔模式",大招被封。

怎么办?不拿 shell,直接**用 open/read/write 读旗子文件**——这招叫 **ORW(Open-Read-Write)**。下一关,我们学会在禁魔模式下用"基础攻击"通关。
