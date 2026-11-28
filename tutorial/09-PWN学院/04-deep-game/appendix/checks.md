# 附录 A · 反作弊（检查机制）演化速查表

> glibc 每加一道检查,就堵一批老招、逼出一批新招。这张表帮你快速判断"当前版本能用什么招"。

## 📅 版本检查年表

| 版本 | 新增检查/特性 | 失效的老招 | 主流新招 |
| --- | --- | --- | --- |
| 2.23~2.25 | 少 | — | 经典 UAF/double free/fastbin attack |
| 2.26 | tcache 引入 | — | tcache poisoning(更简单) |
| 2.27 | tcache 完善 | — | tcache dup, unsorted bin 泄露 |
| 2.28 | tcache count 检查 | 部分越界 | — |
| 2.29 | tcache key(盖章) | 直接 double free | UAF 清 key 绕过 |
| 2.30 | largebin 插入检查 | unsorted bin attack | largebin attack |
| 2.31 | — | — | tcache poisoning 主流 |
| 2.32 | safe-linking(指针打码) | 直接写 fd/next | 泄露堆址 + 编码 |
| 2.33 | IO 检查加强 | 部分 vtable 伪造 | — |
| 2.34 | 移除 malloc/free hook | hook 劫持 | IO_FILE / FSOP |
| 2.35 | vtable 检查加强 | 随便伪造 vtable | House of Apple(合法表偏移) |
| 2.36+ | 持续加固 | 老的 HoA 变体 | 新 HoA 变体 / 深挖 IO |

## 🎮 游戏版解读

```
每一版本 = 一次反作弊更新
新增检查   = 新加的规则
失效老招   = 被封的外挂
主流新招   = 玩家研究出的新外挂
```

## 🔍 快速判断流程

```
1. 确定 glibc 版本(ldd / strings libc)
   ↓
2. 查表:这个版本有哪些检查?
   ↓
3. 排除失效的老招
   ↓
4. 选当前版本的主流招式
   ↓
5. 针对性布置堆风水
```

## 📌 关键检查的游戏化记忆

| 检查 | 游戏说法 | 绕过核心 |
| --- | --- | --- |
| tcache key | 防伪盖章 | UAF 把章抹掉 |
| safe-linking | 地址打码 | 先搞到门牌号(堆址)再算密码 |
| vtable 检查 | 查技能表真伪 | 用官方表的中间按钮 |
| 移除hook | 拆了钩子按钮 | 转攻存档系统(IO_FILE) |
| largebin 检查 | 中转站分类检查 | 改走分类架插入写值 |

---

**一句话总结**:检查永远在升级,但只要你看懂源码(后台逻辑),就能找到下一招。这就是进阶篇教你的核心能力。
