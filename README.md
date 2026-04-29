# CompeteHub

CompeteHub 是面向大学生竞赛场景的信息聚合、筛选、推荐、订阅提醒、交流论坛和后台管理系统。

## 架构

项目采用前后端分离的单仓库工程结构：

```text
frontend/  Vue 3 前端应用
backend/   Flask 后端 API
infra/     Nginx、PostgreSQL 等基础设施配置
docs/      需求、技术栈和架构文档
scripts/   本地开发和初始化脚本
```

后端采用模块化单体架构，前端通过 Axios 调用 `/api/v1` 接口。生产环境由 Nginx 托管前端静态资源，并将 `/api` 请求反向代理到 Flask/Gunicorn。

## 本地开发

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app run.py init-db
flask --app run.py run
```

如果当前环境不方便创建虚拟环境，也可以把依赖安装到 `backend/.python_packages`，再使用本地开发脚本启动：

```powershell
python -m pip install --target backend\.python_packages -r backend\requirements.txt
python scripts\run_backend_dev.py
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

当前环境如果没有 `npm`，可以先启动免构建静态演示界面：

```powershell
python scripts\run_frontend_demo.py
```

开发地址：

- 前端：http://localhost:5173
- 后端：http://localhost:5000/api/v1/health
- 同 WiFi 访问：http://192.168.124.10:5173

外部访问说明见 `docs/外部访问说明.md`。

## Docker 运行

```powershell
docker compose up --build
```

默认服务：

- Web：http://localhost
- PostgreSQL：localhost:5432
- Redis：localhost:6379
