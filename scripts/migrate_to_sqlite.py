#!/usr/bin/env python3
"""
一次性迁移脚本：CSV 回测结果 → SQLite
运行方式：cd backend && python ../scripts/migrate_to_sqlite.py
"""

import os
import sys
import csv
import json
import sqlite3
from datetime import datetime

# 项目根目录
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(ROOT, "data", "dlqi.db")
RESULTS_CSV = os.path.join(ROOT, "results", "backtest_results.csv")
EQUITY_DIR = os.path.join(ROOT, "results", "equity_curves")
ANALYSIS_JSON = os.path.join(ROOT, "results", "model_analysis.json")
RAW_DIR = os.path.join(ROOT, "data", "raw")
MODELS_DIR = os.path.join(ROOT, "data", "models")


def safe_float(val, default=None):
    if val is None or val == "":
        return default
    try:
        v = float(val)
        if v != v or v == float("inf") or v == float("-inf"):
            return default
        return v
    except (ValueError, TypeError):
        return default


def migrate():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. 导入股票原始数据概要到 stock_data（仅导入摘要记录，避免巨大数据量）
    imported_stocks = 0
    if os.path.isdir(RAW_DIR):
        for fname in sorted(os.listdir(RAW_DIR)):
            if not fname.endswith(".csv"):
                continue
            symbol = fname.replace("us_", "").replace(".csv", "")
            csv_path = os.path.join(RAW_DIR, fname)
            try:
                with open(csv_path) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                if not rows:
                    continue
                # 导入最近 500 条
                for row in rows[-500:]:
                    date_str = row.get("date") or row.get("Date", "")
                    cur.execute(
                        "INSERT OR IGNORE INTO stock_data (symbol, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
                        (
                            symbol,
                            date_str[:10],
                            safe_float(row.get("open") or row.get("Open")),
                            safe_float(row.get("high") or row.get("High")),
                            safe_float(row.get("low") or row.get("Low")),
                            safe_float(row.get("close") or row.get("Close")),
                            safe_float(row.get("volume") or row.get("Volume")),
                        ),
                    )
                imported_stocks += 1
            except Exception as e:
                print(f"  跳过 {fname}: {e}")
    print(f"导入了 {imported_stocks} 只股票的价格数据")

    # 2. 导入模型元数据
    imported_models = 0
    if os.path.isdir(MODELS_DIR):
        for name in sorted(os.listdir(MODELS_DIR)):
            meta_path = os.path.join(MODELS_DIR, name, "metadata.json")
            if not os.path.isfile(meta_path):
                continue
            with open(meta_path) as f:
                meta = json.load(f)
            cur.execute(
                "INSERT OR IGNORE INTO ml_models (name, model_type, params, metrics, model_path, status, created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    name,
                    meta.get("model_type", "unknown"),
                    json.dumps(meta.get("params", {})),
                    json.dumps(meta.get("metrics", {})),
                    os.path.join(MODELS_DIR, name),
                    "trained",
                    meta.get("created_at", datetime.now().isoformat()),
                ),
            )
            imported_models += 1
    print(f"导入了 {imported_models} 个模型元数据")

    conn.commit()
    conn.close()
    print(f"迁移完成！数据库位置: {DB_PATH}")


if __name__ == "__main__":
    migrate()
