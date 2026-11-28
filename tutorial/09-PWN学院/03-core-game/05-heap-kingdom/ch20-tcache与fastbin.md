# 第 20 关 · tcache 与 fastbin：快速回收筐里的手脚

## 🎬 游戏开场

回到储物柜中心的两个"快速回收筐":

- **fastbin**:老牌小柜筐,单链表,后进先出。
- **tcache**:新版的"VIP 快速筐",每个大小最多放 7 个,优先级最高——你 malloc 时系统先翻它。

这两个筐的链表指针都**存在被释放柜子自己的数据区里**,而且系统**相当信任这些指针**。

于是玩家的手脚就来了:

- 偷偷改筐里柜子的"下一个"指针 → 下次 malloc 直接返回你指定的地址(**poisoning / 投毒**)。
- 让同一个柜子在筐里出现两次 → 拿到重复柜子(**dup / 复制**)。

新版本给 tcache 加了"盖章"(key)和"地址打码"(safe-linking),但都有破解办法。这一关我们逐个击破。

---

## 🧠 核心概念（游戏版）

### 1. tcache 的结构

tcache 为每个大小维护一条链,每条最多 7 个:

```
tcache_entry(存在chunk用户区):
  ┌────────────┬────────────┐
  │ next       │ key        │
  └────────────┴────────────┘
   指向下一个   ←, 
```

- `next`:下一个空闲 chunk 的地址(2.32 之后被 safe-linking 打码)。
- `key`:指向 tcache_perthread_struct 的指针,用来检测"这个 chunk 是不是已经在这个筐里了"(防 double free)。

### 2. tcache poisoning(投毒)—— 最简单粗暴

**思想**:改掉 tcache 里某个 chunk 的 `next` 指针,让它指向 `target_addr`。下次 malloc 两次,第二次就返回 `target_addr`。

```
1. free(a)          → tcache: [a]
2. 通过UAF或写漏洞改 a->next = target_addr
3. malloc()         → 拿到 a
4. malloc()         → 拿到 target_addr ！← 在目标地址造柜
```

游戏比喻:你把回收筐里柜子的"下一个空格"纸条,改成了"金库地址",系统下次就带你去金库。

**配合 UAF 使用**:如果 free 后还能写这个 chunk(第 18 关),就能改它的 next。

### 3. tcache dup(复制)

tcache 版的 double free。2.29 之前的 glibc:直接 `free(a); free(a)` 就能让 a 在筐里出现两次。

2.29 加了 key 检查:free 时会看 key,发现重复就报错。绕过办法:

- free 之后把 key 字段清掉(通过 UAF 写)。
- 或用 double free 的经典 A→B→A 顺序。

### 4. safe-linking(2.32+)—— 地址打码

新版本把 next 指针"打码"存储:

```
存的值 = (chunk_addr >> 12) XOR next_addr
```

游戏比喻:回收筐里的"下一个空格"纸条被**用密码写了**,你看不懂真实地址。但如果**你知道堆的地址**(比如通过 UAF 泄露),就能算出密码(堆地址>>12),把打码的值还原成真实地址,再伪造打码后的目标地址。

破解前提:**先泄露堆基址**——这也常通过 UAF/格式化字符串实现。

### 5. fastbin attack 对比

fastbin 类似,但:
- 没有 key 检查(所以 double free 更直接)。
- 有 size 检查:取出的 chunk 的 size 必须匹配对应 fastbin,所以目标地址附近要有个"看起来 size 正确"的假 chunk。

经典目标:改写 `__malloc_hook` 附近的内存(malloc_hook 前面有个 0x7f 的假 size),然后 malloc 触发 hook。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 快速筐 | tcache |
| 投毒 | tcache poisoning |
| 复制 | tcache dup |
| 盖章 | tcache key |
| 地址打码 | safe-linking |
| 钩子 | __malloc_hook / __free_hook |

**版本速查**:

| glibc | tcache | key | safe-linking |
| --- | --- | --- | --- |
| 2.26-2.28 | 有 | 无 | 无 |
| 2.29-2.31 | 有 | 有 | 无 |
| 2.32+ | 有 | 有 | 有 |

---

## 🎯 闯关任务:tcache poisoning 小实验

```c
// poison.c
#include <stdlib.h>
#include <stdio.h>
char target[32];   // 目标:让malloc返回这里的地址
int main() {
    char *a = malloc(0x40);
    free(a);
    // 假设有个UAF漏洞能改 a->next:
    *(void**)a = target;    // 把next改成target
    malloc(0x40);           // 返回a
    char *b = malloc(0x40); // 应该返回target
    printf("b=%p target=%p\n", b, target);
}
```

```bash
gcc -g -O0 poison.c -o poison && ./poison
```

(注意:2.32+ 需要按 safe-linking 编码 next。这里用老版本或直接观察。)

看 b 是否等于 target——等于就说明投毒成功!

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| tcache poisoning | 改 next 指针 → malloc 返回任意地址 |
| tcache dup | 筐里放两个相同 chunk |
| key | 防重复 free 的盖章,可绕过 |
| safe-linking | next 打码,需泄露堆址解码 |
| fastbin attack | 需伪造 size 的检查 |

---

## 🎬 下一关预告

**第 21 关 · unsorted bin 与 House 连招**

除了快速筐,大柜子走的是 unsorted bin。它有个 magical 特性:释放后会得到** libc 的地址**(main_arena)!

- 泄露 libc 基址(unsorted bin 泄露)
- largebin attack
- 各种 House 系列连招的名字由来(House of Force、House of Orange...)

下一关我们揭开这些"招式名"背后的原理。堆篇接近尾声,坚持住!
