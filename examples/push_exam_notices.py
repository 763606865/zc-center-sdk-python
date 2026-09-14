#!/usr/bin/env python3
"""爬虫采完招考公告后，直接批量推送到中台 SAPI。

公告与岗位分开上报：先推公告，再按每批最多 100 条推岗位。
最后一批岗位 sync_index=true，刷新公告检索索引。

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

每条公告可带 positions 数组（数万条也可）；脚本会拆出后再分批上报。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from zc_center import ApiException, Client, SapiException
from zc_center.api.exam_notice import POSITION_BATCH_SIZE

NOTICE_BATCH_SIZE = 100


def load_items(path: Path) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
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

    normalized: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SystemExit(f"第 {index} 条不是对象")
        notice = dict(item)
        title = str(notice.get("title") or "").strip()
        collect_source = str(notice.get("collect_source") or "").strip()
        if not title or not collect_source:
            raise SystemExit(f"第 {index} 条缺少必填字段 title / collect_source")

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

        raw_positions = notice.pop("positions", None)
        positions: list[dict[str, Any]] = []
        if isinstance(raw_positions, list):
            for pos_index, position in enumerate(raw_positions):
                if not isinstance(position, dict):
                    raise SystemExit(f"第 {index} 条 positions[{pos_index}] 不是对象")
                positions.append(position)

        normalized.append((notice, positions))
    return normalized


def chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def notice_uuid(row: dict[str, Any], fallback: dict[str, Any]) -> str:
    notice = row.get("notice")
    if isinstance(notice, dict) and notice.get("uuid"):
        return str(notice["uuid"])
    return str(fallback.get("uuid") or "")


def push_positions(client: Client, notice_uuid: str, positions: list[dict[str, Any]]) -> int:
    if not notice_uuid or not positions:
        return 0
    batches = chunks(positions, POSITION_BATCH_SIZE)
    for index, batch in enumerate(batches):
        client.exam_position().report_batch(
            notice_uuid,
            batch,
            sync_index=index == len(batches) - 1,
        )
    return len(positions)


def main() -> int:
    parser = argparse.ArgumentParser(description="推送招考公告 JSON 到中台")
    parser.add_argument("json_file", type=Path, help="爬虫生成的公告 JSON 文件")
    parser.add_argument("--dry-run", action="store_true", help="只校验与打印，不实际上报")
    args = parser.parse_args()

    if not args.json_file.is_file():
        print(f"文件不存在: {args.json_file}", file=sys.stderr)
        return 1

    pairs = load_items(args.json_file)
    position_total = sum(len(positions) for _, positions in pairs)
    print(f"载入 {len(pairs)} 条公告，{position_total} 条岗位")

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

    total_created = total_exists = total_failed = total_positions = 0
    try:
        client.ping().send("exam-notice-crawler")
        notices = [notice for notice, _ in pairs]
        positions_by_index = [positions for _, positions in pairs]
        for batch_index, start in enumerate(range(0, len(notices), NOTICE_BATCH_SIZE), start=1):
            batch = notices[start : start + NOTICE_BATCH_SIZE]
            data = client.exam_notice().report_batch(batch).data() or {}
            created = int(data.get("created") or 0)
            exists = int(data.get("exists") or 0)
            failed = int(data.get("failed") or 0)
            total_created += created
            total_exists += exists
            total_failed += failed
            print(
                f"notice_batch={batch_index} size={len(batch)} "
                f"created={created} exists={exists} failed={failed}"
            )
            results = data.get("results") or []
            for offset, notice in enumerate(batch):
                row = results[offset] if offset < len(results) and isinstance(results[offset], dict) else {}
                if row.get("action") == "failed":
                    print(f"  fail index={row.get('index')} error={row.get('error')}", file=sys.stderr)
                    continue
                uuid = notice_uuid(row, notice)
                pushed = push_positions(client, uuid, positions_by_index[start + offset])
                total_positions += pushed
                if pushed:
                    print(f"  positions notice={uuid} count={pushed}")
    except ApiException as exc:
        print(f"业务失败 code={exc.code} http={exc.http_status} msg={exc}", file=sys.stderr)
        return 2
    except SapiException as exc:
        print(f"SAPI失败: {exc}", file=sys.stderr)
        return 3

    print(
        f"完成 created={total_created} exists={total_exists} "
        f"failed={total_failed} positions={total_positions}"
    )
    return 0 if total_failed == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
