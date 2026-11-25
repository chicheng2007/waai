# 第 31 章 实战：Linux 安全加固脚本

## 本章目标

读完这一章，你将能够：

- 把第 8、17–21 章的安全知识整合成一个完整的加固脚本
- 设计模块化的加固脚本架构
- 实现可回滚、可审计的加固操作
- 编写加固基线检查与报告
- 在实验环境完整演练加固流程

> ⚠️ **合规与谨慎声明**：本章所有操作**必须先在实验虚拟机中测试**。加固会修改系统配置，生产环境务必逐项验证、做好备份、评估业务影响后再应用。

---

## 31.1 项目目标与设计

### 31.1.1 需求

编写一个安全加固脚本，实现：

1. **基线检查**：检查当前系统的安全配置状态
2. **自动加固**：应用推荐的安全配置（可选择性执行）
3. **生成报告**：输出加固前后的对比和评分
4. **支持回滚**：备份原始配置，可恢复

### 31.1.2 架构设计

```
hardening-tool/
├── bin/
│   ├── main.sh              # 主入口
│   ├── modules/
│   │   ├── 01_account.sh    # 账户安全
│   │   ├── 02_ssh.sh        # SSH 加固
│   │   ├── 03_network.sh    # 网络内核参数
│   │   ├── 04_permission.sh # 文件权限
│   │   ├── 05_service.sh    # 服务最小化
│   │   └── 06_firewall.sh   # 防火墙
│   └── lib/
│       ├── common.sh        # 公共函数（日志、备份、检查）
│       └── report.sh        # 报告生成
├── backup/                  # 配置备份
├── reports/                 # 生成的报告
└── README.md
```

模块化设计的好处：每个模块独立，可单独运行、单独测试、按需启用。

---

## 31.2 公共库：common.sh

```bash
#!/bin/bash
# 公共函数库

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# 备份文件（带时间戳）
BACKUP_DIR="$(cd "$(dirname "$0")/../../backup" && pwd)"
backup_file() {
    local file=$1
    [ -f "$file" ] || { log_warn "文件不存在: $file"; return 1; }
    mkdir -p "$BACKUP_DIR"
    cp -a "$file" "$BACKUP_DIR/$(basename $file).$(date +%s).bak"
    log_info "已备份: $file"
}

# 检查并修改配置行
set_config() {
    local file=$1 key=$2 value=$3
    backup_file "$file"
    if grep -qE "^#?${key}" "$file"; then
        sed -i -E "s|^#?${key}.*|${key} ${value}|" "$file"
    else
        echo "${key} ${value}" >> "$file"
    fi
    log_info "设置 $file: $key = $value"
}

# 检查结果计数（用于报告）
CHECKS_TOTAL=0
CHECKS_PASSED=0
check_pass() { CHECKS_TOTAL=$((CHECKS_TOTAL+1)); CHECKS_PASSED=$((CHECKS_PASSED+1)); log_info "通过: $*"; }
check_fail() { CHECKS_TOTAL=$((CHECKS_TOTAL+1)); log_warn "未通过: $*"; }
```

这个库提供了：彩色日志、配置备份（每次修改前自动备份）、配置行修改、检查计数。这体现了第 16 章的模块化与最佳实践。

---

## 31.3 模块示例：账户安全

```bash
#!/bin/bash
# modules/01_account.sh - 账户安全加固
source "$(dirname "$0")/../lib/common.sh"

log_info "=== 账户安全检查与加固 ==="

# 1. 检查空密码账户
EMPTY=$(awk -F: '($2=="") {print $1}' /etc/shadow)
if [ -n "$EMPTY" ]; then
    log_error "发现空密码账户: $EMPTY"
    check_fail "空密码账户检查"
else
    check_pass "无空密码账户"
fi

# 2. 检查 UID=0 的账户
ROOT_USERS=$(awk -F: '$3==0 {print $1}' /etc/passwd)
if [ "$ROOT_USERS" = "root" ]; then
    check_pass "只有 root 拥有 UID 0"
else
    log_error "发现异常 UID=0 账户: $ROOT_USERS"
    check_fail "UID=0 账户检查"
fi

# 3. 加固密码策略
set_config /etc/login.defs PASS_MAX_DAYS 90
set_config /etc/login.defs PASS_MIN_LEN 12
set_config /etc/login.defs PASS_WARN_AGE 7
check_pass "密码策略已加固"

# 4. 锁定不必要的系统账户
for acct in games lp mail news uucp; do
    if passwd -S "$acct" 2>/dev/null | grep -q " P "; then
        log_warn "锁定未使用账户: $acct"
        passwd -l "$acct" 2>/dev/null
    fi
done
check_pass "系统账户检查完成"
```

---

## 31.4 模块示例：SSH 加固

```bash
#!/bin/bash
# modules/02_ssh.sh - SSH 加固（谨慎！）
source "$(dirname "$0")/../lib/common.sh"

log_info "=== SSH 安全加固 ==="
SSHD_CONFIG=/etc/ssh/sshd_config

# 警告：确保已配置密钥登录并验证！
log_warn "执行前请确认：1) 密钥登录已配置并验证 2) 保留一个 SSH 会话"

set_config "$SSHD_CONFIG" "PermitRootLogin" "no"
set_config "$SSHD_CONFIG" "PasswordAuthentication" "no"
set_config "$SSHD_CONFIG" "PermitEmptyPasswords" "no"
set_config "$SSHD_CONFIG" "MaxAuthTries" "3"
set_config "$SSHD_CONFIG" "LoginGraceTime" "30"
set_config "$SSHD_CONFIG" "X11Forwarding" "no"

# 检查语法
if sshd -t 2>/dev/null; then
    log_info "SSH 配置语法正确"
    read -p "是否重启 sshd 使配置生效？[y/N] " ans
    if [ "$ans" = "y" ]; then
        systemctl restart sshd
        log_info "sshd 已重启"
    else
        log_warn "配置未生效，请手动重启并验证密钥登录后再重启"
    fi
else
    log_error "SSH 配置语法错误，未重启！请修复"
fi
check_pass "SSH 配置检查完成"
```

> **关键设计**：SSH 加固模块**不自动重启**——因为改 SSH 配置风险最高，一旦出错会锁死。它检查语法后询问用户，把决定权交给人。这是"谨慎加固"的体现。

---

## 31.5 主入口：main.sh

```bash
#!/bin/bash
# 主入口
set -euo pipefail
source "$(dirname "$0")/lib/common.sh"

BASE="$(cd "$(dirname "$0")/.." && pwd)"
REPORT="$BASE/reports/hardening_$(date +%F_%H%M).txt"

echo "==================================="
echo "  Linux 安全加固工具 v1.0"
echo "  $(date)"
echo "==================================="

# 交互选择模式
echo "请选择模式："
echo "  1) 仅检查（不修改）"
echo "  2) 检查并加固"
read -p "选择 [1/2]: " mode

# 运行各模块
for module in "$BASE"/bin/modules/*.sh; do
    log_info "运行模块: $(basename $module)"
    bash "$module" 2>&1 | tee -a "$REPORT"
done

# 生成报告摘要
{
    echo ""
    echo "===== 加固报告摘要 ====="
    echo "时间: $(date)"
    echo "检查项总数: $CHECKS_TOTAL"
    echo "通过: $CHECKS_PASSED"
} >> "$REPORT"

log_info "报告已生成: $REPORT"
log_info "备份目录: $BACKUP_DIR"
```

---

## 31.6 回滚功能

回滚脚本 `rollback.sh`：

```bash
#!/bin/bash
# 回滚配置到备份版本
BACKUP_DIR="$(dirname "$0")/../backup"

echo "可用备份："
ls -1t "$BACKUP_DIR"/*.bak 2>/dev/null | head -20

read -p "输入要恢复的备份文件完整路径（或 q 退出）: " file
[ "$file" = "q" ] && exit 0

if [ -f "$file" ]; then
    # 从文件名推断原始路径（备份时用 原名.时间戳.bak）
    basename=$(basename "$file")
    original=$(echo "$basename" | sed -E 's/\.[0-9]+\.bak$//')
    read -p "恢复到 /etc/.../$original ? 请确认目标完整路径: " target
    cp -a "$file" "$target" && echo "已恢复: $target"
else
    echo "文件不存在"
fi
```

> **设计思想**：任何修改都可回滚。这是生产环境加固的必备能力——如果加固导致业务异常，能快速恢复。

---

## 31.7 实验演练流程

在实验虚拟机中完整演练：

```bash
# 1. 准备实验环境（快照！）
# 在虚拟机管理器里先拍一个快照

# 2. 下载/创建工具目录结构
mkdir -p hardening-tool/{bin/modules,bin/lib,backup,reports}

# 3. 依次创建本章的脚本文件，chmod +x

# 4. 先运行"仅检查"模式，看基线状态
bash bin/main.sh       # 选 1

# 5. 检查报告，了解系统现状
cat reports/hardening_*.txt

# 6. 运行"检查并加固"模式
bash bin/main.sh       # 选 2

# 7. 验证加固效果
sudo lynis audit system | grep "Hardening index"

# 8. 重启后验证服务是否正常（SSH 尤其重要！）

# 9. 如需回滚，用 rollback.sh
```

### 演练检查清单

- [ ] 已拍虚拟机快照
- [ ] 已备份关键配置
- [ ] SSH 密钥登录已配置并验证
- [ ] 保留一个 root/控制台会话
- [ ] 逐模块测试，不一次性全上
- [ ] 加固后重启验证服务
- [ ] 记录加固前后 Lynis 评分

---

## 31.8 本章总结

| 知识点 | 内容 |
|--------|------|
| 项目设计 | 模块化架构：主入口 + 公共库 + 各功能模块 |
| 公共库 | 彩色日志、配置备份、配置修改、检查计数 |
| 账户模块 | 空密码检查、UID=0 检查、密码策略、锁定无用账户 |
| SSH 模块 | 加固配置 + 语法检查 + 人工确认重启（谨慎） |
| 回滚 | 每次修改前备份，支持恢复 |
| 演练 | 快照 → 仅检查 → 加固 → 验证 → 重启测试 → 回滚 |

---

## 本章练习

1. 搭建 hardening-tool 目录结构，创建本章的所有脚本文件。
2. 运行"仅检查"模式，生成基线报告，分析系统的薄弱环节。
3. 逐个模块测试，观察每个模块的日志输出。
4. 加固后重启实验机，验证 SSH 等服务是否正常。
5. 故意改坏一个配置，用 rollback.sh 恢复，验证回滚功能。
6. 用 Lynis 对比加固前后的评分变化。
7. 扩展一个模块：防火墙检查模块（检查是否只开放了必要端口）。
8. 思考：为什么 SSH 加固模块"不自动重启"？这体现了什么安全原则？

---

**下一章预告**：我们将做第二个实战项目——日志分析入侵检测系统，把第 6、14、20 章的日志分析能力和第 15 章的定时任务整合，构建一个能自动发现攻击并告警的系统。
