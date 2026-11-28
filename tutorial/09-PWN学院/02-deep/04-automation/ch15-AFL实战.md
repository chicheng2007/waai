# 第 15 章 AFL 模糊测试实战

> 与其手工找漏洞，不如让 fuzzer 用海量的随机输入帮你「撞」出来。这一章学习 AFL 的基本使用。

---

## 15.1 AFL 的工作原理

AFL（American Fuzzy Lop）是一个基于覆盖引导的模糊测试工具：

```text
1. 准备一批种子输入 (seeds)
2. 对种子进行变异（翻转比特、插入、删除等）
3. 用插桩的程序运行每个变异输入
4. 记录代码覆盖率
5. 保留能触发新覆盖的输入，继续变异
6. 崩溃的输入保存到 crashes/ 目录
```

**覆盖率引导**是 AFL 的核心：它知道哪些输入「有意思」（触发了新的代码路径），从而高效地探索程序。

---

## 15.2 安装 AFL

```bash
# AFL++（推荐，AFL 的现代分支）
git clone https://github.com/AFLplusplus/AFLplusplus
cd AFLplusplus
make && sudo make install

# 验证
afl-fuzz --version
```

---

## 15.3 编译插桩程序

AFL 需要程序在编译时插桩，以便记录覆盖率：

```bash
# 使用 afl-clang-fast（推荐）
afl-clang-fast -g -O1 -o target target.c

# 或用 afl-gcc
afl-gcc -g -O1 -o target target.c
```

对于没有源码的程序，可以用 AFL 的 QEMU 模式（`afl-qemu-trace`）进行二进制插桩。

---

## 15.4 准备种子输入

```bash
mkdir seeds
echo "hello" > seeds/seed1
echo "test" > seeds/seed2
```

种子要尽量覆盖程序的不同功能路径。

---

## 15.5 运行 fuzzing

```bash
afl-fuzz -i seeds -o findings -m none -- ./target @@
```

其中：

- `-i seeds`：种子目录
- `-o findings`：输出目录
- `-m none`：不限制内存
- `@@`：输入文件占位符（程序从这里读输入）

运行后会看到 AFL 的经典 TUI 界面，显示覆盖率、执行速度、崩溃数等。

---

## 15.6 分析崩溃

```bash
ls findings/crashes/
# 每个文件都是一个导致崩溃的输入

# 用 gdb 复现
gdb ./target
run < findings/crashes/id:000000,...
```

分析崩溃原因：

```gdb
bt                          # 崩溃时的调用栈
info registers              # 寄存器
x/20gx $rsp                 # 栈
```

判断是否可利用（栈溢出？堆溢出？空指针？）。

---

## 15.7 实战：挖出一个栈溢出

```c
// target.c
#include <stdio.h>
#include <string.h>

int process(char *input) {
    char buf[64];
    if (input[0] == 'A') {
        strcpy(buf, input);   // 栈溢出！
        printf("Processing: %s\n", buf);
    }
    return 0;
}

int main() {
    char input[256];
    fgets(input, sizeof(input), stdin);
    process(input);
    return 0;
}
```

fuzzing 步骤：

```bash
afl-clang-fast -g -O1 -o target target.c
mkdir seeds && echo "A" > seeds/seed
afl-fuzz -i seeds -o findings -m none -- ./target
```

AFL 会很快发现以 'A' 开头的长输入导致崩溃。

---

## 15.8 常见坑

1. **程序不退出**：fuzzing 的程序必须能快速处理输入并退出，否则速度极慢。
2. **校验和/加密**：如果程序有校验和，fuzzer 很难通过。可以用 AFL 的自定义变异或先 patches 掉校验。
3. **种子质量**：好的种子能大幅提升效率。
4. **超时**：设置合理的超时时间，避免卡在死循环。

---

## 15.9 小结

这一章我们学习了 AFL：

- 覆盖率引导的模糊测试原理
- 插桩编译、准备种子、运行 fuzzing
- 分析崩溃、判断可利用性

AFL 是发现未知漏洞的利器，但在 CTF 中更多用于「辅助」——帮你快速定位崩溃点，然后手工分析。

下一章我们讲利用脚本工程化。

---

**下一章**：[利用脚本工程化](./ch16-脚本工程化.md)
