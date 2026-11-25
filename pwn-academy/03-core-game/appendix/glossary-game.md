# 附录 A · 游戏术语 ↔ PWN 黑话对照表

> 打游戏时忘了某个黑话?来这里查。左边是游戏里的说法,右边是真实术语。

## 🏙️ 世界与基础

| 游戏说法 | PWN 黑话 | 一句话 |
| --- | --- | --- |
| 内存城 | 虚拟内存空间 | 程序运行的地盘 |
| 小屋/房间 | 字节(byte) | 内存最小单位,8位 |
| 门牌号 | 地址(address) | 十六进制,如0x7fff |
| 城市管理员 | CPU | 执行指令 |
| 藏宝图坐标 | 指针(pointer) | 存地址的变量 |
| 按图取宝 | 解引用(*p) | 访问指针指向的值 |
| 问门牌号 | 取地址(&x) | 获取变量地址 |
| 底朝前放 | 小端序 | 低位字节在低地址 |
| 游戏控制台指令 | 汇编(assembly) | CPU听懂的语言 |
| 随身口袋 | 寄存器 | rax/rdi/rsp/rip等 |
| 进度条 | rip/指令指针 | 指向下一条指令 |

## 🍽️ 栈与利用

| 游戏说法 | PWN 黑话 | 一句话 |
| --- | --- | --- |
| 盘子柱 | 栈(stack) | 后进先出 |
| 盘子 | 栈帧(stack frame) | 一次函数调用 |
| 回城卷轴 | 返回地址 | ret跳过去的地方 |
| 底座 | rbp | 栈帧基址 |
| 柱顶手指 | rsp | 栈顶指针 |
| 堆太多菜 | 栈溢出 | 输入超过缓冲区 |
| 没设限的厨师 | gets/strcpy | 不检查长度的函数 |
| 要填多少 | 偏移(offset) | 到返回地址的字节数 |
| 跳隐藏关 | ret2text | 跳到程序自带代码 |
| 自带作弊器 | ret2shellcode | 自己写的机器码 |
| 借技能库 | ret2libc | 调用libc的system |
| 乐高积木 | ROP gadget | 以ret结尾的指令片段 |
| 拼积木 | ROP链 | 串起来的gadget |
| 警报器 | Canary | 栈保护令牌 |
| 原样奉还 | 泄露Canary填回 | 绕过栈保护 |
| 移到仓库 | 栈迁移 | 搬栈到可控区 |

## 🗺️ 地图与规则

| 游戏说法 | PWN 黑话 | 一句话 |
| --- | --- | --- |
| 地图蓝图 | ELF文件 | 程序文件格式 |
| 代码区 | .text | 只读可执行 |
| 数据区 | .data/.bss | 可读可写 |
| 传送门 | PLT | 调用外部函数的跳板 |
| 公告板 | GOT | 记录函数真实地址 |
| 难度旋钮 | 保护机制 | Canary/NX/PIE/RELRO |
| 禁跑区 | NX | 数据区不可执行 |
| 洗牌地图 | ASLR/PIE | 地址随机化 |
| 焊死的公告板 | Full RELRO | GOT只读 |

## 🔮 副本与堆

| 游戏说法 | PWN 黑话 | 一句话 |
| --- | --- | --- |
| 话痨NPC | printf | 格式化字符串漏洞 |
| 特殊指令 | %p/%s/%n | 泄露/读/写 |
| 透视 | 任意地址读 | %s |
| 修改器 | 任意地址写 | %n |
| 储物柜中心 | 堆(heap) | 动态内存区 |
| 租柜/退柜 | malloc/free | 分配/释放 |
| 柜子钥匙 | 指针 | malloc返回值 |
| 标签牌 | chunk header | prev_size/size |
| 回收站格子 | bin | tcache/fastbin等 |
| 快速回收筐 | tcache | 每类7个,LIFO |
| 退租留钥匙 | UAF | 释放后继续使用 |
| 退租两次 | Double Free | 同一chunk释放两次 |
| 投毒 | tcache poisoning | 改next返回任意地址 |
| 盖章 | tcache key | 防重复free |
| 地址打码 | safe-linking | next指针编码 |
| 摆柜子 | 堆风水 | 控制堆布局 |
| 存档系统 | IO_FILE | 含vtable的FILE结构 |
| 技能清单 | vtable | 函数指针表 |
| 禁魔模式 | seccomp | 禁止execve |
| 基础三连 | ORW | open/read/write读flag |
| 管理员模式 | 内核态 | ring 0 |
| 身份卡 | cred | uid=0是root |

---

## 🎮 手柄速查(pwntools)

| 想做的事 | 代码 |
| --- | --- |
| 启动本地 | `process('./vuln')` |
| 连接远程 | `remote('host', port)` |
| 发包 | `p.sendline(data)` |
| 收包 | `p.recvuntil(b':')` |
| 交互 | `p.interactive()` |
| 打包地址 | `p64(addr)` |
| 解包地址 | `u64(bytes)` |
| 生成shellcode | `asm(shellcraft.amd64.linux.sh())` |
| 找gadget | `ROP(elf).find_gadget(['pop rdi','ret'])` |
| 格式化利用 | `fmtstr_payload(6, {addr: val})` |

---

**记住:所有 PWN 技术,本质上都是"改内存 + 改rip"。** 比喻只是帮你理解,真正的原理就这么简单。
