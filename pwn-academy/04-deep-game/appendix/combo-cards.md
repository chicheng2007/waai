# 附录 B · 现代连招条件对照表

> 遇到一道现代堆题,不知道用哪招?查这张"连招卡",按条件对号入座。

## 🃏 连招卡

### 卡1:House of Apple(2.35 主流)

| 项目 | 内容 |
| --- | --- |
| 适用版本 | 2.34+(hook 被移除) |
| 前置条件 | 任意地址写(常靠 largebin attack)+ 控制 fake FILE + 泄露 libc/堆址 |
| 触发器 | exit() / puts / IO 刷新 |
| 核心 | vtable 指向合法表偏移 + 构造 wide_data |
| 游戏比喻 | 假存档卡 + 官方技能表的特殊按钮 |

### 卡2:FSOP

| 项目 | 内容 |
| --- | --- |
| 适用 | 各种版本(老版更简单) |
| 前置 | 控制 `_IO_list_all` 或某 FILE |
| 触发器 | exit 刷新 FILE 链表 |
| 核心 | 伪造 FILE 满足刷新条件 |
| 游戏比喻 | 改退出动画清单 |

### 卡3:largebin attack

| 项目 | 内容 |
| --- | --- |
| 适用 | 2.30+ |
| 前置 | 能控制 large chunk 的 nextsize 指针 + 泄露堆址(编码) |
| 效果 | 往任意地址写一个堆地址 |
| 游戏比喻 | 分类架插入时改"大小邻居"纸条 |

### 卡4:tcache poisoning

| 项目 | 内容 |
| --- | --- |
| 适用 | 2.26+ |
| 前置 | UAF 能改 tcache chunk 的 next + (2.32+)泄露堆址 |
| 效果 | malloc 返回任意地址 → 任意写 |
| 游戏比喻 | 改快速筐里的"下一个空格"纸条 |

### 卡5:unsorted bin attack

| 项目 | 内容 |
| --- | --- |
| 适用 | 2.30 之前 |
| 前置 | 能改 unsorted chunk 的 bk |
| 效果 | 往任意地址写一个大数(bin头) |
| 游戏比喻 | 改中转站的"上家"纸条 |

### 卡6:stdout 泄露

| 项目 | 内容 |
| --- | --- |
| 适用 | 各种版本 |
| 前置 | 能部分改写 stdout 的 write_base |
| 效果 | 打印任意内存 → 泄露 libc |
| 游戏比喻 | 挪"从哪念"指针让游戏报答案 |

## 🎯 选招决策树

```
题目是什么版本?
  │
  ├─ 2.34+(无hook)
  │    └─ 需要拿shell → House of Apple
  │         └─ 前置需要任意写 → largebin attack
  │
  ├─ 2.31(有hook,safe-linking无)
  │    └─ tcache poisoning → 改 __free_hook → system
  │
  ├─ 2.32/2.33(有safe-linking)
  │    └─ 先泄露堆址 → 编码 next → tcache poisoning
  │
  └─ 2.30之前
       └─ unsorted bin attack / 经典 fastbin attack
```

## 🔧 关键前置能力(按优先级)

1. **泄露 libc**:unsorted bin fd / stdout 泄露 / 格式化字符串
2. **泄露堆址**:UAF 读 chunk 指针 / safe-linking 反推
3. **任意写**:tcache poisoning / largebin attack
4. **控制流劫持**:House of Apple / hook / FSOP

---

**记忆口诀**:先泄露(libc+堆址)→ 再造任意写 → 最后劫持控制流。三步走,哪关都不慌。
