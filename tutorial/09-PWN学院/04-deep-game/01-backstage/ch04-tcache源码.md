# 第 4 关 · tcache：快速回收筐的防伪印章

## 🎬 游戏开场

tcache(thread-local cache,线程本地缓存)是 glibc 2.26 引入的"VIP 快速筐"。它让 malloc/free 快了很多,但也带来了一堆新的利用手法。

管理员给这个筐加了两道防线:

1. **防伪印章(key)**:防止你把同一个柜子退租两次。
2. **地址打码(safe-linking)**:筐里的"下一个空格"纸条用密码写,你看不懂真实地址。

这一关,我们看这两道防线怎么工作,以及怎么绕过它们。这是现代堆利用(glibc 2.29+)的核心课题。

---

## 🧠 核心概念（游戏版）

### 1. 防线一:key 防伪印章

每个进 tcache 的 chunk,用户区第二个 8 字节被写入一个 `key`(通常是 tcache 结构地址):

```c
e->key = tcache;    // 盖章
```

free 时会检查:遍历 tcache 链,如果发现某个 chunk 的 key 等于当前 tcache 且地址相同,说明"这柜子已经在筐里了"→ 报 `double free or corruption` 错误。

游戏翻译:管理员给每个进筐的柜子盖个专属章。你再拿同一个柜子来退,他一翻记录"这章我盖过了"→ 拒绝。

**绕过方法**:

- **UAF 覆盖 key**:free 后通过悬垂指针把 key 字段清成 NULL,再 free 就不会被认出来。
- **double free 顺序**:先 free(a),再 free(b),再 free(a)——检查只扫当前筐,配合 key 操作可绕。
- 2.29 之前没有 key,直接 double free。

### 2. 防线二:safe-linking 地址打码

glibc 2.32 引入。tcache/fastbin 的 `next` 指针不再存真实地址,而是:

```c
// 存的时候(编码)
e->next = PROTECT_PTR(&e->next, next);
// PROTECT_PTR = (pos >> 12) ^ ptr
```

游戏翻译:纸条上的"下一个空格"被用密码写了——密码是"当前柜子地址右移12位"。你直接写一个真实地址进去,系统解码后得到一个乱七八糟的地址。

**破解**:你需要知道**堆地址**(用来算密码):

```python
# 编码:想让next指向target,存在chunk_addr处
encoded = (chunk_addr >> 12) ^ target
# 解码:看到encoded,算出真实next
real = (chunk_addr >> 12) ^ encoded
```

所以 safe-linking 的破解前提是**先泄露堆基址**(通过 UAF 读、unsorted bin 泄露的 fd 等)。

游戏翻译:密码是"柜子门牌号右移12位"。你得先知道柜子的门牌号(堆地址),才能写出正确的密码纸条。

### 3. key 与 next 字段的位置

```
free后的tcache chunk:
  ┌──────────────┐
  │ prev_size    │
  │ size         │
  ├──────────────┤ ← mem
  │ next(编码)    │ ← 8字节,2.32+被打码
  │ key          │ ← 8字节,防伪章
  └──────────────┘
```

**注意**:tcache 的 chunk 不需要 size 检查(不像 fastbin),所以 tcache poisoning 直接写 next 就行——这也是它比 fastbin attack 好用的原因。

### 4. 版本对照表(必背)

| 版本 | tcache | key | safe-linking | 典型绕过 |
| --- | --- | --- | --- | --- |
| 2.26-2.28 | ✅ | ❌ | ❌ | 直接 double free / 写 fd |
| 2.29-2.31 | ✅ | ✅ | ❌ | UAF 清 key |
| 2.32-2.33 | ✅ | ✅ | ✅ | 泄露堆址 + 编码 |
| 2.34+ | ✅ | ✅ | ✅ | 同上,hook 被移除(见后) |

### 5. 2.34 的重大变化:hook 被移除

glibc 2.34 移除了 `__free_hook`、`__malloc_hook` 等钩子——以前"劫持 hook → system"的套路失效了。现代(2.35)主流是利用 **IO_FILE / FSOP / House of Apple**(进阶篇第二大关)来拿 shell。

游戏翻译:管理员把"钩子按钮"拆了,你没法按了,得换一条路——去篡改存档系统(IO_FILE)。

---

## 🔧 真实世界对照

| 游戏说法 | 真实术语 |
| --- | --- |
| 防伪印章 | tcache key |
| 地址打码 | safe-linking (PROTECT_PTR) |
| 密码 | chunk_addr >> 12 |
| 钩子按钮被拆 | 2.34 移除 malloc/free hook |

---

## 🎯 本关任务:编码/解码练习

用 pwntools 模拟 safe-linking 编码:

```python
def protect(pos, ptr):
    return (pos >> 12) ^ ptr

chunk_addr = 0x555555559010
target = 0x555555558020
encoded = protect(chunk_addr, target)
print(hex(encoded))
# 解码验证
print(hex(protect(chunk_addr, encoded)))  # 应该 == target
```

理解这个公式后,你就能在 2.32+ 的题目里正确构造 tcache poisoning 的 next 值。

---

## 📌 本关小结

| 你学会了 | 一句话记忆 |
| --- | --- |
| key | 防伪章,防double free,UAF清key绕过 |
| safe-linking | next=(addr>>12)^ptr,需泄露堆址 |
| 编码解码 | protect(pos,ptr) = (pos>>12)^ptr |
| 版本演进 | 2.34移除hook → 转向IO_FILE |

---

## 🎬 下一关预告

**第 5 关 · bins 与反作弊检查机制演化**

我们把 bins 的链表维护(unsorted/small/large)和 glibc 历年加的所有检查串成一张"反作弊演化年表"。这一关是后台篇的收官,也是你理解"为什么招式越来越难"的总纲。
