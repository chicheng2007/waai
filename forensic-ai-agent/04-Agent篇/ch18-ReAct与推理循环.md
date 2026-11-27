# ch18 ReAct 与推理循环

> **本章目标**：理解 ReAct（Reasoning + Acting）范式——让 Agent 显式地"边思考边行动"。学会写 ReAct 提示词，让模型的推理过程可见、可控、可调试。

**导航**：[上一章：函数调用与工具使用](ch17-函数调用与工具使用.md) · [总目录](../README.md) · [下一章：记忆规划与多步任务](ch19-记忆规划与多步任务.md)

---

## 18.1 什么是 ReAct

ReAct = Reasoning（推理）+ Acting（行动）。核心思想：

> 让模型在每一步行动之前，先**显式写出自己的思考过程**，然后再行动。行动之后观察结果，再思考，再行动，循环往复。

为什么要显式写出思考？三个好处：

1. **提高质量**：模型"想清楚再说"，决策更合理；
2. **可调试**：你能看到它每一步在想什么，出问题好定位；
3. **可控制**：可以在思考环节插入人的审核。

一个 ReAct 循环长这样：

```
Thought（思考）：我需要先看看日志文件有哪些
Action（行动）：list_files(directory="logs/")
Observation（观察）：[starsea_firewall.log, auth.log]

Thought：日志里应该找异常，先用 grep 找外部 IP
Action：grep_log(file="starsea_firewall.log", pattern="203.0.113")
Observation：（返回匹配行）

Thought：找到外部 IP 了，用取证模型分析一下
Action：analyze_log_line(log_line="...")
Observation：结论：端口扫描...

Thought：信息够了，可以总结
Answer（最终答案）：...
```

---

## 18.2 ReAct 提示词模板

不用框架，用提示词就能实现 ReAct。模板：

```python
REACT_PROMPT = """你是一个取证分析 Agent。用以下格式工作：

Thought: 思考下一步该做什么
Action: 调用工具，格式为 工具名(参数)
Observation: [工具会返回这里]
... （重复 Thought/Action/Observation）

当你认为任务完成时，输出：
Answer: 最终答案

可用工具：
- list_files(directory): 列出目录文件
- grep_log(file, pattern): 搜索日志
- analyze_log_line(log_line): 分析单条日志
- ip_lookup(ip): 查询 IP 归属

开始！

任务：{task}
"""

def react_agent(task, max_steps=10):
    prompt = REACT_PROMPT.format(task=task)
    history = ""
    for step in range(max_steps):
        full = prompt + history
        resp = client.chat.completions.create(
            model="local-model",
            messages=[{"role": "user", "content": full}],
            temperature=0.1, max_tokens=500
        )
        output = resp.choices[0].message.content
        print(output)  # 打印出来，观察推理过程

        if "Answer:" in output:
            return output.split("Answer:")[1].strip()

        # 解析 Action，执行工具
        if "Action:" in output:
            action = output.split("Action:")[1].split("\n")[0].strip()
            result = parse_and_execute(action)
            history += f"\n{output}\nObservation: {result}\n"
        else:
            break
    return "未完成任务"
```

这个原生实现虽然简陋，但能让你**透彻理解 ReAct 的原理**。理解了原理，再用框架就得心应手。

---

## 18.3 Thought 的质量决定一切

ReAct 的效果，很大程度取决于 Thought（思考）的质量。好的思考：

- **具体**：不说"我要分析日志"，而说"我要先找出所有外部 IP，因为内部通信通常是正常的"；
- **有依据**：基于前面的 Observation 做决策；
- **有目标**：明确这一步要达成什么。

差的思考：

- 空泛："让我想想"；
- 脱离实际：忽略工具返回的结果；
- 循环："我还是再查一次吧"。

**提升思考质量的方法**：

1. 在 system 提示里给思考范例（few-shot）；
2. 要求思考必须引用 Observation 中的具体信息；
3. 用更强的模型做推理。

---

## 18.4 ReAct  vs  纯函数调用

ch17 的函数调用和 ReAct 有什么区别？

| 对比 | 纯函数调用 | ReAct |
|---|---|---|
| 思考过程 | 隐式（看不到） | 显式（Thought 可见） |
| 可控性 | 一般 | 高（可审查思考） |
| token 消耗 | 少 | 多（要生成思考文本） |
| 复杂任务 | 够用 | 更强 |
| 调试 | 难 | 易 |

**选择建议**：

- 简单任务（1-2 步）：纯函数调用够了；
- 复杂任务（多步推理）：用 ReAct；
- 调试阶段：用 ReAct（看得见思考）；
- 生产阶段：可以用函数调用省 token。

---

## 18.5 让思考可见的价值（取证场景）

取证场景特别需要"思考可见"，因为：

1. **可审计**：取证要求记录每一步（ch02 的"记录"环节）。ReAct 的 Thought 天然就是操作记录；
2. **可复核**：审计人员能看到 Agent 为什么做出某个判断；
3. **符合规范**：取证结论要能解释"怎么得出的"，ReAct 提供了完整的推理链。

**这正是 ReAct 比纯函数调用更适合取证的原因**。它不只是技术选择，更是合规要求。

> 提示：ReAct 的 Thought 记录了推理过程，但要注意——最后写报告时，这不等于"证据"（ch02 红线四）。推理链是辅助记录，结论仍需人工确认。

---

## 18.6 ReAct 的常见问题

### 问题一：陷入循环

模型反复执行同样的_action_。解决：

- 记录已经执行过的 action，检测到重复就提示"你已经做过这一步了"；
- 设置 max_steps；
- 在提示里明确"不要重复执行相同的工具"。

### 问题二：思考与行动不一致

模型说要查 IP，实际调用了 grep。解决：

- 用结构化输出（JSON）强制格式；
- 解析时校验 Thought 和 Action 的一致性。

### 问题三：上下文超限

多轮后历史太长，超出上下文。解决：

- 用 summarizer 压缩历史（把早前的步骤总结成一段）；
- 只保留最近的几轮 + 关键发现。

这与 CTF-Dojo 的 EnIGMA+ 用 summarizer 的思路一致。

---

## 18.7 动手任务

1. **写 ReAct 提示词**：按 18.2 的模板，为取证场景写一个完整的 ReAct 提示词。
2. **原生实现**：用 18.2 的代码实现一个最小 ReAct Agent。
3. **跑一个任务**：让它完成"找出日志里的可疑 IP 并总结"。打印每一步的 Thought/Action/Observation。
4. **观察循环**：故意给一个难任务，看它会不会陷入循环。加 max_steps 和重复检测解决。
5. **加记录**：把每轮的 Thought/Action/Observation 写进日志文件，模拟取证的"记录"环节。

---

## 18.8 小结

- ReAct = 推理 + 行动，让模型显式写出思考再行动；
- 好处：决策更优、可调试、可控制；
- 循环：Thought → Action → Observation → Thought... → Answer；
- 用提示词就能实现（18.2 模板），原生实现助你理解原理；
- Thought 质量决定效果：具体、有依据、有目标；
- **取证特别需要 ReAct**：思考可见 = 可审计、可复核、符合规范；
- 注意循环、不一致、上下文超限三个问题。

ReAct 让 Agent 会"思考"，但复杂任务还需要"记忆"和"规划"。下一章讲这两者。

**导航**：[上一章：函数调用与工具使用](ch17-函数调用与工具使用.md) · [总目录](../README.md) · [下一章：记忆规划与多步任务](ch19-记忆规划与多步任务.md)
