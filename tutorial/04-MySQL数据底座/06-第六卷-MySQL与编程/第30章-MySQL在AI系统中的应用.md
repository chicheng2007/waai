# 第 30 章 MySQL 在 AI 系统中的应用

## 本章目标

读完这一章，你将能够：

- 知道 AI 系统里哪些数据该存 MySQL
- 设计特征存储、模型元数据、实验追踪的表
- 理解向量检索中 MySQL 的角色（元数据 + 向量库配合）
- 搭建 RAG 知识库的元数据存储
- 构建 AI + 安全的数据管道

---

## 30.1 AI 系统需要 MySQL 吗

很多人觉得 AI = 大模型 + 向量数据库，MySQL 没用。这是个误区。

AI 系统里大量数据需要**结构化存储和精确查询**，这正是 MySQL 的强项：

| 数据 | 特点 | 适合 MySQL？ |
|------|------|-------------|
| 训练特征 | 结构化、量大 | ✅ |
| 标注数据 | 结构化 | ✅ |
| 模型元数据 | 结构化 | ✅ |
| 实验记录 | 结构化、需查询 | ✅ |
| 用户/权限/日志 | 结构化 | ✅ |
| 向量 | 高维浮点数组 | ❌（用向量库） |
| 知识库原文 | 文本 | ⚠️（MySQL 可存，也可对象存储） |

**结论**：AI 系统通常是 **MySQL（结构化数据）+ 向量库（向量检索）+ 对象存储（大文件）** 的组合。MySQL 负责它擅长的部分。

---

## 30.2 特征存储

训练恶意软件检测模型时，需要存储样本的特征：

```sql
CREATE TABLE malware_features (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sample_hash CHAR(64) NOT NULL COMMENT '样本SHA256',
    file_size INT UNSIGNED COMMENT '文件大小',
    entropy DECIMAL(5,4) COMMENT '熵值',
    import_count INT COMMENT '导入函数数量',
    has_suspicious_api BOOLEAN DEFAULT FALSE COMMENT '是否有可疑API',
    is_malware BOOLEAN NOT NULL COMMENT '标签：是否恶意',
    extracted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_hash (sample_hash),
    INDEX idx_label (is_malware),
    INDEX idx_entropy (entropy)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

用途：

- 训练时批量读取特征：`SELECT file_size, entropy, import_count, is_malware FROM malware_features`
- 去重：`UNIQUE KEY uk_hash` 保证同一样本不重复
- 分析：`SELECT AVG(entropy) FROM malware_features WHERE is_malware=TRUE`

---

## 30.3 模型元数据

管理训练出的模型版本：

```sql
CREATE TABLE model_registry (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL COMMENT '模型名',
    version VARCHAR(32) NOT NULL COMMENT '版本',
    algorithm VARCHAR(64) COMMENT '算法',
    params JSON COMMENT '超参数',
    metrics JSON COMMENT '评估指标（准确率、召回率等）',
    artifact_path VARCHAR(512) COMMENT '模型文件路径',
    status ENUM('TRAINING','READY','DEPLOYED','ARCHIVED') DEFAULT 'TRAINING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_name_version (name, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

插入一条记录：

```sql
INSERT INTO model_registry (name, version, algorithm, params, metrics, artifact_path, status)
VALUES (
    'malware-detector', 'v1.2',
    'RandomForest',
    '{"n_estimators": 100, "max_depth": 10}',
    '{"accuracy": 0.96, "f1": 0.94, "auc": 0.97}',
    '/models/malware-detector-v1.2.pkl',
    'DEPLOYED'
);
```

JSON 类型存灵活的超参数和指标（第 11 章讲过）。查询：

```sql
SELECT name, version,
       metrics->>'$.accuracy' AS accuracy
FROM model_registry
WHERE status = 'DEPLOYED';
```

---

## 30.4 实验追踪（Experiment Tracking）

记录每次训练实验，方便对比和复现：

```sql
CREATE TABLE ml_experiments (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    experiment_name VARCHAR(128) NOT NULL,
    model_id BIGINT UNSIGNED,
    dataset_version VARCHAR(64),
    params JSON,
    metrics JSON,
    notes TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,
    INDEX idx_model (model_id),
    INDEX idx_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

对比两次实验：

```sql
SELECT experiment_name,
       params->>'$.learning_rate' AS lr,
       metrics->>'$.accuracy' AS accuracy,
       metrics->>'$.loss' AS loss
FROM ml_experiments
WHERE model_id = 1
ORDER BY started_at DESC;
```

这就是简易版的 MLflow——很多公司自建实验追踪就是这么做的。

---

## 30.5 向量检索中 MySQL 的角色

大模型应用（RAG）需要向量数据库（如 Milvus、Pinecone、pgvector）。但 MySQL 仍扮演重要角色——**存储元数据**。

典型架构：

```
用户问题 → 向量化 → 向量库检索 Top-K → 得到文档ID和相似度
                                    ↓
                          回 MySQL 查文档详情
                                    ↓
                          组装 Prompt → LLM 生成答案
```

MySQL 存文档的元数据：

```sql
CREATE TABLE knowledge_docs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(255) COMMENT '来源',
    content TEXT COMMENT '原文',
    vector_id VARCHAR(64) COMMENT '向量库中的ID',
    tags JSON COMMENT '标签',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vector_id (vector_id),
    FULLTEXT KEY ft_content (content)  -- 全文索引
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

检索流程（Python 伪代码）：

```python
# 1. 向量库检索，得到文档 ID 列表
doc_ids = vector_db.search(query_vector, top_k=5)

# 2. 回 MySQL 取详情
sql = "SELECT title, content, source FROM knowledge_docs WHERE vector_id IN (%s)" % \
      ','.join(['%s'] * len(doc_ids))
rows = query_mysql(sql, doc_ids)

# 3. 组装 Prompt
context = "\n".join([r['content'] for r in rows])
prompt = f"基于以下资料回答问题:\n{context}\n\n问题: {question}"
```

另外，MySQL 的**全文索引**（FULLTEXT）也能做关键词检索，和向量检索互补（混合检索）。

---

## 30.6 RAG 知识库元数据

RAG（检索增强生成）系统里，MySQL 管理：

- 文档库（哪些文档、来源、版本）
- 分块信息（每个 chunk 对应哪个文档、在向量库里的 ID）
- 对话记录（用户问了什么、AI 答了什么、引用了哪些文档）

```sql
CREATE TABLE rag_chunks (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    doc_id BIGINT UNSIGNED NOT NULL,
    chunk_index INT NOT NULL COMMENT '第几个分块',
    content TEXT NOT NULL,
    vector_id VARCHAR(64) COMMENT '向量库ID',
    token_count INT COMMENT 'token数',
    UNIQUE KEY uk_doc_chunk (doc_id, chunk_index),
    INDEX idx_vector_id (vector_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rag_conversations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED,
    question TEXT NOT NULL,
    answer TEXT,
    cited_chunks JSON COMMENT '引用的chunk ID列表',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 30.7 AI + 安全的数据管道

把 MySQL 用在 AI 安全系统里，典型数据流：

```
1. 数据采集：扫描器、日志、流量 → 写入 MySQL
2. 特征工程：从 MySQL 读数据，提取特征
3. 模型训练：训练恶意检测模型，元数据存 MySQL
4. 模型部署：模型版本存 MySQL，推理服务读取
5. 实时检测：告警写入 MySQL，分析趋势
6. 反馈闭环：误报/漏报标注回写 MySQL，用于再训练
```

示例：把告警反馈用于模型改进：

```sql
-- 记录误报反馈
CREATE TABLE alert_feedback (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    alert_id BIGINT UNSIGNED NOT NULL,
    is_false_positive BOOLEAN NOT NULL COMMENT '是否误报',
    reviewer VARCHAR(64),
    feedback_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_alert (alert_id)
);

-- 统计某模型的误报率
SELECT
    m.name,
    m.version,
    COUNT(*) AS total_alerts,
    SUM(f.is_false_positive) AS false_positives,
    ROUND(SUM(f.is_false_positive)/COUNT(*), 4) AS fp_rate
FROM model_registry m
JOIN ml_experiments e ON e.model_id = m.id
JOIN alert_feedback f ON f.alert_id = e.id
GROUP BY m.name, m.version;
```

---

## 30.8 性能考虑

AI 数据量往往很大，MySQL 要注意：

1. **批量写入**：特征提取结果用 executemany / LOAD DATA 批量入库
2. **合理索引**：常查的列建索引，但别过多（影响写入）
3. **分区表**：按时间分区，方便归档旧数据
4. **冷热分离**：热数据放 MySQL，冷数据归档到对象存储
5. **读写分离**：训练读从库，写入走主库（第 24 章）

```sql
-- 按时间分区示例
CREATE TABLE features_partitioned (
    id BIGINT NOT NULL,
    sample_hash CHAR(64),
    features JSON,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

---

## 30.9 本章总结

| 知识点 | 内容 |
|--------|------|
| AI 与 MySQL | MySQL 管结构化数据，向量库管向量，对象存储管大文件 |
| 特征存储 | 样本特征表；UNIQUE 去重；索引加速查询 |
| 模型元数据 | model_registry；JSON 存参数/指标 |
| 实验追踪 | ml_experiments；对比实验、复现 |
| 向量检索角色 | MySQL 存元数据，向量库存向量，回表取详情 |
| RAG | 文档库、分块、对话记录 |
| AI+安全管道 | 采集→特征→训练→部署→检测→反馈闭环 |
| 性能 | 批量写入、索引、分区、冷热分离、读写分离 |

---

## 本章练习

1. 设计一张特征存储表，包含样本 hash、特征、标签，思考索引怎么建。
2. 创建 model_registry 表，插入一条模型记录，用 `->>` 查询准确率。
3. 创建实验追踪表，写一条查询对比两次实验的指标。
4. 设计一个简单的 RAG 元数据表结构（文档 + 分块 + 对话）。
5. 用 Python 写一个"向量检索后回 MySQL 取详情"的伪代码。
6. 思考：AI 系统为什么需要 MySQL？向量库不能替代它吗？
7. 思考：AI 数据量很大时，MySQL 要注意哪些性能问题？

---

**下一章预告**：进入第七卷——综合实战。我们会用前面所有知识，搭建三个真实项目：安全日志分析系统、威胁情报平台、AI + 安全数据库后端。这是把知识变成能力的关键。
