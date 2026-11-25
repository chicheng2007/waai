# 第 21 关 · unsorted bin 与 House 连招

## 🎬 游戏开场

在回收站的分类里,大柜子(≥0x400)会先进入 **unsorted bin**(待分类中转站)。这个中转站有个神奇的性质:

> 一个大柜子被 free 后,它的 fd/bk 指针会指向 **main_arena**——一个位于 **libc 里**的结构体地址。

这意味着什么?**你 free 一个大柜子,就能白捡一个 libc 地址!** 泄露它,减去偏移,libc 基址到手——和第 10 关 ret2libc 的思路一脉相承,只不过泄露源从 GOT 换成了堆。

至于那些听起来很酷的 **"House of XXX"** 招式名,其实是国外黑客给各种堆利用套路起的绰号(就像格斗游戏的连招名)。这一关我们认识几个经典的,看懂它们的思路。

---

## 🧠 核心概念（游戏版）

### 1. unsorted bin 泄露 libc

```
1. malloc 一个大chunk(比如0x500),再malloc一个小chunk防止合并
2. free 大chunk → 它进 unsorted bin
3. 现在大chunk的 fd/bk 都指向 main_arena（libc地址）
4. 通过UAF或"use-after-free读取"把它打印出来 → libc 基址到手！
```

游戏比喻:你退租一个大柜子,系统在中转站里给它贴的"上家/下家"纸条上,写着libc总部的地址——你偷看一眼,就知道整个 libc 城市搬哪去了。

注意:要读出 fd/bk,通常需要程序有"打印 chunk 内容"的功能(UAF 读),或者用 show 功能。

### 2. House 系列是什么?

"House of ..." 是一系列堆利用技术的命名传统,源自一篇叫《The House of Lore》的文章,后来大家沿用这个"House of X"的命名。它们大多是**利用特定的堆状态构造出任意写或直接控制流劫持**的套路。

新手先认识这几个名字和核心思想:

| 招式名 | 游戏化理解 | 核心 |
| --- | --- | --- |
| **House of Force** | 骗管理员说"还有无限大的空地" | 篡改 top chunk 的 size 为超大值,下次 malloc 任意地址 |
| **House of Orange** | 主动制造一个"特殊大柜"触发系统整理 | 伪造 top chunk size 触发 sysmalloc,得到 unsorted bin chunk 泄露 libc |
| **House of Einherjar** | 骗系统做"向后合并" | 篡改 prev_size,free 时合并到任意地址 |
| **House of Lore** | 伪造 small bin 链表 | 在小柜分类架上塞假柜子 |
| **House of Spirit** | 在栈上伪造一个柜子再 free | 把栈上的假 chunk 送进回收站 |

### 3. 挑两个细看

**House of Force(经典但新版本已受限)**:

`top chunk` 是堆末尾的"边角料大块"。malloc 时,系统会从 top chunk 切一块给你。如果我能把 top chunk 的 size 改成一个巨大的数,那么下次 malloc 一个超大的 size,系统计算出的新 chunk 地址可能是**任意地址**(因为 `新top = old_top + size` 溢出或跳到目标)。

游戏比喻:你骗管理员"这个边角料有 100 公里长",于是他切给你一块"100 公里外"的地方——正好是你要攻击的目标地址。

(2.29+ 加了检查:malloc 的 size 不能超过 top chunk 的剩余量,所以这招在新版本基本失效。)

**House of Orange**:

当 top chunk 不够大时,malloc 会调用 `sysmalloc` 向系统要新内存,顺便把旧的 top chunk 扔进 unsorted bin。通过伪造 top chunk 的 size 让它"看起来不够大",可以主动触发这个过程,凭空造出一个 unsorted bin chunk 来泄露 libc——**即使程序没有 free 大 chunk 的功能**。

游戏比喻:你故意把"边角料"的标签改小,逼系统换新的边角料,换下来的旧的自动进了中转站,你就能偷看它的 libc 地址。

### 4. House 系列的现代演变

新版本 glibc 检查越来越严,老的 House 招式很多失效了,但新招式不断涌现——最有名的是 **House of Apple**(glibc 2.35 时代的主流),它利用 IO_FILE 结构,进阶版第 6 关专门讲。

> 🎮 一句话:House 系列是"针对堆管理器某个特定机制的精妙骗局",版本越新,骗局越精巧。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 大柜中转站 | unsorted bin |
| libc 总部地址 | main_arena 地址 |
| 无限空地骗局 | House of Force(top chunk 篡改) |
| 逼系统换料 | House of Orange |
| 向后合并骗局 | House of Einherjar |

---

## 🎯 闯关任务:unsorted bin 泄露实战

```c
// leak.c
#include <stdio.h>
#include <stdlib.h>
char *p;
int main() {
    p = malloc(0x500);      // 大chunk
    malloc(0x20);           // 防止和top合并
    free(p);                // p进unsorted bin
    // 假设有UAF读:打印 p 的前8字节(fd)
    printf("fd = %p\n", *(void**)p);   // 这是 main_arena 地址！
}
```

```bash
gcc -g leak.c -o leak && ./leak
```

输出的 fd 是 libc 里的地址。用 `vmmap`(gdb)查看 libc 基址,验证 `fd - libc_base` 是不是个固定偏移。这验证了 unsorted bin 泄露 libc 的原理。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| unsorted bin 泄露 | free大chunk → fd/bk指向main_arena → libc基址 |
| House 系列 | 各种针对堆机制的精妙骗局绰号 |
| House of Force | 篡改top chunk size → 任意地址malloc(旧版) |
| House of Orange | 伪造top size触发sysmalloc造泄露 |
| 现代演变 | 老招式失效,新招式(House of Apple)崛起 |

---

## 🎬 下一关预告

**第 22 关 · 堆风水:提前摆好储物柜**

堆利用最难的不是"知道招式",而是"创造条件"——你需要目标 chunk 恰好出现在合适的位置。这需要像 Feng Shui(风水)一样**精心摆放堆布局**。

下一关我们讲怎么通过控制分配/释放的顺序,把堆排成你想要的形状。这是堆篇的收官,也是从"会招式"到"能做真实堆题"的关键。
