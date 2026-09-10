#!/usr/bin/env python3
"""爬虫采完招考公告后，直接批量推送到中台 SAPI。

用法示例：
  export ZC_CENTER_BASE_URL=https://zc-center.example.com
  export ZC_CENTER_APP_KEY=...
  export ZC_CENTER_APP_SECRET=...
  # 联调关闭加密时：
  # export ZC_CENTER_ENCRYPTION=0

  python examples/push_exam_notices.py /path/to/notices.json

JSON 可为：
  1) 公告对象数组
  2) {"items": [ ... ]}
  3) {"list": [ ... ]}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from zc_center import ApiException, Client, SapiException


BATCH_SIZE = 100


def load_items(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("items"), list):
            items = raw["items"]
        elif isinstance(raw.get("list"), list):
            items = raw["list"]
        else:
            raise SystemExit("JSON 需为数组，或含 items/list 字段的对象")
    else:
        raise SystemExit("不支持的 JSON 结构")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SystemExit(f"第 {index} 条不是对象")
        notice = dict(item)
        title = str(notice.get("title") or "").strip()
        collect_source = str(notice.get("collect_source") or "").strip()
        if not title or not collect_source:
            raise SystemExit(f"第 {index} 条缺少必填字段 title / collect_source")

        # 稳定幂等：优先保留已有 uuid / collect_ref；不要生成非 v4 的 UUID
        existing_uuid = str(notice.get("uuid") or "").strip().lower()
        if existing_uuid:
            notice["uuid"] = existing_uuid
        else:
            notice.pop("uuid", None)

        collect_ref = str(notice.get("collect_ref") or "").strip()
        if not collect_ref:
            collect_ref = (
                str(notice.get("official_url") or "").strip()
                or str(notice.get("collect_url") or "").strip()
                or title
            )
            notice["collect_ref"] = collect_ref[:128]

        normalized.append(notice)
    return normalized


def chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main() -> int:
    parser = argparse.ArgumentParser(description="推送招考公告 JSON 到中台")
    parser.add_argument("json_file", type=Path, help="爬虫生成的公告 JSON 文件")
    parser.add_argument("--dry-run", action="store_true", help="只校验与打印，不实际上报")
    args = parser.parse_args()

    if not args.json_file.is_file():
        print(f"文件不存在: {args.json_file}", file=sys.stderr)
        return 1

    items = load_items(args.json_file)
    print(f"载入 {len(items)} 条公告")

    if args.dry_run:
        print("dry-run：跳过上报")
        return 0

    base_url = os.environ.get("ZC_CENTER_BASE_URL", "").strip()
    app_key = os.environ.get("ZC_CENTER_APP_KEY", "").strip()
    app_secret = os.environ.get("ZC_CENTER_APP_SECRET", "").strip()
    encryption = os.environ.get("ZC_CENTER_ENCRYPTION", "1").strip() not in {"0", "false", "False"}

    if not base_url or not app_key or not app_secret:
        print("请设置 ZC_CENTER_BASE_URL / APP_KEY / APP_SECRET", file=sys.stderr)
        return 1

    client = Client(
        base_url=base_url,
        app_key=app_key,
        app_secret=app_secret,
        encryption=encryption,
    )

    total_created = total_exists = total_failed = 0
    try:
        client.ping().send("exam-notice-crawler")
        for batch_index, batch in enumerate(chunks(items, BATCH_SIZE), start=1):
            data = client.exam_notice().report_batch(batch).data() or {}
            created = int(data.get("created") or 0)
            exists = int(data.get("exists") or 0)
            failed = int(data.get("failed") or 0)
            total_created += created
            total_exists += exists
            total_failed += failed
            print(
                f"batch={batch_index} size={len(batch)} "
                f"created={created} exists={exists} failed={failed}"
            )
            for row in data.get("results") or []:
                if row.get("action") == "failed":
                    print(f"  fail index={row.get('index')} error={row.get('error')}", file=sys.stderr)
    except ApiException as exc:
        print(f"业务失败 code={exc.code} http={exc.http_status} msg={exc}", file=sys.stderr)
        return 2
    except SapiException as exc:
        print(f"SAPI失败: {exc}", file=sys.stderr)
        return 3

    print(f"完成 created={total_created} exists={total_exists} failed={total_failed}")
    return 0 if total_failed == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
