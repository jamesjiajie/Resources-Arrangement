# 资源安排 V2

一个团队资源安排跟踪工具，用于记录同事、项目和多任务占用情况。前端使用 Vite + Vue 3，后端使用 FastAPI，数据库使用 SQLite。

## 功能

- 人员管理：姓名、角色、小组、每周容量、状态、备注
- 项目管理：项目名、编码、负责人、优先级、状态、周期、备注
- 安排管理：同事、项目、任务、占用比例、状态、周期、优先级、备注
- 总览看板：团队容量、进行中项目、进行中安排、延期/阻塞统计
- 负载提醒：低占用、正常、接近满载、超负载、有阻塞
- 项目占用：按项目汇总参与人数和资源占用
- 变更记录：新增、编辑、删除会写入活动日志

## 安装

```bash
source .venv/bin/activate
pip install -r requirements.txt
npm install
```

## 开发启动

终端 1 启动后端：

```bash
npm run api
```

终端 2 启动前端：

```bash
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 生产构建与启动

```bash
npm run build
python server.py
```

打开 `http://127.0.0.1:8000`。FastAPI 会同时提供 API 和构建后的前端页面。

## 技术说明

- `backend/main.py`：FastAPI 应用、路由、静态页面托管
- `backend/database.py`：SQLite 连接、初始化、示例数据
- `backend/services.py`：数据读写和汇总逻辑
- `backend/schemas.py`：Pydantic 请求校验
- `frontend/src/App.vue`：Vue 工作台主界面
- `frontend/src/styles.css`：界面样式
- `package.json`：前端脚本和依赖
- `data/resources.db`：运行时生成的 SQLite 数据库

首次启动会自动创建 `data/resources.db` 并写入示例数据。
