"""
Module phân tích dữ liệu Retailrocket từ Redis.

Cung cấp các hàm phân tích thống kê cho dữ liệu đã đọc từ Redis,
bao gồm thống kê mô tả, phân tích sự kiện, items và categories.
"""

import pandas as pd
import numpy as np

def get_basic_stats(df, name="DataFrame"):

    #Lấy thống kê cơ bản của DataFrame.

    if df is None or len(df) == 0:
        return {"name": name, "num_rows": 0, "num_columns": 0}
    return {
        "name": name,
        "num_rows": len(df),
        "num_columns": len(df.columns),
        "columns": list(df.columns),
        "dtypes": {col: str(df[col].dtype) for col in df.columns},
        "missing_values": df.isnull().sum().to_dict(),
    }


def analyze_events(df):

    #Phân tích chi tiết dữ liệu events.

    if df is None or len(df) == 0:
        return {"error": "Không có dữ liệu events"}

    results = {}
    results["total_events"] = len(df)

    if "event" in df.columns:
        results["event_counts"] = df["event"].value_counts().to_dict()

    if "visitorid" in df.columns:
        results["unique_visitors"] = df["visitorid"].nunique()

    if "itemid" in df.columns:
        results["unique_items"] = df["itemid"].nunique()
        results["top_10_items"] = df["itemid"].value_counts().head(10).to_dict()

    return results


def analyze_category_tree(df):
 
    #Phân tích dữ liệu category tree.

    if df is None or len(df) == 0:
        return {"error": "Không có dữ liệu category tree"}

    results = {}
    results["total_categories"] = len(df)

    if "parentid" in df.columns:
        results["root_categories"] = df["parentid"].isna().sum()
        results["non_root_categories"] = df["parentid"].notna().sum()

    return results


def analyze_item_properties(df):

    #Phân tích dữ liệu item properties.

    if df is None or len(df) == 0:
        return {"error": "Không có dữ liệu item properties"}

    results = {}
    results["total_items"] = len(df)

    if "categoryid" in df.columns:
        results["unique_categories"] = df["categoryid"].nunique()

    if "available" in df.columns:
        avail_counts = df["available"].value_counts().to_dict()
        results["availability"] = avail_counts

    return results


def analyze_item_users(df):

    #Phân tích dữ liệu item → users mapping.

    if df is None or len(df) == 0:
        return {"error": "Không có dữ liệu item-users"}

    results = {}
    results["total_items"] = len(df)

    if "user_count" in df.columns:
        results["avg_users_per_item"] = round(df["user_count"].mean(), 2)
        results["max_users_per_item"] = int(df["user_count"].max())
        results["min_users_per_item"] = int(df["user_count"].min())
        results["top_10_popular_items"] = (
            df.nlargest(10, "user_count")[["itemid", "user_count"]]
            .set_index("itemid")["user_count"]
            .to_dict()
        )

    return results


def get_dataframe_summary(df, name="DataFrame"):

    #Tạo bản tóm tắt dạng text cho DataFrame.

    if df is None or len(df) == 0:
        return f"=== {name} ===\nKhông có dữ liệu.\n"

    lines = []
    lines.append(f"=== {name} ===")
    lines.append(f"Số dòng: {len(df)}")
    lines.append(f"Số cột: {len(df.columns)}")
    lines.append(f"Các cột: {', '.join(df.columns)}")
    lines.append("")

    for col in df.columns:
        dtype = df[col].dtype
        n_unique = df[col].nunique()
        n_missing = df[col].isnull().sum()
        pct_missing = round(n_missing / len(df) * 100, 2) if len(df) > 0 else 0
        lines.append(f"  {col}:")
        lines.append(f"    Kiểu: {dtype} | Duy nhất: {n_unique} | Thiếu: {n_missing} ({pct_missing}%)")

    return "\n".join(lines)
