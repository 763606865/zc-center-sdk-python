# ZC Center Python SDK

适用于 Python 3.10+ 的中台 SAPI 服务端 SDK，提供 HMAC-SHA256 请求签名、AES-256-GCM 加解密、响应验签，以及招考公告/岗位推送封装。

协议与中台 [`docs/sapi/`](../../docs/sapi/README.md)、ThinkPHP / Spring Boot SDK 保持一致。许可证：Apache-2.0。

`app_secret` 只能保存在爬虫/服务端，禁止写入前端或客户端。

## 安装

PyPI（发布后）：

```bash
pip install zc-center-sdk-python
```

源码开发（推荐虚拟环境，避免 macOS `externally-managed-environment`）：

```bash
cd sdk/python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
pytest -q
```

发布到 PyPI 的完整步骤见 [PUBLISH.md](./PUBLISH.md)。

## 配置

| 环境变量 | 说明 |
| --- | --- |
| `ZC_CENTER_BASE_URL` | 中台根地址，如 `https://zc-center.example.com` |
| `ZC_CENTER_APP_KEY` | 中台应用 `app_key` |
| `ZC_CENTER_APP_SECRET` | 中台应用 `app_secret` |
| `ZC_CENTER_ENCRYPTION` | `1`/`0`，须与中台 `SAPI_ENCRYPTION_ENABLED` 一致 |

联调可关闭加密；生产必须开启。

## 爬虫推荐流程

1. 在中台「业务管理 → 应用管理」为爬虫创建生态应用，拿到 `app_key` / `app_secret`，配置 IP 白名单。
2. 先推公告：`exam_notice.report` / `report_batch`（单次最多 100 条公告）。
3. 再推岗位：`exam_position.report_batch(notice_uuid, items, sync_index=...)`，每批最多 **100** 条岗位；最后一批 `sync_index=True`。省考/国考数万岗位很正常，不要塞进公告 JSON。
4. 每条公告至少传 `title`、`collect_source`；强烈建议再传稳定幂等键之一：
   - `uuid`（来源系统 UUID v4）
   - 或 `collect_ref`（来源站点内唯一 ID）
   - 或稳定的 `official_url` / `collect_url`
5. 若仍在公告里带了 `positions`，SDK 会自动拆出并分批上报（乡镇/事业单位小量岗位可用）。示例脚本也会先拆岗位再上报。

### 代码示例

```python
from zc_center import Client

client = Client(
    base_url="https://zc-center.example.com",
    app_key="...",
    app_secret="...",
    encryption=True,
)

client.ping().send("crawler-ready")

reported = client.exam_notice().report({
    "title": "某省公务员考试录用公告",
    "collect_source": "某省公务员局",
    "collect_ref": "src-2026-001",
    "exam_year": 2026,
    "recruit_count": 50000,
    "official_url": "https://example.com/notices/1",
}).data()
notice_uuid = reported["notice"]["uuid"]

client.exam_position().report_batch(
    notice_uuid,
    [{"name": "综合管理岗", "code": "119919101", "recruit_count": 1}],
    sync_index=True,
)

page = client.exam_notice().list({
    "last_uuid": "",
    "limit": 100,
    "exam_year": 2026,
    "recruit_count_min": 100,
}).data()
```

Flask 等框架无特殊依赖，在服务端任务里直接 `from zc_center import Client` 即可。

### 一键推送 JSON 文件

```bash
export ZC_CENTER_BASE_URL=https://zc-center.example.com
export ZC_CENTER_APP_KEY=...
export ZC_CENTER_APP_SECRET=...

python examples/push_exam_notices.py /data/crawler/notices-2026-09-09.json
```

JSON 支持数组，或 `{"items":[...]}` / `{"list":[...]}`。

## 字段约定（招考公告）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `title` | 是 | 公告标题 |
| `collect_source` | 是 | 采集来源站点/单位名 |
| `uuid` | 推荐 | UUID v4，来源稳定 ID |
| `collect_ref` | 推荐 | 来源侧业务主键 |
| `official_url` / `collect_url` | 推荐 | 用于排重 |
| `exam_year` | 否 | 招考年份，如 `2026` |
| `recruit_count` | 否 | 计划录用总人数（不是岗位条数） |
| `code` / `exam_type` / `area_code` | 否 | 业务编码、招考类型、地区码 |
| `publisher_name` / `summary` / `content` | 否 | 发布单位、摘要、正文 |
| `publish_time` 等时间字段 | 否 | Unix 秒；也可传可解析时间字符串 |
| `positions` | 否 | 仅小量岗位可内嵌；SDK 会拆成 `exam_position.report_batch` |

排重与岗位字段见 [`docs/sapi/招考公告.md`](../../docs/sapi/招考公告.md)。

本 SDK 走推模式：爬虫写完即上报。中台无需再为「几点读哪个目录」建配置表；若仍保留本地 JSON，仅作备份或对账即可。

## 简历增量同步

```python
page = client.resume().list({"updated_after": 0, "last_id": 0, "limit": 100})
client.resume().update({"uuid": resume_uuid, "job_status": "actively_looking"})
```

每页都应保存 `next_updated_after` 与 `next_last_id`，下次请求同时回传。

## 职位库 / 职位

```python
client.job_bank().list({"page": 1, "page_size": 20})
page = client.job().list({"updated_after": 0, "last_id": 0, "limit": 100})
client.job().report({
    "bank_code": "default_center",
    "company_credit_code": "91110000MA01234567",
    "code": "JD-001",
    "title": "后端工程师",
    "employment_type": 1,
    "status": 1,
})
client.job().update({"uuid": job_uuid, "status": 2, "remark": "协助暂停"})
```

游标与权限见中台 [`docs/sapi/职位.md`](../../docs/sapi/职位.md)。
