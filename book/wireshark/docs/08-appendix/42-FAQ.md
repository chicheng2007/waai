# 附录 C：常见问题 FAQ

## C.1 安装与启动

**Q：启动 Wireshark 提示权限不足，怎么办？**

Linux 下需要配置普通用户抓包权限（见第四章），把用户加入 wireshark 组并给 dumpcap 设置 capability。macOS 需要允许 ChmodBPF。Windows 需要正确安装 Npcap。

**Q：看不到网卡列表？**

Windows 下多半是 Npcap 没装好，重新安装 Npcap。Linux 下检查网卡是否正常 (`ip link`)。也可能是虚拟机网络配置问题。

**Q：抓不到 loopback（本机访问本机）流量？**

Windows 需要 Npcap 的 loopback 支持，选择 `Npcap Loopback Adapter` 接口。Linux 选择 `lo` 接口。

## C.2 抓包问题

**Q：为什么抓不到其他两台主机之间的通信？**

在交换机网络中，混杂模式只能抓到广播/组播和发给本机的流量。单播流量不会经过你的端口。需要使用端口镜像（SPAN）、网络分流器（TAP），或在目标主机上抓包。

**Q：抓包时提示大量丢包（Dropped）？**

说明抓包主机性能不足。参考第三十九章优化：关闭实时显示、关闭名称解析、增大缓冲区、用 SSD、使用 dumpcap 命令行。

**Q：为什么有些包显示 "Previous segment not captured"？**

可能是抓包丢包（本机性能不足），也可能是网络中真的丢了包。先排查抓包质量（看丢包计数）。

## C.3 显示与过滤

**Q：`ip.addr != 10.0.0.1` 为什么不生效？**

这是最常见的陷阱。`ip.addr` 同时匹配源和目的，只要其中一个不等于就满足，所以几乎匹配所有包。正确写法：`!ip.addr == 10.0.0.1` 或 `ip.src != 10.0.0.1 && ip.dst != 10.0.0.1`。

**Q：过滤器输入框是红色的？**

表达式有语法错误。检查字段名拼写、引号、括号。绿色表示正确，黄色表示有警告。

**Q：如何过滤某个 TCP 连接的完整数据？**

右键该连接的任意包 → `Follow → TCP Stream`，或用 `tcp.stream eq N`（N 是流编号，在包的详情中可看到）。

**Q：如何快速生成过滤器？**

在协议详情窗格中右键字段 → `Prepare as Filter`，Wireshark 自动生成表达式。

## C.4 协议解析

**Q：为什么 HTTP 显示为 TCP？**

可能是非标准端口（如 8080 上的 HTTP），Wireshark 没识别出来。右键 → `Decode As` → 选择 HTTP，强制解析。

**Q：为什么看到的是加密数据？**

HTTPS/TLS 流量默认是加密的。要看到明文需要解密密钥（见第二十九章）。

**Q：校验和显示错误（Bad checksum）是网络问题吗？**

通常不是。这是网卡硬件卸载校验和计算导致的假象。在首选项中关闭校验和验证，或禁用网卡卸载功能。

**Q：为什么有些协议解析不完整？**

可能是协议版本较新、Wireshark 版本较旧，或数据包不完整/畸形。升级 Wireshark 到最新版本。

## C.5 分析技巧

**Q：如何从一个大文件中快速找到关注的流量？**

1. 用显示过滤器缩小范围。
2. 用 Conversations/Endpoints 找关键会话。
3. 用 `Ctrl + F` 搜索关键字。
4. 用 tshark 提取到新文件再分析。

**Q：如何导出 HTTP 传输的文件？**

`File → Export Objects → HTTP`，选择文件保存。

**Q：如何看一个请求对应的响应？**

Wireshark 在协议树中标注 `[Response in frame: N]`，点击可跳转。或用 Follow Stream 查看整个会话。

**Q：时间列显示的是什么时间？**

默认是相对于第一个包的秒数。右键列标题 → `Time Display Format` 可切换为绝对时间或与上一包的间隔。

## C.6 性能与最佳实践

**Q：Wireshark 打开大文件很卡？**

分割文件（editcap）、先过滤保存再说、增加内存、关闭不需要的协议解析、用 tshark 命令行处理。

**Q：抓包时应该开名称解析吗？**

一般不建议开 IP 反向解析（会触发 DNS 查询干扰抓包，且离线分析时有延迟）。MAC 和端口解析通常无害。

**Q：可以用 root 运行 Wireshark 吗？**

不建议。Wireshark 解析不可信数据，以 root 运行有安全风险。正确做法是给 dumpcap 授权，主程序以普通用户运行。

## C.7 获取更多帮助

- 官方文档：<https://www.wireshark.org/docs/>
- 问答社区：<https://ask.wireshark.org>
- 邮件列表：wireshark-users
- 本教程的 GitHub Issues

提问时请提供：Wireshark 版本、操作系统、抓包场景、具体现象、相关过滤表达式。
