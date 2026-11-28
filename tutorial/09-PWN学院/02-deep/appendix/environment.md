# 附录 D：进阶环境配置

## glibc 多版本环境

### glibc-all-in-one

```bash
git clone https://github.com/matrix1001/glibc-all-in-one
cd glibc-all-in-one
python3 update_list
./download 2.31    # 下载 2.31
./download 2.35    # 下载 2.35
```

下载后的 libc 和 loader 在 `libs/` 目录。

### 用指定 libc 运行程序

```bash
# 方法 1：直接指定 loader
./libc-2.31.so/ld-2.31.so --library-path ./libc-2.31.so ./vuln

# 方法 2：用 patchelf 修改二进制
patchelf --set-interpreter ./ld-2.31.so --set-rpath ./libc-2.31.so ./vuln
./vuln

# 方法 3：pwntools
p = process([loader, '--library-path', libdir, binary])
```

### pwninit（自动配置）

```bash
# 自动为题目二进制配置正确的 libc 和 loader
pwninit --bin ./vuln --libc ./libc.so.6 --ld ./ld.so
```

## Docker 多版本环境

```bash
docker run -it --rm ubuntu:20.04 bash
docker run -it --rm ubuntu:22.04 bash
```

## 内核 PWN 环境

```bash
# 安装 qemu
sudo apt install qemu-system-x86_64

# 启动内核（带 gdb 端口）
qemu-system-x86_64 -m 512M -kernel bzImage -initrd rootfs.cpio.gz \
    -append "console=ttyS0 nokaslr" -nographic -s
```

## 必备工具清单

```bash
sudo pip3 install pwntools angr ropgadget
sudo gem install one_gadget seccomp-tools
sudo apt install gdb gcc qemu-system-x86_64
git clone https://github.com/pwndbg/pwndbg && cd pwndbg && ./setup.sh
git clone https://github.com/AFLplusplus/AFLplusplus && cd AFLplusplus && make && sudo make install
```

---

**提示**：进阶实验中，环境版本不匹配是最常见的「玄学问题」来源。做题前先确认 glibc 版本。
