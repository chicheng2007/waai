# 第 27 章 加密基础与 Web 安全

## 本章目标

- 理解哈希、对称加密、非对称加密
- 用 Python 实现常见加密操作
- 理解常见 Web 漏洞（SQL 注入、XSS、CSRF）的原理和防御
- 写一个弱口令检测工具

> **伦理声明**：所有安全测试仅在授权环境进行。Web 漏洞的"攻击"示例仅用于理解原理和编写防御代码，请在你自己搭建的靶场（如 DVWA）练习。

密码学是安全的基石，Web 安全是安全服务的主战场。这一章补齐这两块基本功。

---

## 27.1 哈希（Hash）

### 27.1.1 什么是哈希

哈希是把任意长度的数据映射成固定长度"指纹"的函数：

- **确定性**：同样输入永远得到同样输出
- **单向性**：无法从哈希值反推原文
- **抗碰撞**：不同输入很难得到相同哈希

```python
import hashlib

data = "hello".encode("utf-8")
print(hashlib.md5(data).hexdigest())     # 5d41402abc4b2a76b9719d911017c592
print(hashlib.sha256(data).hexdigest())  # 2cf24dba5fb0a30e...（64位）
```

### 27.1.2 哈希的安全应用

**1. 密码存储**（绝不能明文存密码！）

```python
import hashlib
import os

def hash_password(password, salt=None):
    """加盐哈希：salt 是随机值，防止彩虹表攻击"""
    if salt is None:
        salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt + hashed

def verify_password(password, stored):
    salt = stored[:16]
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt + hashed == stored

stored = hash_password("mypassword123")
print(verify_password("mypassword123", stored))   # True
print(verify_password("wrong", stored))           # False
```

> **注意**：MD5、SHA1 已被证明不安全（可碰撞），密码存储要用 **bcrypt** 或 **PBKDF2**（上面的例子），加盐+多次迭代。

**2. 文件完整性校验**

```python
def file_hash(filepath, algo="sha256"):
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

# hash = file_hash("suspicious.exe")
# print(hash)  # 与威胁情报库里的哈希比对，判断是否为恶意文件
```

---

## 27.2 对称加密与非对称加密

### 27.2.1 对称加密（同一把钥匙）

加密和解密用同一个密钥。代表算法：AES。

```python
# pip install cryptography
from cryptography.fernet import Fernet

# 生成密钥
key = Fernet.generate_key()
cipher = Fernet(key)

# 加密
message = "这是一条机密信息".encode()
encrypted = cipher.encrypt(message)
print("密文:", encrypted)

# 解密
decrypted = cipher.decrypt(encrypted)
print("明文:", decrypted.decode())
```

**特点**：速度快，适合加密大量数据。问题：密钥传输困难。

### 27.2.2 非对称加密（公钥+私钥）

- 公钥：公开，用来加密
- 私钥：保密，用来解密

代表算法：RSA。用于 HTTPS、数字签名、密钥交换。

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

# 生成密钥对
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 公钥加密
message = b"secret message"
encrypted = public_key.encrypt(
    message,
    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
)

# 私钥解密
decrypted = private_key.decrypt(
    encrypted,
    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
)
print(decrypted.decode())   # secret message
```

### 27.2.3 HTTPS 的工作原理

HTTPS = HTTP + TLS，结合了对称和非对称加密：

1. 服务器发送公钥（证书）给客户端
2. 客户端验证证书真伪
3. 客户端用公钥加密一个"会话密钥"发给服务器
4. 服务器用私钥解密得到会话密钥
5. 之后双方用会话密钥对称加密通信（快）

这就是非对称（传密钥）+ 对称（传数据）的组合。

---

## 27.3 Web 安全基础

### 27.3.1 SQL 注入

**原理**：用户输入被拼进 SQL 语句，改变语义。

```python
# 危险代码（拼接字符串）
def unsafe_login(username, password):
    sql = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    # 如果 username = "admin' OR '1'='1"，SQL 变成：
    # SELECT * FROM users WHERE name='admin' OR '1'='1' AND pass='...'
    # 恒真，绕过登录！
    return sql

print(unsafe_login("admin' OR '1'='1", "anything"))
```

**防御：参数化查询**

```python
def safe_login(cursor, username, password):
    sql = "SELECT * FROM users WHERE name=? AND pass=?"
    cursor.execute(sql, (username, password))   # 参数和数据分离，无法注入
```

### 27.3.2 XSS（跨站脚本）

**原理**：用户输入被当作 HTML 执行。

```python
# 危险：直接把用户输入显示到页面
# 如果用户输入 <script>alert('xss')</script>，就会执行恶意脚本

# 防御：输出编码
import html
user_input = "<script>alert('xss')</script>"
safe_output = html.escape(user_input)
print(safe_output)   # &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;
```

### 27.3.3 CSRF（跨站请求伪造）

**原理**：诱导用户在已登录状态下执行恶意操作。

**防御**：CSRF Token（每次请求带一个随机令牌）、SameSite Cookie。

### 27.3.4 弱口令检测工具

```python
# 弱口令检测（对自己的系统做安全检查）
COMMON_PASSWORDS = ["123456", "password", "admin", "111111", "12345678", "qwerty"]

def check_password_strength(password):
    """检查密码强度，返回问题列表"""
    issues = []
    if len(password) < 8:
        issues.append("长度不足8位")
    if password in COMMON_PASSWORDS:
        issues.append("使用了常见弱口令")
    if password.isdigit():
        issues.append("全是数字")
    if password.isalpha():
        issues.append("全是字母")
    return issues

# 测试
for pwd in ["123456", "abc123", "Str0ng!Pass"]:
    issues = check_password_strength(pwd)
    print(f"{pwd}: {'安全' if not issues else issues}")
```

---

## 27.4 本章总结

| 知识点 | 核心内容 |
|--------|---------|
| 哈希 | 单向、定长、抗碰撞；MD5/SHA256；密码加盐哈希（PBKDF2/bcrypt） |
| 对称加密 | AES，同一密钥，速度快 |
| 非对称加密 | RSA，公钥加密私钥解密；HTTPS 结合两者 |
| SQL 注入 | 参数化查询防御 |
| XSS | 输出编码（html.escape）防御 |
| CSRF | CSRF Token 防御 |
| 弱口令检测 | 长度、常见密码、字符多样性 |

---

## 本章练习

1. 实现文件哈希校验工具。
2. 用 Fernet 加密/解密一段文本。
3. 写出 SQL 注入的原理说明，并给出参数化查询的防御代码。
4. 完善弱口令检测工具，加入更多规则。
5. 思考：为什么密码不能明文存储？加盐的作用是什么？

---

**下一章预告**：我们将学习日志分析与安全脚本编写——把前面学的 Python 技能用在真实的安全运维场景中。
