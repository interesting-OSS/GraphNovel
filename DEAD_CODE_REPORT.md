# GraphNovel 项目死代码 / 未使用功能清单

> 扫描时间：2026-06-23  
> 范围：`backend/app/` + `frontend/src/`

---

## 一、后端 — 完全死代码

### 1. `ContextInjectionNode` 类 — 从未被使用

**文件：** `backend/app/graphs/nodes/retrieval.py` 第 169 行

定义了 `RetrievalNode` 的子类，但整个项目中没有任何地方 import 或实例化它。

```python
class ContextInjectionNode(RetrievalNode):
    ...
```

**建议：** 删除 `ContextInjectionNode` 类。

---

### 2. `clear_project_metrics()` 函数 — 从未被调用

**文件：** `backend/app/graphs/metrics.py` 第 116 行

函数定义完整，但全项目搜索无任何调用方。

**建议：** 删除此函数。

---

### 3. `BaseAgent` 死 import

**文件：** `backend/app/graphs/subgraphs/world_build.py` 第 6 行

```python
from app.agents.base_agent import BaseAgent  # 导入但未使用
```

文件内从未引用 `BaseAgent`。

**建议：** 删除该 import 行。

---

### 4. `api/__init__.py` — 空文件

**文件：** `backend/app/api/__init__.py`

内容为空，所有路由注册都在 `main.py` 中完成。

**建议：** 删除或保留均可（不影响运行）。

---

## 二、后端 — 部分未使用

### 5. `PROMPT_CATEGORIES` 字典的值未被消费

**文件：** `backend/app/constants/prompt_categories.py`

只有 `CATEGORY_LIST`（字典的键列表）被 `api/prompt_templates.py` 使用，字典值中的描述和模板列表无人读取。

**建议：** 如后续不再需要模板分类描述，可简化为纯列表。

---

### 6. `graphs/metrics.py` 指标系统 — 仅内存存储

**文件：** `backend/app/graphs/metrics.py`

功能正常，但数据存储在模块级 `defaultdict(list)` 中，服务重启即丢失。可通过 `/api/graph-status/metrics/` 查询。

**建议：** 如需生产环境持久化，应接入 Redis 或时序数据库。

---

## 三、前端 — 完全死组件（3 个）

### 7. `GraphViewer`

**文件：** `frontend/src/components/GraphViewer/index.tsx`

完整的 LangGraph 可视化组件（引用 `@xyflow/react`），未被任何页面导入。

### 8. `FlowMonitor`

**文件：** `frontend/src/components/FlowMonitor/index.tsx`

图执行流程监控组件（引用 `@xyflow/react`），未被任何页面导入。

### 9. `CharacterGraph`

**文件：** `frontend/src/components/CharacterGraph/index.tsx`

角色关系图可视化组件（引用 `@xyflow/react`），未被任何页面导入。

**建议：** 三个组件均可删除，或接入 `GraphMonitor` / `RelationshipMap` 页面。

---

## 四、前端 — 完全死的 API 对象（3 组，10 个方法）

### 10. `inspirationApi`（3 个方法）

**文件：** `frontend/src/services/api.ts` 第 188-195 行

```typescript
export const inspirationApi = {
  generate: (...) => ...,
  generateStream: (...) => ...,
  list: (...) => ...,
};
```

三个方法全无人调用。Inspiration 页面直接使用 `ssePost` 绕过了这个 API 对象。

### 11. `wizardStreamApi`（2 个方法）

**文件：** `frontend/src/services/api.ts` 第 198-203 行

```typescript
export const wizardStreamApi = {
  start: (...) => ...,
  status: (...) => ...,
};
```

### 12. `polishApi`（2 个方法）

**文件：** `frontend/src/services/api.ts` 第 214-217 行

```typescript
export const polishApi = {
  polish: (...) => ...,
  rewrite: (...) => ...,
};
```

**建议：** 三组 API 对象均可删除。

---

## 五、前端 — 零散死 API 方法（~15 个）

| API 对象 | 死方法 |
|---|---|
| `projectApi` | `export`, `import` |
| `characterApi` | `get` |
| `chapterApi` | `get` |
| `settingsApi` | `get`, `save`, `listPresets` |
| `taskApi` | `get` |
| `graphStatusApi` | `getHistory` |
| `relationshipApi` | `create`, `update`, `delete` |
| `skillApi` | `chat`, `get`, `delete` |
| `writingStyleApi` | `presets` |
| `promptTemplateApi` | `categories` |
| `mcpApi` | `callTool` |
| `coverApi` | `generate`（`projectApi.generateCover` 已覆盖） |
| `chapterExtendedApi` | `generateStream`, `analyze`, `polish`, `rewrite`, `partialRegenerate`, `getDiff` |

**建议：** 逐方法删除，或确认对应功能后续会接入后再保留。

---

## 六、前端 — 死类型定义（16 个）

**文件：** `frontend/src/types/index.ts`

| 类型 | 行号 |
|---|---|
| `Inspiration` | 161-168 |
| `PaginationResponse<T>` | 183-189 |
| `ApiResponse<T>` | 191-194 |
| `ApiError` | 196-203 |
| `WizardBasicInfo` | 207-215 |
| `WorldSetting` | 217-224 |
| `PlotPoint` | 228-232 |
| `ConflictInfo` | 234-239 |
| `EmotionalArc` | 241-246 |
| `ChapterAnalysis` | 248-262 |
| `SSEProgress` | 266-272 |
| `SSEChunk` | 274-277 |
| `SSEResult` | 279-282 |
| `SSEError` | 284-288 |
| `SSEDone` | 290-293 |
| `SSEEvent` | 295 |

> 注：`sseClient.ts` 自行定义了内部的 SSE 类型，不依赖这些。

**建议：** 可全部删除。

---

## 清理优先级建议

| 优先级 | 内容 | 理由 |
|---|---|---|
| P0 | 后端死 import（#3） | 一行改动，立即见效 |
| P1 | 后端死类/死函数（#1, #2） | 减少维护负担 |
| P1 | 前端 3 组死 API 对象（#10-12） | 减少 API 层误导 |
| P2 | 前端 16 个死类型（第六节） | 减少类型文件臃肿 |
| P2 | 前端 ~15 个零散死方法（第五节） | 逐方法确认，可能部分后续会用 |
| P3 | 前端 3 个死组件（#7-9） | 这些组件代码完整，可能后续接入 |
| P3 | 后端部分未使用（#5, #6） | 功能正常，非紧急 |
