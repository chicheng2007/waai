# 学习资源链接速查表

> 配套《网安零基础学AI完整路线.md》使用 · 整理日期：2026-11-23
> 下面链接均已联网核实过；个别以官网为准，失效请到官网搜索。

---

## 一、软考网络工程师

| 资源 | 链接 |
|---|---|
| 中国计算机技术职业资格网（报名/官方通知） | https://www.ruankao.org.cn |

> 你现有的 Summer 的课 + 官方《网络工程师教程》已够用，这里只补报名官网。

---

## 二、AI 课程与数学视频

| 资源 | 链接 | 说明 |
|---|---|---|
| 吴恩达《Machine Learning Specialization》（Coursera） | https://www.coursera.org/specializations/machine-learning-introduction | 官方新版，可申请助学金免费学 |
| DeepLearning.AI 官网 | https://www.deeplearning.ai | 吴恩达团队，含免费短课 |
| 李沐《动手学深度学习》中文官网 | https://zh.d2l.ai | 免费在线书 + 每节可运行的 Jupyter |
| 李沐 PyTorch 版课程 PDF | https://courses.d2l.ai/zh-v2/ | 课程讲义 |
| 3Blue1Brown B站官方账号 | https://space.bilibili.com/88461692 | 数学动画，中文官方 |
| 《线性代数的本质》合集 | https://www.bilibili.com/video/BV1ys411472E/ | 必看，建立直觉 |
| 《微积分的本质》系列 | https://space.bilibili.com/88461692 | 在账号内搜索"微积分的本质" |
| 《深度学习之神经网络》系列 | https://space.bilibili.com/88461692 | 账号内"深度学习"合集 |

---

## 三、AI 编程环境 / 编码 Agent（现在就用）

| 工具 | 链接 | 用途 |
|---|---|---|
| Cursor（编码 Agent，强烈推荐） | https://cursor.com | 写代码 / 改报错 / 写脚本 |
| Claude Code | https://www.anthropic.com/claude-code | 命令行编码 Agent |
| GitHub Copilot | https://github.com/features/copilot | 代码补全 |
| 通义灵码 | https://tongyi.aliyun.com/lingma/ | 国产代码助手 |
| Jupyter | https://jupyter.org | 写 Python 实验 |
| scikit-learn | https://scikit-learn.org | 传统机器学习库 |
| PyTorch | https://pytorch.org | 深度学习框架 |
| Hugging Face | https://huggingface.co | 模型 / 数据集社区 |

---

## 四、数据集

| 数据集 | 链接 | 用途 |
|---|---|---|
| KDD Cup 1999（网络入侵检测） | https://www.kaggle.com/datasets/galaxyh/kdd-cup-1999-data | 阶段 1 入门项目 |
| CIC-IDS2017（入侵检测） | https://www.kaggle.com/datasets/cicdataset/cicids2017 | 阶段 2 流量检测项目 |
| Malware Detection（恶意代码） | https://www.kaggle.com/search?q=malware+detection | 阶段 2 恶意代码分类 |
| Kaggle 首页 | https://www.kaggle.com | 找数据集 / 比赛 |
| 阿里云天池 | https://tianchi.aliyun.com | 国内数据科学比赛 |
| DataFountain | https://www.datafountain.cn | 国内数据竞赛平台 |

---

## 五、网安：CTF 平台与靶场（用 CTF 驱动攻防）

| 平台 | 链接 | 说明 |
|---|---|---|
| 攻防世界 XCTF（新手首选） | https://adworld.xctf.org.cn | 国内头部，分难度，免费 |
| CTFHub（技能树刷题） | https://www.ctfhub.com | 中文，按知识点分模块 |
| NSSCTF（比赛复现 / Writeup） | https://www.nssctf.cn | 适合看题解 |
| BUUCTF（真题聚合） | https://buuoj.cn | 题目多，免费 |
| CTFtime（国际赛事日历） | https://ctftime.org | 找比赛 |
| TryHackMe（零基础友好，引导式） | https://tryhackme.com | 游戏化入门，强烈推荐 |
| Hack The Box（进阶靶机） | https://www.hackthebox.com | 有基础后再上 |
| PortSwigger Web Security Academy | https://portswigger.net/web-security | Web 安全权威免费实验室，配 Burp |
| DVWA（本地靶场 GitHub） | https://github.com/digininja/DVWA | 本地搭 Web 漏洞练习 |
| Pikachu（中文靶场） | https://github.com/zhuifengshaonianhanlu/pikachu | 国内初学友好 |
| Vulhub（CVE 复现） | https://github.com/vulhub/vulhub | Docker 漏洞环境 |

---

## 六、网安工具下载

| 工具 | 链接 | 说明 |
|---|---|---|
| Burp Suite 下载 | https://portswigger.net/burp/downloads | 选 Community 免费版 |
| Wireshark 下载 | https://www.wireshark.org/download.html | 抓包，免费 |
| Kali Linux 下载 | https://www.kali.org/get-kali/ | 预装大量渗透工具 |
| Nmap 下载 | https://nmap.org/download.html | 端口 / 服务扫描 |

---

## 七、电子取证工具

| 工具 | 链接 | 说明 |
|---|---|---|
| **火眼证据分析**（你的主线） | 学校实验室环境内使用 | 行业软件，一般无公开下载；需要请联系学校老师 / 官方渠道 |
| FTK Imager（做镜像） | https://www.exterro.com/ftk-imager | 免费，只学做镜像即可 |
| Autopsy（开源分析） | https://www.autopsy.com/download/ | 无火眼环境时的免费替代 |
| The Sleuth Kit | https://github.com/sleuthkit/sleuthkit | Autopsy 底层命令行工具 |
| Volatility 3（内存取证） | https://github.com/volatilityfoundation/volatility3 | 大三再碰 |
| Volatility 3 文档 | https://volatility3.readthedocs.io | 官方使用文档 |

---

## 八、Agent 开发（大三以后）

| 资源 | 链接 | 说明 |
|---|---|---|
| LangChain 文档 | https://python.langchain.com | 最主流的 Agent 框架 |
| CrewAI | https://www.crewai.com | 多智能体框架 |
| Hugging Face Agents 课程 | https://huggingface.co/learn/agents-course | 免费 Agent 教程 |
| DeepLearning.AI 短课（LangChain / crewAI） | https://www.deeplearning.ai | 搜 "LangChain" / "crewAI" 短课 |

---

## 九、社区 / 资讯 / 论文

| 资源 | 链接 | 说明 |
|---|---|---|
| FreeBuf | https://www.freebuf.com | 国内安全资讯，有 AI+安全专栏 |
| 安全客 | https://www.anquanke.com | 国内安全资讯 |
| 看雪学院 | https://kanxue.com | 侧重二进制 / 逆向 |
| Papers with Code | https://paperswithcode.com | 找论文 + 开源代码 |
| GitHub（AI+安全项目） | https://github.com/search?q=AI+for+cybersecurity | 搜开源项目 |

---

## 十、书籍购买

在线书/电子书优先用上面免费资源；纸质书在 **京东 / 当当 / 天猫** 直接搜书名即可：
- 现在买：《网络工程师教程》第5版（雷震甲）、《Python编程：从入门到实践》
- 软考后买：《机器学习实战》、《利用Python进行数据分析》
- 大二下买：《动手学深度学习》（李沐）、《白帽子讲Web安全》（吴翰清）

> 《动手学深度学习》官网 https://zh.d2l.ai 有免费完整在线版和 Jupyter 代码，可以先在线读，再决定是否买纸质书。

---

*提示：以上均为合法学习资源。CTF、靶场、SRC 挖洞请在授权范围内进行，切勿对未授权的真实系统测试——这是网安专业学生的红线。*
