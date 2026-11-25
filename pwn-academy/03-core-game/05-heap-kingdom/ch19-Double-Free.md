# 第 19 关 · Double Free：退租两次的骗局

## 🎬 游戏开场

你去储物柜中心,把柜子退租了一次。然后又去退租**同一个柜子**——明明你已经没有它了,却骗管理员说"我还要退这个"。

正常情况下管理员会拒绝:"这柜子已经是空的了,你没资格退!"

但如果管理员的检查有漏洞(比如他只看你手里的纸条,不核对记录),你可能骗他把这个空柜子**在回收名单上登记两次**。

结果:回收站里,同一个柜子出现了两个位置。当你再申请柜子时,系统两次都把这个柜子分给你——**你拿到了两个指向同一块内存的指针**。

更妙的是,如果中间你还能往这个"双重登记"的柜子里写点东西,就能篡改回收站的链表指针,让系统在**你指定的任意地址**造一个假柜子。这就是 double free 的威力。

---

## 🧠 核心概念（游戏版）

### 1. 什么是 Double Free?

```c
char *p = malloc(0x20);
free(p);   // 第一次退租
free(p);   // 第二次退租 —— Double Free!
```

同一块内存被 free 两次。系统这本账就乱了。

### 2. 系统为什么会中招?

回顾第 17 关:free 一个 chunk 后,系统把它的地址放进回收站的链表(fastbin/tcache)。

```
fastbin:  [p] → ...
```

如果你再 free(p) 一次,系统检查:"队头的柜子是不是就是 p?"——如果是,它会**误以为你是在连续释放同一个正常操作**,直接放行:

```
fastbin:  [p] → [p] → ...   ← 同一个柜子出现两次!
```

(glibc 的检查只防"连续的 double free",所以用 A→B→A 的顺序可以绕过。tcache 的检查在 2.29 前后有变化,进阶版细讲。)

### 3. 从"一房二卖"到"任意地址造柜"

Double Free 的真正杀招是配合**修改 fd 指针**:

场景(fastbin attack 的经典流程):

```
1. malloc A, B   (A、B 是同大小的小柜子)
2. free(A)       → fastbin: [A]
3. free(B)       → fastbin: [B] → [A]
4. free(A)       → fastbin: [A] → [B] → [A]   (double free,A出现两次!)
5. malloc 一次   → 拿到 A,趁机往 A 的数据区写入 fake_addr(篡改 fd)
6. 现在 fastbin: [B] → [A] → [fake_addr]
7. malloc B → malloc A → malloc → 返回 fake_addr!  ← 在假地址造出了柜子
```

第 7 步,系统把 `fake_addr` 当成了一个空闲柜子返回给你——而那个地址可以是**任意地方**(比如 GOT 表附近)。你往里写东西,就等于改了那个地方。

游戏比喻:你在回收名单上动手脚,把"下一个空格"的纸条改成"银行金库的地址",系统下次真带你去金库开个柜子。

### 4. 检查与反检查

glibc 后来加了很多检查来防这些:

| 检查 | 游戏说法 | 绕过 |
| --- | --- | --- |
| tcache key(2.29+) | 退租时盖章,重复退会被发现 | 改 key / UAF 覆盖 |
| safe-linking(2.32+) | 链表地址打码,看不清真实值 | 泄露堆地址后解码 |
| align_check | 柜子地址必须对齐 | 找合适的假地址 |

这就是为什么堆利用"版本相关"——不同 glibc 版本,攻防规则不同。基础版先掌握思想,进阶版逐版本细讲。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 退租两次 | double free |
| 一房二卖 | 同一 chunk 返回两次 |
| 篡改"下一个空格"纸条 | 覆盖 fd 指针 |
| 在假地址造柜 | 任意地址 malloc / arbitrary write |

---

## 🎯 闯关任务:观察 double free

写程序(用老版本 glibc 或用 tcache 绕过技巧):

```c
// df.c
#include <stdlib.h>
int main() {
    char *a = malloc(0x20);
    char *b = malloc(0x20);
    free(a);
    free(b);
    free(a);      // double free
    char *c = malloc(0x20);
    char *d = malloc(0x20);
    char *e = malloc(0x20);
    printf("a=%p b=%p c=%p d=%p e=%p\n", a,b,c,d,e);
}
```

```bash
gcc -g df.c -o df
./df
```

观察:如果 c、d、a 出现相同地址,说明 double free 让你拿到了重复柜子。如果直接报错 `double free or corruption`,说明 check 拦住了——这正是新版本 glibc 的行为,你需要进阶技巧。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| Double Free | 同一 chunk free 两次 |
| 骗过检查 | 用 A→B→A 顺序绕过连续检测 |
| 杀招 | 篡改 fd → 任意地址 malloc → 任意写 |
| 版本相关 | tcache key / safe-linking 会增加难度 |

---

## 🎬 下一关预告

**第 20 关 · tcache 与 fastbin：快速回收筐里的手脚**

上一关我们用了 fastbin/tcache 的机制,但没细讲。这一关专门攻克新版本 glibc 里最重要的两个回收筐:

- **tcache poisoning**:直接改 tcache 的 next 指针,下次 malloc 就返回任意地址——比 fastbin attack 更简单粗暴。
- **tcache dup**(double free 的 tcache 版)
- safe-linking 打码怎么破

这是现代堆题(glibc 2.31/2.35)的入门必修课。下一关见!
