# 第 14 章 angr 符号执行入门

> 当程序逻辑复杂到手工逆向很费劲时，可以用符号执行让机器帮你求解「什么样的输入能到达目标」。

---

## 14.1 什么是符号执行

传统调试：你给一个具体输入，程序走一条确定的路径。

符号执行：你给一个**符号变量**（比如 `x` 代表任意输入），程序探索所有可能的路径，收集路径约束，然后用约束求解器求出满足条件的具体输入。

```text
程序：
  read(input)
  if input[0] == 'a':
      if input[1] == 'b':
          print("success")
      else:
          print("fail")
  else:
      print("wrong")

符号执行会自动求出：input = "ab"
```

---

## 14.2 安装 angr

```bash
sudo pip3 install angr
```

> 💡 **提示**：angr 依赖较多（z3、cle、pyvex 等），建议用 Python 3.8+ 环境。

---

## 14.3 基本用法

```python
import angr
import claripy

# 加载二进制
proj = angr.Project('./crackme', auto_load_libs=False)

# 创建初始状态
state = proj.factory.entry_state()

# 创建符号输入（比如 16 字节）
sym_input = claripy.BVS('input', 16 * 8)

# 把符号输入放到 stdin
state = proj.factory.entry_state(stdin=angr.SimFileStream(name='stdin', content=sym_input, has_end=False))

# 创建仿真管理器
simgr = proj.factory.simgr(state)

# 探索：找到 success 分支，避开 fail 分支
simgr.explore(
    find=lambda s: b'success' in s.posix.dumps(1),
    avoid=lambda s: b'fail' in s.posix.dumps(1)
)

# 输出解
if simgr.found:
    solution = simgr.found[0].posix.dumps(0)
    print(f'Input: {solution}')
```

---

## 14.4 关键概念

### 14.4.1 状态（State）

`state` 代表程序在某一时刻的快照，包括寄存器、内存、约束条件等。

### 14.4.2 仿真管理器（SimulationManager）

管理多条并行探索的路径：

```python
simgr.active        # 当前活跃路径
simgr.deadended     # 死亡路径
simgr.found         # 找到目标
simgr.avoid         # 避开的路径
```

### 14.4.3 约束求解（Claripy）

```python
x = claripy.BVS('x', 32)        # 32 位符号变量
s = claripy.Solver()
s.add(x > 10)
s.add(x < 20)
s.eval(x, 1)                    # 求一个解，比如 15
```

---

## 14.5 在 CTF 中的应用

### 14.5.1 求解密码/校验逻辑

对于「输入密码 → 一堆检查 → 正确则输出 flag」的题目，angr 能自动求出密码。

### 14.5.2 到达特定地址

```python
target_addr = 0x401234
simgr.explore(find=target_addr)
```

### 14.5.3 约束输入格式

```python
# 限制输入只含可打印字符
for byte in sym_input.chop(8):
    state.solver.add(byte >= 0x20)
    state.solver.add(byte <= 0x7e)
```

---

## 14.6 常见坑

1. **路径爆炸**：复杂程序会产生指数级路径。用 `avoid` 剪枝、设置超时、限制路径数。
2. **符号化内存**：angr 处理间接跳转、复杂数据结构时可能卡住。
3. **库函数**：用 `auto_load_libs=False` 避免加载整个 libc（但可以 hook 关键函数）。

```python
# hook 函数
@angr.SimStatePlugin
class ...
proj.hook_symbol('strlen', angr.SIM_PROCEDURES['libc']['strlen']())
```

---

## 14.7 小结

这一章我们入门了 angr：

- 符号执行自动求解输入
- Project、State、SimulationManager 核心概念
- explore(find, avoid) 探索路径
- 应用于密码求解、路径到达

angr 是强大的辅助工具，但不是万能的——复杂程序仍需手工逆向配合。

下一章我们学习 AFL 模糊测试。

---

**下一章**：[AFL 模糊测试实战](./ch15-AFL实战.md)
