# 第 8 章 Python C API：从底层理解扩展与嵌入

## 本章目标

读完这一章，你将能够：

- 理解 Python C API 是所有绑定工具的底层基础
- 用纯 C API 写一个 Python 扩展模块（理解 pybind11 背后的原理）
- 理解引用计数、借用引用/新引用这些核心概念
- 在 C/C++ 程序里**嵌入 Python 解释器**，让 C 程序执行 Python 代码
- 理解扩展模块初始化、方法表、参数解析的底层机制
- 知道什么时候该用底层 API、什么时候该用高级工具

---

## 8.1 Python C API 是什么

Python 解释器本身是用 C 写的（CPython）。它暴露了一套 C 接口，叫 **Python C API**，允许：

1. **写扩展模块**：用 C 写函数/类型，编译成 `.so`，Python 能 `import`
2. **嵌入 Python**：在 C/C++ 程序里启动 Python 解释器，执行 Python 代码

ctypes、cffi、Cython、pybind11 最终都构建了这套 API 之上。理解它，你就理解了所有工具的**共同地基**。

**为什么还要学底层 API？**

- 看懂绑定工具生成的 C 代码
- 做一些高级工具才能做的事（自定义类型、内存精细控制）
- 理解引用计数——这是 Python 内存管理的本质，也是很多 bug 的根源
- 嵌入 Python 到 C 程序（高级工具不太覆盖这个方向）

**代价**：API 繁琐，容易出错（引用计数错误会导致内存泄漏或崩溃）。日常开发优先用 pybind11/Cython。

---

## 8.2 环境准备：Python 头文件

写 C 扩展需要 Python 的开发头文件：

```bash
# Ubuntu/Debian
sudo apt install python3-dev

# 查询头文件路径和编译参数
python3-config --includes
# 输出：-I/usr/include/python3.11
python3-config --ldflags --embed  # 嵌入时需要
```

---

## 8.3 第一个 C 扩展模块

### 8.3.1 完整代码

创建 `spam.c`：

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

// 1. 模块函数：返回两个整数之和
static PyObject* spam_add(PyObject* self, PyObject* args) {
    int a, b;
    // 解析参数："ii" 表示两个 int
    if (!PyArg_ParseTuple(args, "ii", &a, &b)) {
        return NULL;  // 解析失败，已设置异常
    }
    // 用 PyLong_FromLong 创建 Python int 对象返回
    return PyLong_FromLong(a + b);
}

// 2. 另一个函数：返回一个字符串
static PyObject* spam_greet(PyObject* self, PyObject* args) {
    const char* name;
    if (!PyArg_ParseTuple(args, "s", &name)) {
        return NULL;
    }
    // 格式化创建 Python 字符串
    return PyUnicode_FromFormat("Hello, %s from C!", name);
}

// 3. 方法表：声明模块里有哪些函数
static PyMethodDef SpamMethods[] = {
    {"add",  spam_add,  METH_VARARGS, "两个整数相加"},
    {"greet", spam_greet, METH_VARARGS, "从C打招呼"},
    {NULL, NULL, 0, NULL}  // 哨兵，表示结束
};

// 4. 模块定义
static struct PyModuleDef spammodule = {
    PyModuleDef_HEAD_INIT,
    "spam",           // 模块名
    "Python C API 示例模块",  // 文档
    -1,               // 模块状态大小
    SpamMethods       // 方法表
};

// 5. 模块初始化函数（名字必须是 PyInit_模块名）
PyMODINIT_FUNC PyInit_spam(void) {
    return PyModule_Create(&spammodule);
}
```

### 8.3.2 编译

```python
# setup.py
from setuptools import setup, Extension

setup(
    name="spam",
    ext_modules=[
        Extension("spam", ["spam.c"], extra_compile_args=["-O2"])
    ],
)
```

```bash
python setup.py build_ext --inplace
```

### 8.3.3 使用

```python
import spam
print(spam.add(3, 5))       # 8
print(spam.greet("Alice"))  # Hello, Alice from C!
print(spam.__doc__)         # Python C API 示例模块
```

### 8.3.4 代码结构解析

对比 pybind11 的几行代码，这里繁琐很多，但结构清晰：

```
PyObject*  ← 所有 Python 对象在 C 里的表示
    ↓
模块函数（PyObject* 参数 + PyObject* 返回）
    ↓
方法表（PyMethodDef 数组）
    ↓
模块定义（PyModuleDef）
    ↓
初始化函数（PyInit_xxx）
```

**这就是 pybind11 在底层帮你生成的东西。** 理解了这个，再看 pybind11 就透明了。

---

## 8.4 核心概念：引用计数

### 8.4.1 PyObject 与引用计数

CPython 里每个对象都是 `PyObject*`，结构体里有 `ob_refcnt`（引用计数）。当计数归零，对象被释放。

C API 里有两种引用：

| 类型 | 含义 | 例子 |
|------|------|------|
| **新引用（new reference）** | 你拥有它，用完必须 `Py_DECREF` | `PyLong_FromLong`、`PyUnicode_FromFormat` |
| **借用引用（borrowed reference）** | 不拥有，不要 decref | `PyList_GetItem`、`PyDict_GetItem` |

**规则**：

- 函数返回新引用 → 你负责 `Py_DECREF`
- 函数返回借用引用 → 不要 decref（除非先 incref 变成自己的）

忘记 decref → **内存泄漏**；多 decref → **对象被提前释放，崩溃/UAF**。这是 C 扩展最经典的问题。

### 8.4.2 示例：正确处理引用

```c
static PyObject* spam_process(PyObject* self, PyObject* args) {
    PyObject* list;
    if (!PyArg_ParseTuple(args, "O", &list))  // "O" 得到借用引用
        return NULL;

    // 处理列表...
    Py_ssize_t n = PyList_Size(list);

    // 如果要保存引用，先 INCREF
    // PyObject* saved = list; Py_INCREF(saved);

    // 返回新引用（调用方负责释放）
    return PyLong_FromSsize_t(n);
}
```

### 8.4.3 为什么 pybind11 更安全

pybind11 用 RAII（如 `py::object`）自动管理引用计数，你几乎不用手动 decref。这就是高级工具的价值——**把容易出错的手动管理自动化**。

---

## 8.5 参数解析与类型检查

`PyArg_ParseTuple` 的格式字符串：

| 格式 | C 类型 | 说明 |
|------|--------|------|
| `i` | `int` | Python int → C int |
| `l` | `long` | → long |
| `d` | `double` | float → double |
| `s` | `const char*` | str → UTF-8 C 字符串 |
| `O` | `PyObject*` | 任意对象（借用引用） |
| `p` | `int` | 任意对象 → 布尔 |
| `|` | | 后面的参数可选 |
| `S` | `PyObject*` | 必须是 str（新引用） |

示例：带可选参数

```c
static PyObject* spam_power(PyObject* self, PyObject* args) {
    double base, exp = 2.0;  // exp 默认 2
    // "d|d"：第一个必需 double，第二个可选 double
    if (!PyArg_ParseTuple(args, "d|d", &base, &exp))
        return NULL;
    return PyFloat_FromDouble(pow(base, exp));
}
```

关键字参数需要 `PyArg_ParseTupleAndKeywords`，更复杂，这里不展开。

---

## 8.6 嵌入 Python：在 C 程序里执行 Python

这是 C API 的另一个方向：让 C/C++ 程序**启动 Python 解释器**，执行 Python 代码。这在「C 主程序需要脚本扩展能力」时非常有用（如游戏引擎、安全工具的插件系统）。

### 8.6.1 完整示例

创建 `embed.c`：

```c
#include <Python.h>

int main(int argc, char* argv[]) {
    // 1. 初始化 Python 解释器
    Py_Initialize();

    // 2. 执行一段 Python 代码
    PyRun_SimpleString(
        "print('Hello from embedded Python!')\n"
        "x = 10\n"
        "y = 20\n"
        "print(f'10 + 20 = {x+y}')\n"
    );

    // 3. （可选）调用 Python 模块里的函数
    PyRun_SimpleString(
        "import sys\n"
        "sys.path.insert(0, '.')\n"
    );

    // 4. 检查是否有异常
    if (PyErr_Occurred()) {
        PyErr_Print();
    }

    // 5. 关闭解释器
    Py_Finalize();
    return 0;
}
```

编译（注意 `--embed` 参数，链接 Python 库）：

```bash
gcc embed.c $(python3-config --includes) $(python3-config --ldflags --embed) -o embed
./embed
```

输出：

```
Hello from embedded Python!
10 + 20 = 30
```

### 8.6.2 嵌入的价值：给 C 程序加脚本能力

想象一个用 C 写的安全扫描器，核心扫描用 C（快），但检测规则用 Python 写（灵活）。嵌入 Python 后：

```c
// C 扫描到一个事件，调用 Python 规则判断
PyRun_SimpleString(
    "def check(event):\n"
    "    return 'malicious' in event.lower()\n"
);
// 然后在 C 里调用 check(...)
```

这样规则可以热更新，不用重编译 C 程序。**很多安全产品（WAF、EDR）就是这么设计的**：核心引擎 C/C++，规则引擎嵌入式 Python/Lua。

### 8.6.3 嵌入的注意事项

- **线程/GIL**：嵌入时要小心 GIL 管理，尤其是 C 多线程同时调 Python
- **子解释器**：Python 3.12+ 支持子解释器隔离，但很多扩展不支持
- **部署**：嵌入需要目标机器有 Python 库，或用静态链接
- **性能**：频繁 C↔Python 切换有开销，批量处理更好

---

## 8.7 定义新的 Python 类型（进阶）

C API 还能定义全新的 Python 类型（比函数复杂）。这是 pybind11 `py::class_` 的底层。

```c
typedef struct {
    PyObject_HEAD
    int value;
} CustomObject;

static PyObject* Custom_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
    CustomObject* self = (CustomObject*)type->tp_alloc(type, 0);
    if (self != NULL) self->value = 0;
    return (PyObject*)self;
}

static PyTypeObject CustomType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "spam.Custom",
    .tp_basicsize = sizeof(CustomObject),
    .tp_new = Custom_new,
    // ... 更多字段
};
```

代码相当繁琐，这正是 pybind11/Cython 存在的意义——**它们帮你生成这些样板代码**。了解即可，日常不手写。

---

## 8.8 四种方案的本质对比

现在我们已经学完了 Python↔C/C++ 的四种方案，做个本质对比：

| 方案 | 底层 | 你写什么 | 编译器生成什么 | 抽象层次 |
|------|------|---------|--------------|---------|
| ctypes | dlopen + C ABI | Python 声明 | 无（运行时解析） | 最低（纯 Python） |
| cffi | dlopen / C 扩展 | cdef 声明 | C 绑定代码（API模式） | 低 |
| Cython | Python C API | `.pyx`（Python+C类型） | C 代码 → 扩展 | 中 |
| pybind11 | Python C API | C++ 绑定代码 | 模板实例化 → 扩展 | 高 |
| Python C API | —— | 纯 C | 直接是扩展 | 地基 |

**一句话总结**：

- ctypes/cffi：Python 出发，调用 C **函数**
- Cython：Python 出发，**变成** C
- pybind11：C++ 出发，**暴露给** Python
- C API：一切的地基，直接用 Python 解释器的 C 接口

---

## 8.9 本章总结

| 知识点 | 内容 |
|--------|------|
| Python C API | CPython 暴露的 C 接口，所有绑定工具的地基 |
| 扩展模块结构 | PyObject* 函数 + PyMethodDef 方法表 + PyModuleDef + PyInit_xxx |
| 引用计数 | 新引用（负责 decref）vs 借用引用（不要 decref）；错误导致泄漏/UAF |
| 参数解析 | `PyArg_ParseTuple` 格式字符串（i/l/d/s/O/p） |
| 嵌入 Python | `Py_Initialize` → `PyRun_SimpleString` → `Py_Finalize` |
| 嵌入价值 | 给 C 程序加脚本能力（如安全工具规则引擎） |
| 自定义类型 | `PyTypeObject`，繁琐，日常用 pybind11 代替 |
| 方案本质 | ctypes/cffi/Cython/pybind11 都构建在 C API 之上 |

---

## 本章练习

1. 编译 `spam.c` 扩展模块，从 Python 调用 `add` 和 `greet`。
2. 给模块加一个函数，接收列表并返回其长度（练习引用计数）。
3. 用 `PyArg_ParseTuple` 的 `|` 语法写一个带可选参数的函数。
4. 编译 `embed.c`，成功在 C 程序里执行 Python 代码。
5. （进阶）在嵌入的 Python 里导入一个你自己写的 `.py` 文件并调用其函数。
6. 思考：为什么 pybind11 用 RAII 管理引用比手动 decref 更安全？结合第 2 章的所有权概念回答。

---

**下一章预告**：第二卷（Python+C/C++）圆满完成。进入第三卷——**Python 与 Rust**，最安全的混合方案。从 PyO3 开始：用 Rust 写 Python 扩展，在享受 Rust 内存安全与高性能的同时，保持 Python 的易用接口。
