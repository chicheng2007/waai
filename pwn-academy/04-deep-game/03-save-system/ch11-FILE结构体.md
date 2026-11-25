# 第 11 关 · FILE 结构体：存档里的每一格

## 🎬 游戏开场

我们一直在说"存档卡"(FILE 结构),但没真正打开看过它长什么样。这一关,我们把这张卡的每一格都翻出来看看,搞清楚哪些格子对攻击有用。

`_IO_FILE` 是 glibc 里表示"一个输入输出流"的结构。stdout、stdin、stderr 各是一个。它里面记录了缓冲区在哪、读写到哪了、当前是什么模式,以及最重要的——技能表(vtable)指针。

---

## 🧠 核心概念（游戏版）

### 1. FILE 结构的关键字段

```c
struct _IO_FILE {
    int  _flags;              // 状态标志(读/写/缓冲模式等)
    char *_IO_read_ptr;       // 读缓冲当前位置
    char *_IO_read_end;       // 读缓冲结束
    char *_IO_read_base;      // 读缓冲起点
    char *_IO_write_base;     // 写缓冲起点
    char *_IO_write_ptr;      // 写缓冲当前位置
    char *_IO_write_end;      // 写缓冲结束
    char *_IO_buf_base;       // 缓冲区起点
    char *_IO_buf_end;        // 缓冲区终点
    ...
    struct _IO_wide_data *_wide_data;  // 宽字符数据(House of Apple关键)
    ...
};
// _IO_FILE_plus = _IO_FILE + vtable指针
struct _IO_FILE_plus {
    _IO_FILE file;
    const struct _IO_jump_t *vtable;   // 技能表!
};
```

游戏翻译:存档卡上有很多格子——缓冲区位置、读写进度、模式标志,还有一张"技能表地址"和"宽字符备注栏"(House of Apple 的关键)。

### 2. 攻击时最关心的格子

| 字段 | 为什么重要 | 攻击用途 |
| --- | --- | --- |
| `_flags` | 决定刷新时的条件判断 | 伪造假FILE要设对 |
| `_write_base/_write_ptr` | 决定"有没有数据要写" | 满足条件才触发刷新 |
| `_wide_data` | 宽字符流的数据 | House of Apple 劫持点 |
| `vtable` | 技能表指针 | 指向合法偏移绕过检查 |
| `_fileno` | 文件描述符 | 某些攻击要设成1(stdout) |

### 3. 刷新的条件判断

`_IO_flush_all_lockp` 刷新一个 FILE 前,大致检查:

```c
if (fp->_mode <= 0 && fp->_IO_write_ptr > fp->_IO_write_base)
    // 或者 vtable 的 overflow 存在
    调用 vtable->__overflow(fp)
```

游戏翻译:管理员刷卡前先看"这张卡有没有要写的数据"(write_ptr > write_base)。你伪造假卡时,得把这几个格子设成"有数据要写",管理员才会刷它。

### 4. vtable 是什么样?

vtable(`_IO_jump_t`)是一堆函数指针的集合:

```c
struct _IO_jump_t {
    size_t __dummy;
    size_t __dummy2;
    void (*__finish)(...);
    void (*__overflow)(...);     // 缓冲满时调用
    ...
};
```

每个 FILE 类型(stdout/stdin/stderr)有自己的 vtable:`_IO_file_jumps`、`_IO_wfile_jumps` 等。它们都在 libc 的只读数据区——这就是 vtable 检查的"合法区域"。

游戏翻译:技能表是一排按钮(函数指针),不同存档卡配不同的技能表。这些表都印在 libc 的只读手册上。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 存档卡 | `_IO_FILE_plus` |
| 模式标志 | `_flags` |
| 读写进度格 | `_write_ptr/_write_base` 等 |
| 宽字符备注栏 | `_wide_data` |
| 技能表 | vtable (`_IO_jump_t`) |

---

## 🎯 本关任务:查看一个真实的 FILE

```bash
gdb ./程序
(gdb) p _IO_2_1_stdout_
(gdb) p/x _IO_2_1_stdout_.vtable
(gdb) p _IO_file_jumps
```

逐个字段对照上面的结构,看看 stdout 的各个格子的值。特别注意 vtable 指向哪里。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| FILE结构 | 记录流状态 + vtable + wide_data |
| 关键字段 | flags/write_ptr/wide_data/vtable |
| 刷新条件 | write_ptr > write_base 才刷 |
| vtable | 函数指针表,在libc只读区 |

---

## 🎬 下一关预告

**第 12 关 · vtable：技能表与反作弊的军备竞赛**

vtable 检查是怎么一步步加强的?攻击者又是怎么从"随便伪造"进化到"用合法偏移"的?下一关讲清楚这场"技能表攻防战"的演化史。这是理解 House of Apple 为什么这样设计的关键。
