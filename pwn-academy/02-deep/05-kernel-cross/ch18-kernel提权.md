# 第 18 章 kernel ROP 与提权实战

> 拿到内核态的控制流后，如何安全地提权并返回用户态？这一章讲 swapgs/iretq 和缓解机制的绕过。

---

## 18.1 提权公式

```c
commit_creds(prepare_kernel_cred(NULL));
```

- `prepare_kernel_cred(NULL)`：创建一个 root 权限的 cred 结构
- `commit_creds(cred)`：把当前进程的 cred 替换成它

执行后，当前进程变成 root。

---

## 18.2 kernel ROP

当能控制内核栈的返回地址时，构造 ROP 链：

```text
[ pop rdi; ret ][ 0 ][ prepare_kernel_cred ][ mov rdi, rax; ret ][ commit_creds ][ ... ]
```

但还有两个问题：

1. **如何从内核态返回用户态？** 需要 `swapgs` 和 `iretq`
2. **SMEP/SMAP 阻止执行用户态代码**

---

## 18.3 swapgs 与 iretq

从系统调用返回用户态时，内核执行：

```asm
swapgs          ; 切换 GS 段寄存器（内核 GS ↔ 用户 GS）
iretq           ; 从栈上弹出 rip, cs, rflags, rsp, ss 返回用户态
```

ROP 链的最后要布置：

```text
[ swapgs; ret ]
[ iretq; ret ]
[ user_rip ]      ; 返回用户态后执行的位置
[ user_cs ]
[ user_rflags ]
[ user_rsp ]
[ user_ss ]
```

这些用户态寄存器值需要在漏洞触发前保存：

```c
save_state();  // 保存 cs, rflags, rsp, ss 到全局变量
```

---

## 18.4 绕过 SMEP/SMAP

**SMEP**（Supervisor Mode Execution Prevention）：禁止内核执行用户态代码。
**SMAP**（Supervisor Mode Access Prevention）：禁止内核访问用户态数据。

绕过方法：

1. **纯内核 ROP**：所有 gadget 都在内核代码里，不执行用户态代码
2. **修改 CR4 寄存器**：关闭 SMEP/SMAP 位

```asm
; 关闭 SMEP（CR4 的 bit 20）
mov rax, cr4
and rax, 0xffffffffffefffff  ; 清除 bit 20
mov cr4, rax
```

需要找 `mov cr4, rax; ret` 这样的 gadget。

---

## 18.5 绕过 KASLR

KASLR 随机化内核地址。泄露方法：

- `/proc/kallsyms`（需要权限）
- 内核漏洞泄露
- 侧信道攻击

---

## 18.6 完整利用流程

```text
1. 保存用户态寄存器状态（save_state）
2. 触发漏洞，获得内核栈控制
3. kernel ROP：
   - 调用 commit_creds(prepare_kernel_cred(0))
   - swapgs; iretq 返回用户态
4. 用户态执行 system("/bin/sh") → root shell
```

---

## 18.7 小结

这一章我们学习了 kernel ROP 提权：

- 提权公式：commit_creds(prepare_kernel_cred(0))
- 返回用户态：swapgs + iretq
- 绕过 SMEP/SMAP：纯内核 ROP 或改 CR4
- 绕过 KASLR：泄露内核地址

第五篇的内核部分到此。接下来简单介绍 Windows PWN 和 ARM PWN。

---

**下一章**：[Windows PWN 入门](./ch19-WindowsPWN.md)
