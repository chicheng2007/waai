# 第 2 关 · malloc 源码：租赁系统的后台日志

## 🎬 游戏开场

你来到储物柜中心的后台,看到租赁管理员 `_int_malloc` 面前贴着一张**接单流程图**。每当有人来租柜子(malloc),他就照着这张图一步步找柜子。

今天我们就跟着他走一遍。你会发现,他找柜子的**先后顺序**极其重要——因为这决定了你构造的堆布局能不能生效。

---

## 🧠 核心概念（游戏版）

### 1. 管理员接单的总体流程

```
有人来租 size 大小的柜子
  │
  ├─① 先查 tcache 快速筐(有现成的?直接给,最快)
  │
  ├─② 再查 fastbin(小柜筐)
  │
  ├─③ 查 small bin(中柜架)
  │
  ├─④ "整理"unsorted bin(把中转站的柜子分类,顺便看有没有合适的)
  │      ├─ 找到精确合适的 → 直接给
  │      └─ 不合的 → 分类到 small/large bin
  │
  ├─⑤ 查 large bin(大柜架,找最小的能装下的)
  │
  ├─⑥ 从 top chunk(边角料)切一块
  │
  └─⑦ 都不行 → 向系统要新地(sysmalloc)
```

**游戏比喻**:管理员找柜子是"从快到慢、从小到大"搜一遍——先看门口快速筐,没有再看分类架,最后实在没有才切边角料。

**关键洞察**:tcache 优先级最高。这意味着**只要 tcache 里有货,系统绝不会去看其他 bin**。堆风水时,你要时刻算"tcache 是不是满的",否则布局全乱。

### 2. 源码片段(翻译成人话)

glibc 2.35 的 `_int_malloc` 里,tcache 检查在第一段:

```c
// 简化版
if (tcache != NULL && tc_idx < mp_.tcache_bins) {
    tcache_entry *e = tcache->entries[tc_idx];   // 取该大小筐的头
    if (e != NULL) {                              // 筐里有货
        tcache->entries[tc_idx] = e->next;        // 取出,链头后移
        return e;                                 // 直接返回给用户
    }
}
```

游戏翻译:"如果快速筐这个尺寸的格子里有柜子,就拿走最上面那个,把链头指向下一个,返回给用户。"

**注意** `e->next`——这就是 tcache poisoning 要改的指针(第 20 关)。系统无条件信任它,你改它指向哪,下次 malloc 就返回哪。

### 3. unsorted bin 的"整理"阶段

这是最精妙的一段。系统遍历 unsorted bin 时:

```c
while ((victim = unsorted_chunks(av)->bk) != unsorted_chunks(av)) {
    // 取出一个 chunk
    if (size == nb) {          // 大小刚好
        return victim;         // 直接给用户(unsorted bin attack 的机会)
    }
    // 否则分类到 small/large bin
}
```

游戏翻译:管理员把中转站的柜子挨个看——"这个尺寸正好?给你;不对?放到对应的分类架上去"。

**unsorted bin attack** 就是利用这里的链表操作:通过篡改 bk 指针,让系统在"整理"时把一个地址写进链表——实现 arbitrary write(基础篇第 21 关提到,进阶篇细讲)。

### 4. 从 top chunk 切

```c
victim = av->top;                    // 边角料
size = chunksize(victim);
if (size >= nb + MINSIZE) {          // 够大
    av->top = chunk_at_offset(victim, nb);  // 切一刀
    set_head(victim, nb | PREV_INUSE);
    return victim;
}
```

游戏翻译:边角料够大就切一块给你,剩下的还是边角料。**House of Force** 就是骗这里的 size 计算,让"切一刀"的位置落在任意地址。

### 5. 关键结论

| 你想让 malloc 返回哪里 | 需要控制的筐 |
| --- | --- |
| 任意地址 | tcache 的 next(最快,首选) |
| 伪造的假 chunk | fastbin 的 fd(需 size 匹配) |
| 利用整理过程写值 | unsorted bin 的 bk |

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 接单流程图 | `_int_malloc` 的控制流 |
| 快速筐优先 | tcache 优先级最高 |
| 中转站整理 | unsorted bin 遍历与分类 |
| 切边角料 | 从 top chunk 分配 |

---

## 🎯 本关任务:跟着源码走一遍

打开 glibc 源码,找到 `_int_malloc`,用 gdb 在你的程序里下一个断点:

```bash
gdb ./vuln
(gdb) break _int_malloc
(gdb) run
# 每次malloc都会停下,观察:
# 1. 这次是从tcache拿的,还是从别处?
# 2. tcache的entries数组里有什么?
(gdb) p mp_.tcache_bins
```

亲眼看着管理员按流程图找柜子,比读十遍源码都管用。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| malloc流程 | tcache→fastbin→small→unsorted→large→top→sysmalloc |
| tcache优先 | 筐里有货就直接给,不会看别的 |
| 源码信任指针 | e->next 无条件信任 → poisoning 根源 |
| unsorted整理 | 遍历分类时可被 unsorted bin attack 利用 |

---

## 🎬 下一关预告

**第 3 关 · free 源码:退柜子的完整流程**

malloc 看完了,看它的反面:free。退租时管理员要判断"放哪个筐、要不要和邻居合并、tcache 满了怎么办"——每一步都有可被利用的细节。下一关,跟着 `_int_free` 走一遍。
