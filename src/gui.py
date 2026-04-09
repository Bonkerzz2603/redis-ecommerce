"""
Giao diện đồ họa (GUI) cho Retailrocket Recommender — Redis Edition.

Kết nối trực tiếp Redis Server để tải và phân tích dữ liệu,
không cần import CSV thủ công.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data_loader import RedisDataLoader
from src.analysis import (
    get_basic_stats, analyze_events, analyze_category_tree,
    analyze_item_properties, analyze_item_users, get_dataframe_summary,
)
from src.visualization import (
    plot_event_distribution, plot_top_items,
    plot_popular_items_by_users, plot_category_tree,
    plot_item_availability, plot_per_column_distribution,
    plot_correlation_matrix, plot_redis_overview,
)

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class RetailrocketApp:
    #Ứng dụng GUI chính — kết nối Redis Server.

    def __init__(self, root):
        self.root = root
        self.root.title("Retailrocket Recommender — Redis Edition")
        self.root.geometry("1250x820")
        self.root.minsize(950, 650)

        # Biến
        self.redis_host = tk.StringVar(value="localhost")
        self.redis_port = tk.IntVar(value=6379)
        self.redis_db = tk.IntVar(value=0)
        self.redis_password = tk.StringVar(value="")
        self.max_users = tk.IntVar(value=500)

        self.loader = None          # RedisDataLoader
        self.loaded_data = {}       # dict of DataFrames
        self.redis_stats = {}       # thống kê nhanh
        self.current_canvas = None
        self.current_toolbar = None
        self.current_tb_frame = None

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_statusbar()

        self.update_status("Sẵn sàng. Nhấn 'Kết nối Redis' để bắt đầu.")

    # ==================== MENU ====================
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Kết nối Redis", command=self.connect_redis)
        file_menu.add_command(label="Ngắt kết nối", command=self.disconnect_redis)
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        data_menu = tk.Menu(menubar, tearoff=0)
        data_menu.add_command(label="Tải Events", command=lambda: self.load_dataset("events"))
        data_menu.add_command(label="Tải Item Properties", command=lambda: self.load_dataset("item_properties"))
        data_menu.add_command(label="Tải Category Tree", command=lambda: self.load_dataset("category_tree"))
        data_menu.add_command(label="Tải Item-Users", command=lambda: self.load_dataset("item_users"))
        data_menu.add_separator()
        data_menu.add_command(label="Tải tất cả", command=self.load_all_data)
        menubar.add_cascade(label="Dữ liệu", menu=data_menu)

        chart_menu = tk.Menu(menubar, tearoff=0)
        chart_menu.add_command(label="Tổng quan Redis", command=self.plot_overview)
        chart_menu.add_separator()
        chart_menu.add_command(label="Phân bổ Event", command=self.plot_events)
        chart_menu.add_command(label="Top Items (events)", command=self.plot_top_items)
        chart_menu.add_command(label="Items phổ biến (users)", command=self.plot_popular_items)
        chart_menu.add_command(label="Category Tree", command=self.plot_categories)
        chart_menu.add_command(label="Item Availability", command=self.plot_availability)
        chart_menu.add_separator()
        chart_menu.add_command(label="Phân bổ cột — Events", command=lambda: self.plot_distribution("events"))
        chart_menu.add_command(label="Ma trận tương quan", command=lambda: self.plot_correlation("events"))
        menubar.add_cascade(label="Biểu đồ", menu=chart_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Về ứng dụng", command=self.show_about)
        menubar.add_cascade(label="Trợ giúp", menu=help_menu)

    # ==================== TOOLBAR ====================
    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(toolbar, text="Host:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(toolbar, textvariable=self.redis_host, width=14).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(toolbar, text="Port:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(toolbar, textvariable=self.redis_port, width=6).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(toolbar, text="DB:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(toolbar, textvariable=self.redis_db, width=3).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(toolbar, text="Pass:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(toolbar, textvariable=self.redis_password, width=10, show="*").pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(toolbar, text="Kết nối Redis", command=self.connect_redis).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Label(toolbar, text="Max users:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Spinbox(toolbar, from_=50, to=50000, increment=50,
                     textvariable=self.max_users, width=7).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(toolbar, text="Tải dữ liệu", command=self.load_all_data).pack(side=tk.LEFT, padx=(0, 4))

        # Đèn trạng thái kết nối
        self.conn_label = ttk.Label(toolbar, text="● Chưa kết nối", foreground="red")
        self.conn_label.pack(side=tk.RIGHT, padx=4)

    # ==================== MAIN AREA ====================
    def _build_main_area(self):
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---- LEFT ----
        left_frame = ttk.Frame(self.paned, width=370)
        self.paned.add(left_frame, weight=1)

        self.left_notebook = ttk.Notebook(left_frame)
        self.left_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab Redis Info
        info_frame = ttk.Frame(self.left_notebook, padding=5)
        self.left_notebook.add(info_frame, text="Redis")
        self.info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Tab Thống kê
        stats_frame = ttk.Frame(self.left_notebook, padding=5)
        self.left_notebook.add(stats_frame, text="Thống kê")
        self.stats_text = scrolledtext.ScrolledText(stats_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        # Tab Dữ liệu
        data_outer = ttk.Frame(self.left_notebook, padding=5)
        self.left_notebook.add(data_outer, text="Dữ liệu")

        # Selector
        sel_frame = ttk.Frame(data_outer)
        sel_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(sel_frame, text="Dataset:").pack(side=tk.LEFT)
        self.ds_combo = ttk.Combobox(sel_frame, state="readonly", width=20,
                                      values=["events", "item_properties", "category_tree", "item_users"])
        self.ds_combo.pack(side=tk.LEFT, padx=4)
        self.ds_combo.bind("<<ComboboxSelected>>", self.on_dataset_select)

        self.data_tree = ttk.Treeview(data_outer, show="headings", height=18)
        v_scroll = ttk.Scrollbar(data_outer, orient=tk.VERTICAL, command=self.data_tree.yview)
        h_scroll = ttk.Scrollbar(data_outer, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # ---- RIGHT ----
        right_frame = ttk.Frame(self.paned, width=650)
        self.paned.add(right_frame, weight=2)

        chart_lf = ttk.LabelFrame(right_frame, text="Biểu đồ", padding=5)
        chart_lf.pack(fill=tk.BOTH, expand=True)

        btn_bar = ttk.Frame(chart_lf)
        btn_bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(btn_bar, text="Tổng quan", command=self.plot_overview).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Events", command=self.plot_events).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Top Items", command=self.plot_top_items).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Popular", command=self.plot_popular_items).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Category", command=self.plot_categories).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Available", command=self.plot_availability).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Lưu", command=self.save_chart).pack(side=tk.RIGHT, padx=2)

        self.chart_frame = ttk.Frame(chart_lf)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        self._show_welcome()

    # ==================== STATUS BAR ====================
    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Sẵn sàng")
        bar = ttk.Frame(self.root)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(bar, textvariable=self.status_var,
                  relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, padx=2, pady=2)

    # ==================== HELPERS ====================
    def update_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _show_welcome(self):
        fig = Figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5,
                "Retailrocket Recommender\n— Redis Edition —\n\n"
                "1. Nhập Host / Port / DB\n"
                "2. Nhấn  Kết nối Redis\n"
                "3. Nhấn  Tải dữ liệu\n"
                "4. Chọn biểu đồ để phân tích",
                ha="center", va="center", fontsize=15, color="#555",
                transform=ax.transAxes)
        ax.set_axis_off()
        self._display_figure(fig)

    def _display_figure(self, fig):
        # Xóa sạch canvas và toolbar frame cũ
        if self.current_canvas:
            self.current_canvas.get_tk_widget().destroy()
            self.current_canvas = None
        if self.current_tb_frame:
            self.current_tb_frame.destroy()
            self.current_tb_frame = None
        self.current_toolbar = None

        # Tạo toolbar frame MỚI ở BOTTOM trước
        self.current_tb_frame = ttk.Frame(self.chart_frame)
        self.current_tb_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Tạo canvas mới
        self.current_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.current_canvas.draw()
        self.current_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Toolbar matplotlib bên trong tb_frame
        self.current_toolbar = NavigationToolbar2Tk(self.current_canvas, self.current_tb_frame)
        self.current_toolbar.update()

    def _require_data(self, key):
        if key not in self.loaded_data or self.loaded_data[key] is None or len(self.loaded_data[key]) == 0:
            messagebox.showwarning("Cảnh báo", f"Chưa có dữ liệu '{key}'. Hãy tải dữ liệu trước!")
            return False
        return True

    # ==================== REDIS ====================
    def connect_redis(self):
        self.update_status("Đang kết nối Redis…")
        self.root.config(cursor="wait")
        try:
            pwd = self.redis_password.get() or None
            self.loader = RedisDataLoader(
                host=self.redis_host.get(),
                port=self.redis_port.get(),
                db=self.redis_db.get(),
                password=pwd,
            )
            self.loader.connect()

            self.conn_label.config(text="● Đã kết nối", foreground="green")
            self.update_status("Kết nối Redis thành công!")

            # Hiển thị thông tin
            self._show_redis_info()

        except Exception as e:
            self.conn_label.config(text="● Lỗi kết nối", foreground="red")
            messagebox.showerror("Lỗi", f"Không thể kết nối Redis:\n{e}")
            self.update_status(f"Lỗi kết nối: {e}")
        finally:
            self.root.config(cursor="")

    def disconnect_redis(self):
        if self.loader:
            self.loader.disconnect()
        self.loader = None
        self.loaded_data = {}
        self.redis_stats = {}
        self.conn_label.config(text="● Chưa kết nối", foreground="red")
        self.update_status("Đã ngắt kết nối Redis.")
        self._show_welcome()

    def _show_redis_info(self):
        if not self.loader or not self.loader.is_connected():
            return
        self.info_text.delete("1.0", tk.END)
        info = self.loader.get_redis_info()
        self.info_text.insert(tk.END, "=== Redis Server ===\n")
        for k, v in info.items():
            self.info_text.insert(tk.END, f"  {k}: {v}\n")

        self.info_text.insert(tk.END, "\n--- Đang đếm keys… ---\n")
        self.root.update_idletasks()

        self.redis_stats = self.loader.get_stats()
        self.info_text.insert(tk.END, "\n=== Thống kê Keys ===\n")
        for k, v in self.redis_stats.items():
            self.info_text.insert(tk.END, f"  {k}: {v:,}\n")

    # ==================== LOAD DATA ====================
    def load_dataset(self, key):
        if not self.loader or not self.loader.is_connected():
            messagebox.showwarning("Cảnh báo", "Chưa kết nối Redis!")
            return
        self.update_status(f"Đang tải {key} từ Redis…")
        self.root.config(cursor="wait")
        try:
            max_u = self.max_users.get()
            if key == "events":
                self.loaded_data[key] = self.loader.load_events(max_users=max_u)
            elif key == "item_properties":
                self.loaded_data[key] = self.loader.load_item_properties()
            elif key == "category_tree":
                self.loaded_data[key] = self.loader.load_category_tree()
            elif key == "item_users":
                self.loaded_data[key] = self.loader.load_item_users()

            n = len(self.loaded_data[key])
            self.update_status(f"Đã tải {key}: {n:,} dòng")
            self._refresh_stats()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi tải {key}: {e}")
            self.update_status(f"Lỗi: {e}")
        finally:
            self.root.config(cursor="")

    def load_all_data(self):
        if not self.loader or not self.loader.is_connected():
            messagebox.showwarning("Cảnh báo", "Chưa kết nối Redis!")
            return
        self.update_status("Đang tải tất cả dữ liệu từ Redis…")
        self.root.config(cursor="wait")
        try:
            max_u = self.max_users.get()
            self.loaded_data = self.loader.load_all(max_users=max_u)
            total = sum(len(df) for df in self.loaded_data.values() if df is not None)
            self.update_status(f"Đã tải xong — tổng cộng {total:,} dòng")
            self._refresh_stats()
            messagebox.showinfo("Thành công", f"Đã tải {len(self.loaded_data)} datasets ({total:,} dòng)")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi tải dữ liệu: {e}")
            self.update_status(f"Lỗi: {e}")
        finally:
            self.root.config(cursor="")

    def _refresh_stats(self):
        self.stats_text.delete("1.0", tk.END)
        for key, df in self.loaded_data.items():
            if df is not None and len(df) > 0:
                self.stats_text.insert(tk.END, get_dataframe_summary(df, key) + "\n\n")

                if key == "events":
                    for k, v in analyze_events(df).items():
                        self.stats_text.insert(tk.END, f"  ► {k}: {v}\n")
                elif key == "category_tree":
                    for k, v in analyze_category_tree(df).items():
                        self.stats_text.insert(tk.END, f"  ► {k}: {v}\n")
                elif key == "item_properties":
                    for k, v in analyze_item_properties(df).items():
                        self.stats_text.insert(tk.END, f"  ► {k}: {v}\n")
                elif key == "item_users":
                    for k, v in analyze_item_users(df).items():
                        self.stats_text.insert(tk.END, f"  ► {k}: {v}\n")

                self.stats_text.insert(tk.END, "\n" + "=" * 55 + "\n\n")
        self.left_notebook.select(1)

    # ==================== DATA TABLE ====================
    def on_dataset_select(self, _event=None):
        key = self.ds_combo.get()
        if not key or key not in self.loaded_data:
            return
        df = self.loaded_data[key]
        if df is None or len(df) == 0:
            return
        self._display_dataframe(df)

    def _display_dataframe(self, df):
        self.data_tree.delete(*self.data_tree.get_children())
        cols = list(df.columns)
        self.data_tree["columns"] = cols
        for c in cols:
            self.data_tree.heading(c, text=c)
            self.data_tree.column(c, width=110, minwidth=70)
        limit = min(500, len(df))
        for i in range(limit):
            vals = [str(df.iloc[i][c]) for c in cols]
            self.data_tree.insert("", tk.END, values=vals)
        self.update_status(f"Hiển thị {limit}/{len(df)} dòng")

    # ==================== CHARTS ====================
    def plot_overview(self):
        if not self.redis_stats:
            if self.loader and self.loader.is_connected():
                self.redis_stats = self.loader.get_stats()
            else:
                messagebox.showwarning("Cảnh báo", "Chưa kết nối Redis!")
                return
        fig = plot_redis_overview(self.redis_stats)
        if fig:
            self._display_figure(fig)

    def plot_events(self):
        if not self._require_data("events"): return
        fig = plot_event_distribution(self.loaded_data["events"])
        if fig: self._display_figure(fig)

    def plot_top_items(self):
        if not self._require_data("events"): return
        fig = plot_top_items(self.loaded_data["events"])
        if fig: self._display_figure(fig)

    def plot_popular_items(self):
        if not self._require_data("item_users"): return
        fig = plot_popular_items_by_users(self.loaded_data["item_users"])
        if fig: self._display_figure(fig)

    def plot_categories(self):
        if not self._require_data("category_tree"): return
        fig = plot_category_tree(self.loaded_data["category_tree"])
        if fig: self._display_figure(fig)

    def plot_availability(self):
        if not self._require_data("item_properties"): return
        fig = plot_item_availability(self.loaded_data["item_properties"])
        if fig: self._display_figure(fig)

    def plot_distribution(self, key):
        if not self._require_data(key): return
        fig = plot_per_column_distribution(self.loaded_data[key])
        if fig: self._display_figure(fig)

    def plot_correlation(self, key):
        if not self._require_data(key): return
        fig = plot_correlation_matrix(self.loaded_data[key])
        if fig:
            self._display_figure(fig)
        else:
            messagebox.showinfo("Thông báo", "Không đủ cột số để vẽ tương quan")

    def save_chart(self):
        if not self.current_canvas:
            messagebox.showwarning("Cảnh báo", "Không có biểu đồ!")
            return
        fp = filedialog.asksaveasfilename(
            title="Lưu biểu đồ", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"),
                       ("SVG", "*.svg"), ("JPEG", "*.jpg")])
        if fp:
            self.current_canvas.figure.savefig(fp, bbox_inches="tight", dpi=150)
            self.update_status(f"Đã lưu: {fp}")

    # ==================== ABOUT ====================
    def show_about(self):
        messagebox.showinfo("Về ứng dụng",
            "Retailrocket Recommender System\n"
            "— Redis Edition —\n\n"
            "Phiên bản: 2.0.0\n\n"
            "Kết nối trực tiếp Redis Server\n"
            "để phân tích dữ liệu E-Commerce.\n\n"
            "Dữ liệu được import vào Redis bằng import.py,\n"
            "sau đó ứng dụng đọc từ Redis để phân tích.\n\n"
            "Nguồn: Kaggle — Retailrocket Dataset")


def main():
    root = tk.Tk()
    RetailrocketApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
