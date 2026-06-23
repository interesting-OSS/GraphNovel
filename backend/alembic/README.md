# Alembic 数据库迁移指南

本项目使用 **PostgreSQL + pgvector** 作为数据库，通过 Alembic 管理 schema 版本。

## 📁 目录结构

```
backend/
├── alembic.ini                   # Alembic 配置文件（时间戳命名模板）
├── alembic/
│   ├── env.py                    # 迁移环境配置（自动路径探测 + 显式模型注册）
│   ├── script.py.mako            # 迁移文件模板
│   └── versions/                 # 迁移版本文件
│       ├── 20250622_xxxx_a1b2c3d4_初始数据库结构.py
│       └── ...
```

## 🚀 使用方法

### 前置条件

```bash
cd backend
```

确保 PostgreSQL 可访问（Docker 环境中已自动处理）。

### 生成迁移脚本

```bash
alembic revision --autogenerate -m "描述信息"
```

生成的文件命名格式：`YYYYMMDD_HHMM_revision_slug.py`

### 应用迁移

```bash
alembic upgrade head
```

### 回退迁移

```bash
alembic downgrade -1          # 回退一个版本
alembic downgrade <revision>  # 回退到指定版本
```

### 查看状态

```bash
alembic current               # 当前版本
alembic history               # 迁移历史
alembic heads                  # 分支头
```

### 生成离线 SQL（不直接执行）

```bash
alembic upgrade head --sql > migration.sql
```

## ⚙️ env.py 关键配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `compare_type` | `True` | 检测列类型变更 |
| `compare_server_default` | `True` | 检测 server_default 变更 |
| `render_as_batch` | `False` | PostgreSQL 原生 ALTER TABLE |

### 路径探测

`env.py` 根据自身文件路径自动推算项目根目录并加入 `sys.path`，**不依赖 PYTHONPATH 环境变量**：

```python
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
os.chdir(_project_root)
```

### 模型注册

所有模型在 `env.py` 中**逐个显式导入**，确保 autogenerate 不遗漏任何表：

```python
from app.models.project import Project
from app.models.outline import Outline
# ... 所有模型
```

新增模型后，**必须在 `env.py` 中添加对应的 import 语句**。

## 📝 最佳实践

1. **每个迁移只做一件事** —— 结构变更与数据填充分开
2. **迁移文件用中文 slug** —— 方便快速理解内容
3. **带 down_revision** —— 永远保留回退路径
4. **审阅生成的 SQL** —— `--autogenerate` 不一定总能生成完美脚本
5. **先备份** —— 生产环境执行迁移前务必备份数据库

## 🐛 常见问题

### Q: 找不到 `app` 模块
A: `env.py` 已自动处理路径问题。如仍出现，请确认 `.env` 文件存在且 `DATABASE_URL` 正确。

### Q: autogenerate 漏掉了新表
A: 检查 `env.py` 中是否已导入对应的模型类。

### Q: 迁移后表已存在报错
A: 检查 `alembic_version` 表，手动清理后重新执行：

```sql
DELETE FROM alembic_version;
```
然后重新运行 `alembic upgrade head`。

### Q: Docker 中如何执行迁移？
A: 容器启动时 `entrypoint.sh` 会自动执行 `alembic upgrade head`，无需手动操作。
