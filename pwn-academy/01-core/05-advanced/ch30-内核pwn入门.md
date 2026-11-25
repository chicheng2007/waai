# 第 30 章 内核 PWN 入门

> 前面所有内容都发生在用户态。这一章我们把视角抬到内核态，看看当漏洞出现在内核模块中时，利用的思路有什么不同。

---

## 30.1 用户态与内核态

现代 CPU 有特权级（Ring 0~3），Linux 使用其中两级：

- **用户态（Ring 3）**：普通应用程序运行的地方，受限访问硬件和内核内存
- **内核态（Ring 0）**：内核和驱动运行的地方，拥有最高权限

用户程序通过 **系统调用（syscall）** 陷入内核态。系统调用发生时，CPU 会切换到内核态，执行内核里的处理函数。

```
用户态 (Ring 3)                    内核态 (Ring 0)
    │                                   │
    │  syscall(...)                     │
    ├──────────────────────────────────▶│  查系统调用表 → 找到处理函数
    │                                   │  执行内核代码（可访问一切）
    │  ◀────────────────────────────────┤  返回结果
    │                                   │
```

**内核 PWN 的目标**：利用内核模块或驱动中的漏洞，在内核态执行代码，从而提权到 root（拿到 Ring 0 权限）。

---

## 30.2 内核 PWN 题的一般形式

CTF 中的内核题通常给你：

1. **一个带漏洞的内核模块**（`.ko` 文件）
2. **一个启动脚本**（用 qemu 启动一个精简的 Linux 系统）
3. **bzImage**（内核镜像）和根文件系统

选手需要：逆向后漏洞模块，编写 exp 在虚拟机里运行，最终提权读取 flag（通常放在 root 才能读的地方）。

### 运行环境

```bash
# 典型的 qemu 启动命令
qemu-system-x86_64 \
    -m 512M \
    -kernel bzImage \
    -initrd rootfs.cpio.gz \
    -append "console=ttyS0 nokaslr" \
    -nographic \
    -s    # 开启 gdb 调试端口 1234
```

其中 `nokaslr` 关闭内核地址随机化（KASLR），方便调试。

---

## 30.3 内核态的关键概念

### 30.3.1 系统调用与 ioctl

内核模块通常通过以下方式暴露接口给用户态：

- **系统调用**：注册一个新的系统调用号
- **设备文件**：创建 `/dev/xxx`，用户通过 `open/read/write/ioctl` 与之交互
- **ioctl**：最常用的接口，通过命令码传递不同的操作

```c
// 用户态调用
ioctl(fd, CMD_ADD, &data);

// 内核态处理
long my_ioctl(struct file *file, unsigned int cmd, unsigned long arg) {
    switch (cmd) {
        case CMD_ADD: ...
    }
}
```

### 30.3.2 内核中的内存分配

内核有自己的内存分配器：

- **kmalloc / kfree**：类似用户态的 malloc/free，用于小对象
- **vmalloc**：大块内存
- **kmem_cache**：slab/slub 分配器，用于固定大小对象

内核堆利用和用户态堆利用思路类似（UAF、double free 等都存在），但实现细节不同。

### 30.3.3 关键数据结构

- **`cred` 结构体**：记录进程的权限（uid、gid、capabilities）。提权的经典目标是修改当前进程的 cred，把 uid 改成 0（root）。
- **`task_struct`**：进程描述符
- **`tty_struct`**：终端设备结构，常用于堆利用
- **`seq_operations`**：包含函数指针，可作为利用目标

---

## 30.4 提权的常用手法

### 30.4.1 commit_creds(prepare_kernel_cred(0))

这是内核提权的「标准公式」：

```c
// 在内核态执行
void *cred = prepare_kernel_cred(NULL);  // 创建一个 root  cred
commit_creds(cred);                      // 应用到当前进程
```

执行后，当前进程变成 root。

### 30.4.2 ret2usr（已过时）

早期内核没有 SMEP/SMAP 保护时，可以直接让内核执行用户态的代码：

```text
栈溢出 → 返回地址指向用户态的提权函数 → 在内核态执行 prepare_kernel_cred
```

### 30.4.3 绕过 SMEP/SMAP

现代内核有 SMEP（禁止内核执行用户态代码）和 SMAP（禁止内核访问用户态数据）。绕过方法：

- **ROP**：在内核代码里找 gadget，构造 ROP 链调用 `commit_creds`
- **kernel ROP + swapgs + iretq**：ROP 完成后从内核态返回用户态，执行 shell

---

## 30.5 一个简单的内核漏洞示例

假设有一个内核模块，其 ioctl 处理函数有栈溢出：

```c
// 漏洞模块（内核态）
static long vuln_ioctl(struct file *file, unsigned int cmd, unsigned long arg) {
    char buf[64];
    copy_from_user(buf, (void *)arg, 200);   // 栈溢出！
    return 0;
}
```

利用步骤：

1. 用户态程序打开 `/dev/vuln` 设备
2. 通过 ioctl 传入超长数据，溢出内核栈
3. 覆盖返回地址，构造 ROP 链调用 `commit_creds(prepare_kernel_cred(0))`
4. ROP 链最后执行 `swapgs; iretq` 返回用户态
5. 用户态程序现在以 root 运行，读取 flag

```c
// 用户态 exp（简化）
int main() {
    int fd = open("/dev/vuln", O_RDONLY);
    
    // 构造 payload（含内核 ROP 链）
    char payload[200];
    // ... 填充 ROP 链 ...
    
    ioctl(fd, CMD_TRIGGER, payload);
    
    // 提权后读取 flag
    system("cat /flag");
}
```

---

## 30.6 内核 PWN 的学习建议

内核 PWN 是 PWN 的进阶领域，门槛较高。建议按以下顺序学习：

1. **Linux 内核基础**：理解系统调用、进程管理、内存管理
2. **内核模块开发**：会写简单的 `.ko` 模块，理解 ioctl
3. **内核调试**：用 qemu + gdb 调试内核
4. **内核利用技术**：UAF、堆溢出、cred 提权
5. **绕过缓解机制**：SMEP、SMAP、KASLR、CFG 等

> 💡 **提示**：内核 PWN 需要学习大量新知识（内核数据结构、slab 分配器等）。本教程只是入门介绍，建议阅读专门的资料（如 《Linux Kernel Exploitation》）深入学习。

---

## 30.7 小结

这一章我们简要介绍了内核 PWN：

- **内核态 vs 用户态**：Ring 0 vs Ring 3，通过 syscall 切换
- **内核 PWN 的形式**：漏洞模块 + qemu 环境 + 提权读 flag
- **内核接口**：系统调用、设备文件、ioctl
- **内核内存**：kmalloc、vmalloc、kmem_cache
- **提权目标**：修改 cred 结构体，调用 `commit_creds(prepare_kernel_cred(0))`
- **缓解机制**：SMEP、SMAP、KASLR 需要绕过

第五篇 · 进阶之路至此完结。接下来是最后一篇——工具与实战。

---

**下一章**：[pwntools 精通](../06-tools-practice/README.md) → [第 31 章](../06-tools-practice/ch31-pwntools.md)
