# 第 3 关 · free 源码：退柜子的完整流程

## 🎬 游戏开场

接单流程(malloc)看完了,现在站在退租窗口看 `_int_free`。

每当有人说"我要退租这个柜子",管理员要做一系列判断:

- 这个柜子有多小?能不能进快速筐?
- 快速筐满没满(最多7个)?
- 邻居柜子是不是也空着?要不要合并成大柜?
- 有没有盖章(key)防止重复退租?

每一步判断都藏着利用空间。这一关我们跟着 free 走一遍。

---

## 🧠 核心概念（游戏版）

### 1. free 的总体流程

```
有人退租 chunk P
  │
  ├─① 基本检查:地址对齐?size合法?不是top chunk?
  │
  ├─② 小柜子 → 尝试放 tcache
  │     ├─ 筐没满(≤7) → 放进筐,盖章(key),结束!
  │     └─ 筐满了 → 继续往下
  │
  ├─③ fastbin 范围 → 放进 fastbin,结束
  │
  ├─④ 检查前后邻居是否空闲 → 合并(coalesce)
  │
  ├─⑤ 放进 unsorted bin
  │
  └─⑥ 如果很大 → 可能还给系统(munmap/trim)
```

游戏翻译:退租时优先塞进快速筐(最快),塞不下就看小柜筐,再不行就检查能不能和邻居合并,最后进中转站。

### 2. tcache 放入的源码(关键!)

```c
// 简化(glibc 2.35)
if (tc_idx < mp_.tcache_bins && tcache && tcache->counts[tc_idx] < mp_.tcache_count) {
    tcache_put(p, tc_idx);   // 放进筐
    return;                  // 结束!注意:这里的return很关键
}
```

`tcache_put` 里:

```c
static void tcache_put(mchunkptr chunk, size_t tc_idx) {
    tcache_entry *e = (tcache_entry *)chunk2mem(chunk);
    e->key = tcache;                          // 盖章:记录"我已在这个筐"
    e->next = tcache->entries[tc_idx];        // next指向原链头
    tcache->entries[tc_idx] = e;              // 更新链头
    ++(tcache->counts[tc_idx]);
}
```

**游戏翻译**:

- `e->key = tcache`:给柜子盖个章,证明"它在快速筐里"。这是防 double free 的 key(第 4 关详讲)。
- `e->next = 原链头`:柜子里的"下一个空格"纸条指向原来的第一个。LIFO(后进先出)。

**利用点**:`e->next` 写在**用户数据区**——如果你能在 free 之后再写这个 chunk(UAF),就能改 next = tcache poisoning。

### 3. 关键洞察:tcache 里的 return

注意上面 `tcache_put` 后有 `return`——**只要 tcache 没满,free 就结束了,不会合并邻居!**

这意味着:

- 小 chunk 进 tcache 后,**不会和相邻 chunk 合并**。
- 这改变了堆布局的行为,也让一些老招式(依赖合并)失效。

游戏翻译:管理员把柜子塞进快速筐就收工了,根本不检查邻居——以前会合并,现在不会。

### 4. 合并(coalesce)逻辑

当 chunk 没进 tcache/fastbin,走到合并阶段:

```c
// 向后合并(和前一个chunk)
if (!prev_inuse(p)) {
    prevsize = prev_size(p);
    p = chunk_at_offset(p, -prevsize);   // 把P往前挪到前一个chunk
}
// 向前合并(和后一个chunk)
nextchunk = chunk_at_offset(p, size);
if (!inuse(nextchunk)) {
    unlink(nextchunk);   // 从bin里摘掉
    size += nextsize;
}
```

游戏翻译:如果前后柜子空着,就拆掉中间的隔板,三个小柜合成一个大柜。`prev_size` 字段在这里被读取——**House of Einherjar 就是伪造 prev_size 骗它合并到任意地址**。

### 5. unlink 宏——经典攻击面

合并时调用的 `unlink` 宏,负责把 chunk 从 bin 链表摘除:

```c
#define unlink(P, BK, FD) {
    FD = P->fd;
    BK = P->bk;
    FD->bk = BK;      // ← 写操作
    BK->fd = FD;      // ← 写操作
}
```

如果攻击者能伪造 P 的 fd/bk,就能让这两行写操作写到任意地址——这就是经典的 **unlink attack**(老版本威力巨大,新版本加了双向链表检查)。

游戏翻译:摘柜子时要通知前后柜子"更新纸条",如果你伪造了前后柜子的门牌,通知就会发到错误的地方——任意地址写。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 退租流程 | `_int_free` |
| 盖章 | tcache key |
| 塞筐就收工 | tcache 里 return,不合并 |
| 拆隔板合并 | coalesce |
| 摘柜通知 | unlink 宏 |

---

## 🎯 本关任务:观察 free 的分支

```bash
gdb ./vuln
(gdb) break _int_free
(gdb) run
# 触发free,然后单步,看它走tcache分支还是合并分支
(gdb) p tcache->counts[tc_idx]
```

free 一个小 chunk,观察它进 tcache 后 counts 的变化;再 free 7 个同样的 chunk,看第 8 个开始走什么分支(不再进 tcache)。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| free流程 | 基本检查→tcache→fastbin→合并→unsorted |
| tcache return | 进筐就不合并,改变布局 |
| tcache_put | 盖章key + 写next(poisoning点) |
| 合并 | 读prev_size → House of Einherjar |
| unlink | 摘链写fd/bk → 经典攻击面 |

---

## 🎬 下一关预告

**第 4 关 · tcache 源码:快速回收筐的防伪印章**

free 和 malloc 都反复提到 tcache——这个"VIP 快速筐"是理解现代堆利用的钥匙。下一关我们专门拆它:key 盖章怎么防 double free、safe-linking 怎么给指针打码、以及各自的绕过方法。这是进阶篇最核心的一关之一。
