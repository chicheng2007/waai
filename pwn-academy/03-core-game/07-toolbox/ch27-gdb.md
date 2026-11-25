# 第 27 关 · gdb：慢动作回放与透视挂

## 🎬 游戏开场

游戏卡关了?你想知道"到底哪一步出错了吗"?

普通玩家反复重试;高手开**慢动作回放 + 透视挂**——一步一步看程序在干什么,每个口袋(寄存器)里是什么,每格内存里是什么。

这就是 **gdb**: Linux 下最强的调试器。配合 pwndbg 插件,它能:

- 在指定位置**打断点**(游戏暂停)
- **单步执行**(一帧一帧看)
- **查看寄存器/内存/栈**
- **看堆布局**(堆题神器)

这一关教你最常用的操作,够你调试绝大多数题目。

---

## 🧠 核心概念（游戏版）

### 1. 启动与打断

```bash
gdb ./vuln              # 启动
(gdb) start             # 在main停下
(gdb) break func        # 在函数func打断点
(gdb) break *0x401176   # 在具体地址打断点
(gdb) run               # 运行(到断点停)
(gdb) continue          # 继续运行到下一个断点
```

### 2. 单步执行(慢动作)

```bash
(gdb) stepi    # 执行一条汇编指令(最细)
(gdb) nexti    # 执行一条汇编,但不进入函数
(gdb) si / ni  # stepi/nexti的简写
```

看汇编单步,是 PWN 调试的核心——你要看清楚 rip 怎么走、栈怎么变。

### 3. 查看"口袋"(寄存器)

```bash
(gdb) info registers        # 所有寄存器
(gdb) p $rsp                # 看某个寄存器
(gdb) p/x $rax              # 十六进制显示
```

### 4. 查看内存(透视)

```bash
(gdb) x/20gx $rsp       # 从rsp开始,看20个8字节(g=8字节,x=十六进制)
(gdb) x/32bx 0x401000   # 看32个字节
(gdb) x/s 0x401024      # 当字符串看
(gdb) x/10i $rip        # 看即将执行的10条指令
```

`x/` 命令格式:`x/数量 格式 地址`。格式:`g`=8字节,`w`=4字节,`x`=16进制,`s`=字符串,`i`=指令。

### 5. 查看栈帧

```bash
(gdb) info frame     # 当前栈帧信息
(gdb) bt            # 调用栈回溯(backtrace)
```

### 6. pwndbg 增强命令(强烈推荐)

装了 pwndbg 后:

```bash
heap        # 显示堆的所有chunk布局(堆题神器!)
bins        # 显示各bin的链表状态
checksec    # 看保护
vmmap       # 看内存映射
find        # 在内存里搜字节
search      # 搜ROP gadget
context     # 一屏显示所有关键信息(汇编/寄存器/栈)
```

### 7. 实用调试技巧

- **崩溃分析**:程序崩了,用 `bt` 看调用栈,`x/i $rip` 看崩在哪条指令。
- **测偏移**:用 cyclic pattern 让程序崩溃,然后 `cyclic_find($rsp)` 自动算偏移。
- **观察 payload**:断点设在 `ret` 前,看栈上是不是你要的ROP链。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语/命令 |
| --- | --- |
| 慢动作 | stepi / nexti |
| 暂停点 | break |
| 透视 | x/ 查看内存 |
| 看口袋 | info registers |
| 堆布局透视 | pwndbg heap |

---

## 🎯 闯关任务:单步跟一次栈溢出

用第 7 关的 vuln 程序:

```bash
gdb ./vuln
(gdb) break vulnerable
(gdb) run
(gdb) stepi    # 一路单步
(gdb) info registers
(gdb) x/20gx $rsp
```

在 `gets` 返回后、函数 `ret` 前,查看栈上的返回地址是不是被你的输入覆盖了。亲眼看到"回城卷轴被涂改"的那一刻,你会对栈溢出有全新的理解。

---

## 📌 本关小结

| 命令 | 用途 |
| --- | --- |
| break / run / continue | 断点与运行 |
| stepi / nexti | 单步执行 |
| info registers | 看寄存器 |
| x/ | 看内存 |
| heap / bins / vmmap | pwndbg 增强 |

---

## 🎬 下一关预告

**工具箱毕业,BOSS 战开始!**

第 28、29 关,我们将完整复盘两道真实题目(一道栈、一道堆),从 checksec 到构造 exp,把前面 27 关的所有技能串起来。这是你从"学招式"到"独立通关"的最后一跃!
