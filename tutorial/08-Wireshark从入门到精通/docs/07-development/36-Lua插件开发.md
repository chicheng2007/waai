# 第三十六章 Lua 插件开发

Wireshark 支持用 Lua 脚本扩展功能。通过 Lua，你可以编写自定义协议解析器（Dissector）、监听器（Listener）、菜单项等。本章介绍 Lua 插件开发的基础，让你能让 Wireshark 理解私有协议或实现定制功能。

## 36.1 Lua 插件基础

### 36.1.1 启用 Lua

Wireshark 默认支持 Lua（除非编译时禁用）。把 `.lua` 文件放到插件目录即可自动加载：

- Windows：`%APPDATA%\Wireshark\plugins\`
- Linux/macOS：`~/.local/lib/wireshark/plugins/` 或 `~/.config/wireshark/plugins/`

也可以放到 Wireshark 安装目录的 `plugins/lua/` 下（全局插件）。

### 36.1.2 最小示例

```lua
-- hello.lua
print("Hello from Lua plugin!")

-- 创建一个菜单项
register_menu("My Tools/Hello", function()
    print("Hello clicked!")
end, MENU_TOOLS_UNSORTED)
```

重启 Wireshark 或 `Ctrl + Shift + L` 重新加载 Lua 插件。

### 36.1.3 常用 API 概览

| API | 用途 |
| --- | --- |
| `Proto` | 定义协议 |
| `ProtoField` | 定义协议字段 |
| `Dissector` | 解析器对象 |
| `ByteArray` | 字节数组操作 |
| `TreeItem` | 协议树节点 |
| `Listener` | 监听数据包 |
| `register_menu` | 注册菜单 |
| `Pref` | 首选项 |
| `Field` | 访问其他协议字段 |

## 36.2 编写自定义 Dissector

### 36.2.1 基本结构

```lua
-- 定义协议
local my_proto = Proto("myproto", "My Custom Protocol")

-- 定义字段
local f_magic = ProtoField.uint16("myproto.magic", "Magic", base.HEX)
local f_len   = ProtoField.uint16("myproto.len", "Length", base.DEC)
local f_cmd   = ProtoField.string("myproto.cmd", "Command")

my_proto.fields = {f_magic, f_len, f_cmd}

-- 解析器函数
function my_proto.dissector(buffer, pinfo, tree)
    pinfo.cols.protocol = "MYPROTO"

    local subtree = tree:add(my_proto, buffer(), "My Custom Protocol")

    -- 解析字段（假设格式：magic(2) + len(2) + cmd(变长)）
    if buffer:len() < 4 then return end

    local magic = buffer(0, 2):uint()
    local len = buffer(2, 2):uint()

    subtree:add(f_magic, buffer(0, 2))
    subtree:add(f_len, buffer(2, 2))

    if buffer:len() >= 4 + len then
        local cmd = buffer(4, len):string()
        subtree:add(f_cmd, buffer(4, len))
    end
end

-- 注册到 TCP 端口 9999
local tcp_table = DissectorTable.get("tcp.port")
tcp_table:add(9999, my_proto)
```

### 36.2.2 关键概念

- **Proto**：定义协议对象，参数是内部名称和显示名称。
- **ProtoField**：定义字段，类型包括 `uint8/16/32`、`string`、`ipv4`、`bytes` 等。第一个参数是显示过滤器字段名（如 `myproto.magic`），可以在过滤框中使用。
- **dissector 函数**：Wireshark 对每个包调用此函数，参数是 `buffer`（字节数据）、`pinfo`（包信息）、`tree`（协议树）。
- **DissectorTable**：把解析器注册到特定端口或协议。常用表：`tcp.port`、`udp.port`、`eth.type`、`ip.proto`。

### 36.2.3 ByteArray 操作

```lua
local bytes = buffer(0, 4):bytes()    -- 转 ByteArray
local val = bytes:get_index(0)        -- 取第 0 字节
bytes:set_index(0, 0xFF)              -- 设置字节
```

## 36.3 Listener（监听器）

Listener 用于统计或监听特定协议的数据包：

```lua
local listener = Listener.new("ip", "tcp")
local count = 0

function listener.packet(pinfo, tvb)
    count = count + 1
    print("Packet " .. count .. ": " .. tostring(pinfo.src) .. " -> " .. tostring(pinfo.dst))
end

function listener.reset()
    count = 0
end
```

`Listener.new("ip", "tcp")` 的第一个参数是 tap 类型（frame、ip、tcp 等），第二个是过滤器。

## 36.4 首选项与菜单

```lua
-- 定义首选项
local pref_port = Pref.uint("Server Port", 9999, "TCP port for the protocol")
my_proto.prefs.port = pref_port

-- 注册菜单
register_menu("My Tools/Show Stats", function()
    print("Total packets: " .. count)
end, MENU_TOOLS_UNSORTED)
```

## 36.5 调试技巧

- 用 `print()` 输出到 Wireshark 的 Lua 控制台（`Help → Lua → Console`... 实际上输出到终端/标准输出）。
- 在 Wireshark 图形界面，输出可在启动 Wireshark 的终端看到。
- 语法错误会在 `Help → About → Plugins` 或启动时提示。
- 用 `Ctrl + Shift + L`（或菜单）重新加载 Lua 插件，无需重启。

## 36.6 学习资源

- Wireshark 官方文档：[Lua Developer's Guide](https://www.wireshark.org/docs/wsdg_html_chunked/wsluarm_intro.html)
- Wireshark Wiki 的 Lua 页面：<https://wiki.wireshark.org/Lua>
- 自带的示例脚本：Wireshark 安装目录的 `plugins/lua/` 下。

## 36.7 小结

- Lua 插件放到插件目录自动加载，可定义 Dissector、Listener、菜单、首选项。
- 自定义 Dissector 的核心：Proto 定义协议、ProtoField 定义字段、dissector 函数解析字节、DissectorTable 注册端口。
- Listener 用于监听和统计特定流量。
- print() 调试，Ctrl+Shift+L 重新加载插件。

下一章，通过一个完整案例学习自定义协议解析。
