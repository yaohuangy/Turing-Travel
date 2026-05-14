# 途灵旅行（Turing Travel）

AI 驱动的智能旅行规划助手。输入目的地、日期和偏好，自动生成完整的旅行行程——包含每日景点、餐饮推荐、酒店住宿、预算明细、地图路线和天气预报。

## 功能

- **AI 行程生成**：基于大语言模型（DeepSeek-V4-Pro）生成结构化多日行程，结合本地旅行攻略 RAG 检索增强质量
- **地图可视化**：高德地图展示景点标记和行经路线，支持点击联动
- **智能编辑**：用自然语言修改行程（如"把午餐换成火锅"），AI 自动调整
- **行程管理**：保存、查看、删除历史行程
- **多格式导出**：支持 Markdown 和 PDF 导出
- **天气查询**：匹配每日天气预报
- **预算明细**：交通、住宿、餐饮、门票、其他分项展示

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Ant Design Vue 4 + Pinia |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 |
| AI/LLM | 阿里云 DashScope（DeepSeek-V4-Pro / text-embedding-v4 / qwen3-rerank） |
| 地图 | 高德地图 JS API v2.0 + Web Services |
| 数据库 | SQLite + ChromaDB（向量存储） |
| 缓存 | Redis（可选，不可用时自动降级） |
| 导出 | Jinja2（Markdown）+ ReportLab（PDF） |

## 项目结构

```
Turing-Travel/
├── backend/
│   ├── app/
│   │   ├── agents/          # LLM Agent（行程生成）
│   │   ├── api/             # FastAPI 路由
│   │   │   └── routes/      # trip / weather / export / config
│   │   ├── models/          # Pydantic 模型 + SQLAlchemy ORM
│   │   └── services/        # 业务逻辑（地图/天气/缓存/存储/导出）
│   ├── rag/                 # RAG 检索引擎
│   │   ├── retriever.py     # 查询改写 → 向量搜索 → 重排序
│   │   └── vector_db.py     # ChromaDB 向量库管理
│   ├── data/guides/         # 旅行攻略 Markdown（7 个城市）
│   ├── templates/           # Jinja2 导出模板
│   ├── tests/               # 33 个测试
│   └── eval/                # RAG 评估脚本
├── frontend/
│   └── src/
│       ├── views/           # Home（表单）/ Result（结果）/ History（历史）
│       ├── components/      # AmapTripMap（地图组件）
│       ├── services/        # API 请求封装
│       ├── stores/          # Pinia 状态管理
│       ├── types/           # TypeScript 类型定义
│       └── utils/           # 共享工具函数和城市数据
└── .gitignore
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- Redis（可选）

### 1. 克隆项目

```bash
git clone https://github.com/yaohuangy/Turing-Travel.git
cd Turing-Travel
```

### 2. 配置密钥

```bash
cd backend
cp .env.example .env
```

编辑 `backend/.env`，填入你的 API 密钥：

```env
DASHSCOPE_API_KEY=你的阿里云DashScope密钥
AMAP_API_KEY=你的高德地图Web服务密钥
```

> DashScope 获取：https://dashscope.console.aliyun.com/apiKey
> 高德地图获取：https://console.amap.com/dev/key/app

### 3. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.api.main:app --reload --port 8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 健康检查 |
| GET | `/api/config` | 获取地图 JS Key |
| POST | `/api/trip/generate` | 生成行程 |
| POST | `/api/trip/save` | 保存行程 |
| GET | `/api/trips` | 行程列表 |
| GET | `/api/trip/trip/{id}` | 行程详情 |
| POST | `/api/trip/edit` | AI 编辑行程 |
| DELETE | `/api/trip/trip/{id}` | 删除行程 |
| GET | `/api/weather/forecast` | 天气预报 |
| GET | `/api/export/{id}/markdown` | 导出 Markdown |
| GET | `/api/export/{id}/pdf` | 导出 PDF |
| POST | `/api/export/markdown` | 直接导出 Markdown |
| POST | `/api/export/pdf` | 直接导出 PDF |

## 运行测试

```bash
cd backend
python -m pytest tests/ -q
```

## License

MIT
