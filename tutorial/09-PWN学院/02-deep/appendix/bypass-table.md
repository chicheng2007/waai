# 附录 B：绕过手法速查表

## 按检查机制查绕过

| 检查 | 引入版本 | 绕过手法 |
| --- | --- | --- |
| tcache key | 2.29 | malloc 出来再 free；修改 fd 构造假链表；UAF 清 key+next |
| safe-linking | 2.32 | 先泄露堆地址，用 `(pos>>12)^target` 编码 fd |
| unlink 双链表检查 | 2.29 | 构造自洽假链表；转向 tcache（单向） |
| fastbin 对齐检查 | 2.32 | 保证 fake chunk 地址 0x10 对齐 |
| top chunk size 检查 | 2.29 | 放弃 House of Force，转向其他技术 |
| 移除 hooks | 2.34 | IO_FILE 利用（House of Apple）、exit_funcs |
| vtable 检查 | 2.24 | _IO_str_jumps（2.27~2.31）；House of Apple（2.35） |

## 按目标查手法

| 目标 | 手法 |
| --- | --- |
| 泄露 libc | unsorted bin leak、stdout 泄露、GOT 打印 |
| 泄露堆地址 | tcache fd 解码、environ、stdout 泄露 |
| 泄露栈地址 | environ 泄露、栈上指针 |
| 任意地址写 | tcache poisoning、largebin attack、Fastbin Attack |
| getshell（2.31） | __free_hook、__malloc_hook |
| getshell（2.35） | House of Apple、FSOP |
| 沙箱绕过 | ORW、openat、mprotect |

## 版本选择速查

| glibc | Ubuntu | 主流终点 |
| --- | --- | --- |
| 2.23 | 16.04 | 任意 vtable、fastbin attack |
| 2.27 | 18.04 | tcache dup（无 key）、FSOP |
| 2.29 | 19.04 | tcache key 绕过、_IO_str_jumps |
| 2.31 | 20.04 | tcache poisoning + __free_hook |
| 2.34 | 22.04 | hooks 移除，IO_FILE 兴起 |
| 2.35 | 22.04 | House of Apple |
