# Ceron 运维手册（Operations）

面向日常运行、监控、升级与排障。部署步骤见 [DEPLOYMENT.md](./DEPLOYMENT.md)。

## 1. 服务拓扑

```
frontend :3000  ──/api 反代──▶  go-svc :8080  ──REST──▶  python-svc :8000 ──▶ LLM/OCR/富集数据源
                                    │
                                    └─ OnComplete ─▶ CRM webhook（可选）
```

| 服务 | 端口 | 健康检查 |
|---|---|---|
| python-svc | 8000 | `GET /health`（含数据驻留合规状态） |
| go-svc | 8080 | `GET /health` |
| frontend | 3000 | HTTP 200 |

## 2. 日常运维

- **启动/停止**：Docker `docker compose up -d / down`；systemd `systemctl restart ceron-python ceron-gateway`；Windows NSSM `nssm restart CeronPython`。
- **日志**：
  - Docker：`docker compose logs -f go-svc python-svc`
  - systemd：`journalctl -u ceron-python -f`
  - Windows NSSM：查看 NSSM 配置的输出文件或事件查看器。
- **关键日志**：go-svc 启动行会打印 `python svc=…, workers=N, crm=…`，可确认配置生效；Python 控制台打印 uvicorn 访问日志。

## 3. 监控建议

- 拨测：每分钟 GET 两个 `/health`；失败告警。
- 业务指标（生产接入 Prometheus 时采集）：intake QPS、job completed/failed 比率、Python /v1/pipeline 时延、LLM 调用失败率。
- 当前作业表为**内存态**（go-svc 重启丢失历史），生产化时替换为 Postgres/Redis 持久化（见 roadmap）。

## 4. 升级与回滚

```bash
# 升级
git pull
cd backend/python-svc && py -3 -m pytest -q      # 测试
cd ../go-svc && go build ./... && go vet ./...   # 构建
docker compose up --build -d                     # 或逐服务重启

# 回滚
git checkout <上一个发布 tag>
docker compose up --build -d
```

升级顺序：先 python-svc（接口向后兼容），再 go-svc，最后 frontend。

## 5. 配置变更

1. 修改对应 `.env`（python-svc 或 go-svc）。
2. 重启对应服务使配置生效。
3. 用 `/health` 与一次 intake 冒烟验证。

新增配置项时必须同步更新 `.env.example` 与本手册（见第 7 节文档同步策略）。

## 6. 故障排查（速查）

| 现象 | 排查 |
|---|---|
| intake 返回 500，job failed | python-svc 未启动或 `PYTHON_SVC_URL` 不对；看 go-svc 日志中的 HTTP 错误 |
| pipeline 返回「text 或 image_base64 至少提供一项」 | 请求体缺字段 |
| OCR 报错 | `OCR_PROVIDER=azure` 但未配 ENDPOINT/KEY；tesseract 未安装 chi_tra 语言包 |
| 富集 flags 出现「查冊失敗/服務不可用」 | 外部数据源不通，已自动降级为人工复核，属预期兜底 |
| 抽取字段缺失 | mock 正则能力有限；配置真实 LLM 后复测，并跑 `py poc/bilingual_poc.py` 对比 |

## 7. 文档同步策略（随代码更新）

为保证文档不过期，**每次代码变更需同步更新以下文件**：

| 变更类型 | 需更新的文档 |
|---|---|
| 新增/修改 REST 接口 | 根 `README.md` API 说明 + `docs/DEPLOYMENT.md` 验证清单 |
| 新增配置项（env） | 对应 `.env.example` + `docs/DEPLOYMENT.md` §2 + 本手册 §5 |
| 新增服务/端口 | `docs/DEPLOYMENT.md`、本手册 §1、`docker-compose.yml` |
| 新增模块/能力 | 根 `README.md` 架构与能力清单 |
| 验证状态变化 | 根 `README.md`「已验证」章节（测试数、构建结果） |

提交前检查项：代码改了，上表对应文档是否也改了？
