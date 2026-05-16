# AI 赋能的智能简历分析系统

一个面向招聘初筛场景的简历解析与岗位匹配服务。后端使用 Python + FastAPI，可部署到阿里云函数计算 FC；前端使用 React + Vite，可部署到 GitHub Pages、Vercel 或任意静态托管服务。

## 功能

- 上传单个 PDF 简历，支持多页解析
- 清洗并分段简历文本
- 提取姓名、电话、邮箱、地址等基本信息
- 额外提取求职意向、期望薪资、工作年限、学历、技能、项目经历
- 接收岗位 JD，提取岗位关键词
- 计算技能匹配、经验相关性、教育匹配和综合评分
- 可选接入 OpenAI 兼容模型进行结构化抽取与评分
- 可选接入 Redis 缓存解析和匹配结果
- 提供可用的 Web 页面完成上传、分析、匹配流程

## 项目结构

```text
.
├── backend
│   ├── app
│   │   ├── main.py              # REST API 入口
│   │   ├── models.py            # Pydantic 数据模型
│   │   └── services             # PDF、AI、缓存、匹配服务
│   ├── tests
│   ├── requirements.txt
│   ├── serverless_handler.py    # 阿里云 FC HTTP 入口适配
│   └── s.yaml                   # Serverless Devs 部署示例
└── frontend
    ├── src
    ├── package.json
    └── vite.config.js
```

## 后端本地运行

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

健康检查：

```bash
curl http://localhost:8000/health
```

API 文档：

```text
http://localhost:8000/docs
```

## 前端本地运行

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

默认前端会请求 `http://localhost:8000`。如后端地址不同，修改 `frontend/.env`：

```env
VITE_API_BASE_URL=https://your-api-domain.example.com
```

## 环境变量

后端：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
REDIS_URL=
ALLOWED_ORIGINS=http://localhost:5173
```

说明：

- 未配置 `OPENAI_API_KEY` 时，系统会使用规则抽取和本地评分，确保演示可跑通。
- 配置 `REDIS_URL` 后启用缓存；未配置时使用内存缓存。
- `OPENAI_BASE_URL` 支持 OpenAI 兼容服务，便于切换国内云模型网关。

## REST API

### 上传并解析简历

`POST /api/resumes`

表单字段：

- `file`: PDF 文件

返回包含 `resume_id`、清洗文本、分段结果、结构化信息和缓存命中状态。

### 岗位匹配评分

`POST /api/match`

```json
{
  "resume_id": "已有简历 ID",
  "job_description": "岗位需求文本"
}
```

也可以直接传 `resume_text`：

```json
{
  "resume_text": "候选人简历文本",
  "job_description": "岗位需求文本"
}
```

返回关键词、各维度得分、综合评分和匹配理由。

## 阿里云函数计算部署

推荐使用自定义运行时或容器方式部署 FastAPI 服务。仓库中提供 `backend/s.yaml` 作为 Serverless Devs 示例：

```bash
cd backend
npm install -g @serverless-devs/s
s deploy
```

部署前请在阿里云控制台或 `s.yaml` 中配置环境变量：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `REDIS_URL`
- `ALLOWED_ORIGINS`

## 前端部署

GitHub Pages：

```bash
cd frontend
npm install
npm run build
```

将 `frontend/dist` 发布到 GitHub Pages。若仓库名不是根域名，需要设置：

```env
VITE_BASE_PATH=/your-repo-name/
VITE_API_BASE_URL=https://your-fc-http-trigger-url
```

也可直接部署到 Vercel/Netlify，并配置 `VITE_API_BASE_URL`。

## 测试

```bash
cd backend
pip install -r requirements.txt
pytest
```

## 提交给面试官

- GitHub 仓库地址：`https://github.com/<your-name>/<repo>`
- 线上演示地址：`https://<your-name>.github.io/<repo>/`
- 姓名与联系方式：按 Boss 直聘消息填写
