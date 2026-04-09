"""
Module trực quan hóa dữ liệu Retailrocket từ Redis.

Cung cấp các hàm vẽ biểu đồ phân bổ, ma trận tương quan,
scatter/density plots và biểu đồ đặc thù e-commerce.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot_event_distribution(df, save_path=None):

    #Vẽ biểu đồ phân bổ các loại event (view, addtocart, transaction).

    if df is None or len(df) == 0 or "event" not in df.columns:
        return None

    event_counts = df["event"].value_counts()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    colors = ["#2196F3", "#FF9800", "#4CAF50"]
    event_counts.plot(kind="bar", ax=ax1, color=colors[: len(event_counts)])
    ax1.set_title("Số lượng theo loại Event", fontsize=14)
    ax1.set_ylabel("Số lượng")
    ax1.set_xlabel("Loại Event")
    ax1.tick_params(axis="x", rotation=0)
    for i, v in enumerate(event_counts.values):
        ax1.text(i, v + v * 0.01, f"{v:,}", ha="center", fontsize=10)

    ax2.pie(
        event_counts.values,
        labels=event_counts.index,
        autopct="%1.1f%%",
        colors=colors[: len(event_counts)],
        startangle=90,
    )
    ax2.set_title("Tỷ lệ các loại Event", fontsize=14)

    fig.suptitle("Phân bổ Events (dữ liệu từ Redis)", fontsize=16, y=1.02)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
    return fig


def plot_top_items(df, top_n=20, save_path=None):

    #Vẽ biểu đồ top N items được tương tác nhiều nhất.

    if df is None or len(df) == 0 or "itemid" not in df.columns:
        return None

    top_items = df["itemid"].value_counts().head(top_n)

    fig, ax = plt.subplots(figsize=(12, 6))
    top_items.plot(kind="bar", ax=ax, color="#2196F3")
    ax.set_title(f"Top {top_n} Items (từ Redis events)", fontsize=14)
    ax.set_ylabel("Số lượt tương tác")
    ax.set_xlabel("Item ID")
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
    return fig


def plot_popular_items_by_users(df_item_users, top_n=20, save_path=None):

    #Vẽ biểu đồ items có nhiều user tương tác nhất (từ item:*:users).

    if df_item_users is None or len(df_item_users) == 0:
        return None

    top = df_item_users.head(top_n)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(
        [str(x) for x in top["itemid"]],
        top["user_count"],
        color="#4CAF50",
    )
    ax.set_xlabel("Số lượng Users")
    ax.set_ylabel("Item ID")
    ax.set_title(f"Top {top_n} Items phổ biến nhất (Redis item→users)", fontsize=14)
    ax.invert_yaxis()
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
    return fig


def plot_category_tree(df_cat, save_path=None):

    #Vẽ biểu đồ phân bổ category tree.

    if df_cat is None or len(df_cat) == 0:
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Root vs non-root
    root = df_cat["parentid"].isna().sum()
    non_root = df_cat["parentid"].notna().sum()
    ax1.bar(["Root", "Non-root"], [root, non_root], color=["#FF5722", "#3F51B5"])
    ax1.set_title("Root vs Non-root Categories", fontsize=14)
    ax1.set_ylabel("Số lượng")
    for i, v in enumerate([root, non_root]):
        ax1.text(i, v + v * 0.01, str(v), ha="center", fontsize=12)

    # Top parent categories
    if "parentid" in df_cat.columns:
        parent_counts = df_cat["parentid"].dropna().value_counts().head(15)
        parent_counts.plot(kind="bar", ax=ax2, color="#009688")
        ax2.set_title("Top 15 Parent Categories", fontsize=14)
        ax2.set_ylabel("Số con")
        ax2.set_xlabel("Parent ID")
        ax2.tick_params(axis="x", rotation=45)

    fig.suptitle("Phân tích Category Tree (Redis)", fontsize=16, y=1.02)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
    return fig


def plot_item_availability(df_props, save_path=None):

    #Vẽ biểu đồ trạng thái available của items.

    if df_props is None or len(df_props) == 0 or "available" not in df_props.columns:
        return None

    counts = df_props["available"].value_counts()

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#4CAF50" if str(k) == "1" else "#F44336" for k in counts.index]
    counts.plot(kind="bar", ax=ax, color=colors)
    ax.set_title("Trạng thái Available của Items (Redis)", fontsize=14)
    ax.set_ylabel("Số Items")
    ax.set_xlabel("Available")
    ax.tick_params(axis="x", rotation=0)
    for i, v in enumerate(counts.values):
        ax.text(i, v + v * 0.01, f"{v:,}", ha="center", fontsize=11)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
    return fig


def plot_per_column_distribution(df, n_graph_shown=10, n_graph_per_row=5, save_path=None):

    #Vẽ biểu đồ phân bổ (histogram/bar) cho mỗi cột dữ liệu.

    if df is None or len(df) == 0:
        return None

    nunique = df.nunique()
    df_filtered = df[[col for col in df if 1 < nunique[col] < 50]]
    n_row, n_col = df_filtered.shape

    if n_col == 0:
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        ax.text(0.5, 0.5, "Không có cột phù hợp để vẽ",
                ha="center", va="center", fontsize=12)
        ax.set_axis_off()
        return fig

    column_names = list(df_filtered)
    n_graph_row = int((n_col + n_graph_per_row - 1) / n_graph_per_row)

    fig = plt.figure(
        figsize=(6 * n_graph_per_row, 8 * n_graph_row),
        dpi=80, facecolor="w",
    )

    for i in range(min(n_col, n_graph_shown)):
        plt.subplot(n_graph_row, n_graph_per_row, i + 1)
        column_df = df_filtered.iloc[:, i]
        if not np.issubdtype(type(column_df.iloc[0]), np.number):
            column_df.value_counts().plot.bar()
        else:
            column_df.hist()
        plt.ylabel("counts")
        plt.xticks(rotation=90)
        plt.title(f"{column_names[i]}")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
    return fig


def plot_correlation_matrix(df, graph_width=8, save_path=None):

    #Vẽ ma trận tương quan giữa các cột số.

    if df is None or len(df) == 0:
        return None

    df_clean = df.select_dtypes(include=[np.number])
    df_clean = df_clean.dropna(axis="columns")
    df_clean = df_clean[[col for col in df_clean if df_clean[col].nunique() > 1]]

    if df_clean.shape[1] < 2:
        return None

    corr = df_clean.corr()
    fig = plt.figure(figsize=(graph_width, graph_width), dpi=80)
    plt.matshow(corr, fignum=1)
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=90)
    plt.yticks(range(len(corr.columns)), corr.columns)
    plt.gca().xaxis.tick_bottom()
    plt.colorbar()
    plt.title("Ma trận tương quan (Redis data)", fontsize=15)

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
    return fig


def plot_redis_overview(stats, save_path=None):
    """
    Vẽ biểu đồ tổng quan dữ liệu Redis.

    Parameters
    ----------
    stats : dict
        Kết quả từ RedisDataLoader.get_stats()
    """
    labels = []
    values = []

    mapping = {
        "user_keys": "Users (events)",
        "item_user_keys": "Items (users)",
        "item_prop_keys": "Items (props)",
        "category_keys": "Categories",
    }

    for k, label in mapping.items():
        if k in stats and stats[k] > 0:
            labels.append(label)
            values.append(stats[k])

    if not values:
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]
    ax1.bar(labels, values, color=colors[: len(values)])
    ax1.set_title("Phân bổ Keys trong Redis", fontsize=14)
    ax1.set_ylabel("Số lượng Keys")
    for i, v in enumerate(values):
        ax1.text(i, v + v * 0.01, f"{v:,}", ha="center", fontsize=11)

    ax2.pie(values, labels=labels, autopct="%1.1f%%",
            colors=colors[: len(values)], startangle=90)
    ax2.set_title("Tỷ lệ Keys theo loại", fontsize=14)

    fig.suptitle(
        f"Tổng quan Redis — {stats.get('total_keys', 0):,} keys",
        fontsize=16, y=1.02,
    )
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
    return fig
