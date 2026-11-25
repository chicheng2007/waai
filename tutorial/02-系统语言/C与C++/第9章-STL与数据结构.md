# 第 9 章 STL 标准库与数据结构

## 本章目标

- 掌握常用 STL 容器：vector、string、map、set、unordered_map
- 掌握迭代器和常用算法
- 理解容器的内存管理和安全特性
- 用 STL 实现安全数据处理

STL（Standard Template Library）是 C++ 的"神器"。它提供了经过高度优化、经过充分测试的数据结构和算法，让你不用重复造轮子，而且比手写的更安全。

---

## 9.1 vector：动态数组

### 9.1.1 基本用法

```cpp
#include <vector>
#include <iostream>

int main() {
    std::vector<int> ports = {22, 80, 443, 3389};
    
    ports.push_back(8080);       // 添加
    ports.pop_back();            // 删除最后一个
    std::cout << ports[0] << std::endl;   // 22
    std::cout << ports.size() << std::endl;  // 4
    
    // 遍历
    for (int p : ports) {
        std::cout << p << " ";
    }
    return 0;
}
```

### 9.1.2 vector 的安全性

```cpp
std::vector<int> v(5);
// v[10] = 100;   // 越界！operator[] 不检查
v.at(10) = 100;   // 抛出异常 std::out_of_range（安全！）
```

> `at()` 会做边界检查，`operator[]` 不检查。安全要求高的场景用 `at()`。

### 9.1.3 内存管理

vector 会自动扩容（通常是 2 倍）。理解这一点对性能很重要：

```cpp
std::vector<int> v;
v.reserve(1000);   // 预留空间，避免多次扩容（性能优化）
for (int i = 0; i < 1000; i++) v.push_back(i);
```

---

## 9.2 string：安全字符串

```cpp
#include <string>

std::string s = "hello";
s += " world";              // 拼接
s.find("world");            // 查找，返回位置或 npos
s.substr(0, 5);             // 子串 "hello"
s.length();                 // 长度
s.empty();                  // 是否为空

// 和 C 字符串互转
const char *c = s.c_str();
std::string s2(c);
```

> **安全性**：`std::string` 自动管理内存，不会像 `strcpy` 那样溢出。现代 C++ 强烈推荐用它代替字符数组。

---

## 9.3 map 与 unordered_map：字典

### 9.3.1 map（有序，红黑树）

```cpp
#include <map>
#include <string>

std::map<std::string, int> port_map;
port_map["HTTP"] = 80;
port_map["HTTPS"] = 443;
port_map["SSH"] = 22;

std::cout << port_map["HTTP"] << std::endl;  // 80

// 遍历（按 key 排序）
for (const auto &pair : port_map) {
    std::cout << pair.first << ": " << pair.second << std::endl;
}
```

### 9.3.2 unordered_map（无序，哈希表，更快）

```cpp
#include <unordered_map>

std::unordered_map<std::string, int> ip_fails;
ip_fails["192.168.1.1"] = 5;
ip_fails["10.0.0.1"] = 12;

// 查找
auto it = ip_fails.find("10.0.0.1");
if (it != ip_fails.end()) {
    std::cout << "失败次数: " << it->second << std::endl;
}
```

> **性能**：unordered_map 查找是 O(1)，map 是 O(log n)。大量数据用 unordered_map 更快。但注意哈希碰撞攻击（攻击者构造大量碰撞 key 让哈希表退化成 O(n)）——这也是一种 DoS 攻击手法。

---

## 9.4 set 与 unordered_set：集合

```cpp
#include <set>
#include <unordered_set>

std::unordered_set<std::string> blacklist = {"10.0.0.1", "192.168.1.100"};

// 判断是否存在（O(1)）
if (blacklist.count("10.0.0.1")) {
    std::cout << "黑名单 IP!" << std::endl;
}

// set 自动去重且有序
std::set<int> ports = {80, 22, 443, 22};   // {22, 80, 443}
```

---

## 9.5 算法与迭代器

```cpp
#include <algorithm>
#include <vector>

std::vector<int> ports = {22, 80, 443, 3389, 8080};

// 排序
std::sort(ports.begin(), ports.end());

// 查找
auto it = std::find(ports.begin(), ports.end(), 443);
if (it != ports.end()) std::cout << "找到 443\n";

// 计数
int cnt = std::count_if(ports.begin(), ports.end(), 
                        [](int p) { return p < 1024; });

// 过滤（C++20 ranges 更优雅）
```

### 9.5.1 Lambda 表达式

```cpp
// [](参数) -> 返回类型 { 函数体 }
auto is_dangerous = [](int port) {
    return port == 23 || port == 445 || port == 3389;
};

std::cout << is_dangerous(3389) << std::endl;   // 1 (true)
```

Lambda 在算法中作为谓词非常常用，是现代 C++ 的标配。

---

## 9.6 实战：安全日志分析器

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <algorithm>

struct LogEntry {
    std::string ip;
    std::string event;
};

int main() {
    std::vector<LogEntry> logs = {
        {"192.168.1.1", "LOGIN_FAIL"},
        {"10.0.0.5", "LOGIN_FAIL"},
        {"192.168.1.1", "LOGIN_FAIL"},
        {"8.8.8.8", "LOGIN_OK"},
        {"10.0.0.5", "LOGIN_FAIL"},
    };
    
    // 统计每个 IP 的失败次数
    std::unordered_map<std::string, int> fails;
    for (const auto &log : logs) {
        if (log.event == "LOGIN_FAIL") {
            fails[log.ip]++;
        }
    }
    
    // 找出可疑 IP（失败 >= 2）
    std::cout << "=== 可疑 IP ===\n";
    for (const auto &[ip, count] : fails) {   // 结构化绑定（C++17）
        if (count >= 2) {
            std::cout << "[警告] " << ip << " 失败 " << count << " 次\n";
        }
    }
    
    return 0;
}
```

> 注意结构化绑定 `auto &[ip, count]` 是 C++17 特性，需要 `-std=c++17`。

---

## 9.7 本章总结

| 容器/工具 | 特点 | 用途 |
|----------|------|------|
| vector | 动态数组，连续内存 | 列表数据 |
| string | 安全字符串 | 文本处理 |
| map | 有序字典（红黑树） | 需要排序的映射 |
| unordered_map | 哈希表字典，O(1) | 快速查找 |
| set/unordered_set | 集合，去重 | 黑名单、去重 |
| 算法 | sort/find/count_if | 数据处理 |
| lambda | 匿名函数 | 算法谓词 |

---

## 本章练习

1. 用 vector 存储端口列表，排序后去重。
2. 用 unordered_map 统计日志中每个 IP 的出现次数。
3. 用 set 实现 IP 黑名单查询。
4. 用 lambda + count_if 统计知名端口数量。
5. 思考：map 和 unordered_map 各适合什么场景？哈希碰撞攻击是什么？

---

**下一章预告**：我们将进入 C/C++ 网络安全的"重头戏"——内存安全漏洞：栈溢出、堆溢出、UAF。这一章把前面的内存知识串起来，讲清楚漏洞的原理和利用思路。
