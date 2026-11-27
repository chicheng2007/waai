# ch20 实战：Agent 骨架

> **本章目标**：把 Agent 篇四章的组件组装成一个完整、可运行的取证 Agent 骨架。这是原生代码实现的"最小可用 Agent"，不依赖复杂框架，让你透彻理解每个部件如何协作。后面三个项目都基于这个骨架。

**导航**：[上一章：记忆规划与多步任务](ch19-记忆规划与多步任务.md) · [总目录](../README.md) · [下一章：项目一-日志研判工具](../05-实战项目/ch21-项目一-日志研判工具.md)

---

## 20.1 骨架设计

我们要实现的 Agent 具备：

- **大脑**：本地 Qwen（或微调后的取证模型）；
- **工具**：grep、列文件、查IP、取证分析模型；
- **记忆**：结构化发现 + 摘要；
- **规划**：任务分解为步骤；
- **循环**：Plan-and-Execute + 每步 ReAct；
- **记录**：完整日志，可审计。

目录结构：

```
forensic-agent/
├── agent.py          # Agent 主类
├── tools.py          # 工具定义与执行
├── prompts.py        # 提示词模板
├── memory.py         # 记忆管理
└── main.py           # 入口
```

---

## 20.2 工具模块（tools.py）

```python
# tools.py
import subprocess
import os

# 工具定义（给模型看的）
TOOL_DEFS = [
    {"name": "list_files", "description": "列出指定目录下的文件",
     "params": {"directory": "目录路径"}},
    {"name": "grep_log", "description": "在日志中搜索关键词，返回匹配行",
     "params": {"file": "文件路径", "pattern": "搜索关键词"}},
    {"name": "ip_lookup", "description": "查询 IP 归属（模拟）",
     "params": {"ip": "IP地址"}},
    {"name": "analyze_log", "description": "用取证模型分析日志行",
     "params": {"log_line": "日志行"}},
]

# 工具执行（真正干活）
def execute(name, args):
    if name == "list_files":
        return "\n".join(os.listdir(args["directory"]))
    elif name == "grep_log":
        # 白名单检查：只允许读 .log 文件
        if not args["file"].endswith(".log"):
            return "错误：只能读取 .log 文件"
        r = subprocess.run(["grep", args["pattern"], args["file"]],
                          capture_output=True, text=True, timeout=10)
        return r.stdout[:2000] or "无匹配"
    elif name == "ip_lookup":
        # 模拟：真实场景接 API
        ip = args["ip"]
        return f"{ip}：文档测试地址段（保留IP）" if ip.startswith("203.0.113") else f"{ip}：内网地址"
    elif name == "analyze_log":
        return qa.analyze(args["log_line"])  # ch15 的取证模型
    return f"未知工具：{name}"
```

**安全**：工具执行有白名单（只能读 .log 文件），防止 Agent 乱读敏感文件。

---

## 20.3 记忆模块（memory.py）

```python
# memory.py
class Memory:
    def __init__(self):
        self.findings = {
            "suspicious_ips": [],
            "events": [],
            "conclusions": []
        }
        self.log = []  # 完整操作记录（审计用）

    def add_ip(self, ip):
        if ip not in self.findings["suspicious_ips"]:
            self.findings["suspicious_ips"].append(ip)

    def add_event(self, event):
        self.findings["events"].append(event)

    def add_conclusion(self, c):
        self.findings["conclusions"].append(c)

    def record(self, step, thought, action, observation):
        self.log.append({
            "step": step, "thought": thought,
            "action": action, "observation": observation
        })

    def summary(self):
        """给 Agent 看的简洁记忆"""
        return f"""当前发现：
- 可疑IP：{self.findings['suspicious_ips']}
- 事件数：{len(self.findings['events'])}
- 结论：{self.findings['conclusions']}"""
```

---

## 20.4 提示词（prompts.py）

```python
# prompts.py
PLAN_PROMPT = """你是取证任务规划器。把任务拆成有序步骤，每步说明用什么工具。
只输出步骤列表，不要解释。

任务：{task}

步骤："""

REACT_PROMPT = """你是取证 Agent。按格式工作：
Thought: 思考（结合当前发现）
Action: 工具名(参数JSON)
Observation: [工具结果]

可用工具：{tools}
当前发现：{memory}
任务：{task}

开始："""
```

---

## 20.5 Agent 主类（agent.py）

```python
# agent.py
from openai import OpenAI
import json, re
from tools import TOOL_DEFS, execute
from memory import Memory
from prompts import PLAN_PROMPT, REACT_PROMPT

class ForensicAgent:
    def __init__(self):
        self.client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
        self.memory = Memory()

    def llm(self, prompt, max_tokens=500):
        return self.client.chat.completions.create(
            model="local-model",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=max_tokens
        ).choices[0].message.content

    def plan(self, task):
        """任务分解"""
        return self.llm(PLAN_PROMPT.format(task=task), max_tokens=600)

    def react_step(self, task, step_num):
        """单步 ReAct"""
        tools_desc = "\n".join(
            f"- {t['name']}: {t['description']}" for t in TOOL_DEFS
        )
        prompt = REACT_PROMPT.format(
            tools=tools_desc, memory=self.memory.summary(), task=task
        )
        out = self.llm(prompt)

        # 解析 Thought 和 Action
        thought = re.search(r"Thought:(.*?)(?=Action:|$)", out, re.S)
        action = re.search(r"Action:(\w+)\((.*?)\)", out, re.S)
        thought = thought.group(1).strip() if thought else "..."
        if action:
            name, argstr = action.group(1), action.group(2)
            try:
                args = json.loads(argstr)
            except:
                args = {}
            obs = execute(name, args)
            # 更新记忆
            if "ip" in args:
                self.memory.add_ip(args["ip"])
            self.memory.record(step_num, thought, f"{name}({argstr})", obs)
            return obs
        return "无行动"

    def run(self, task, max_steps=10):
        print("=== 规划 ===")
        plan = self.plan(task)
        print(plan)

        print("\n=== 执行 ===")
        for i in range(max_steps):
            obs = self.react_step(task, i+1)
            print(f"[步骤{i+1}] 观察：{obs[:150]}")

        # 生成最终报告
        print("\n=== 汇总 ===")
        report = self.llm(f"""基于以下发现，生成取证分析报告，按结论/依据/建议组织：
{self.memory.summary()}
任务：{task}""", max_tokens=800)
        return report, self.memory.log
```

---

## 20.6 入口（main.py）

```python
# main.py
from agent import ForensicAgent
import json

agent = ForensicAgent()
task = "分析 starsea_firewall.log，找出可疑 IP 和异常事件"

report, log = agent.run(task, max_steps=8)

print("\n=== 最终报告 ===")
print(report)

# 保存审计记录
with open("audit_log.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print("\n审计记录已保存到 audit_log.json")
```

运行：

```bash
python main.py
```

你会看到 Agent 一步步规划、调用工具、更新发现，最后生成报告。**这就是一个完整的取证 Agent 骨架。**

---

## 20.7 这个骨架的不足

诚实地说，这个原生骨架比较简陋：

- 解析 Action 用正则，不够鲁棒；
- 规划结果没有真正被执行（只是打印）；
- 没有 RAG；
- 错误处理简单。

**但这正是它的价值**：它让你看清 Agent 的每个部件。理解了它，再用 LangChain / LangGraph 等框架，你就不会被框架"黑箱"住。ch21 会用 LangChain 做一个更完善的版本。

---

## 20.8 动手任务

1. **跑通骨架**：按 20.2-20.6 写代码，运行 `main.py`，看 Agent 完整跑一遍。
2. **改进解析**：把正则解析改成更鲁棒的方式（如让模型输出 JSON）。
3. **接上规划**：让 `run` 真正按 plan 的步骤执行，而不是盲目循环。
4. **加 RAG**：把 ch19 的 RAG 接进记忆模块。
5. **审计记录**：检查 `audit_log.json`，确认每一步都记录完整（可审计）。

---

## 20.9 小结

- 骨架组件：工具（tools）+ 记忆（memory）+ 提示词（prompts）+ 主类（agent）+ 入口（main）；
- 工具执行有白名单，保证安全；
- 记忆分"发现"和"操作日志"，后者用于审计；
- 原生实现虽然简陋，但让你看透 Agent 原理；
- 后面项目会用 LangChain 做更完善的版本。

Agent 篇完成。你现在理解了从模型到 Agent 的完整链条。接下来进入实战项目篇，做三个能写进简历的完整项目。

**导航**：[上一章：记忆规划与多步任务](ch19-记忆规划与多步任务.md) · [总目录](../README.md) · [下一章：项目一-日志研判工具](../05-实战项目/ch21-项目一-日志研判工具.md)
