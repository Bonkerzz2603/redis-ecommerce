# Retailrocket Recommender System — Redis Edition

## Giới thiệu

Ứng dụng phân tích dữ liệu E-Commerce từ dataset **Retailrocket** (Kaggle),
sử dụng **Redis Server** làm nguồn dữ liệu chính.

Dữ liệu CSV được import vào Redis một lần bằng `import.py`,
sau đó ứng dụng GUI đọc trực tiếp từ Redis để phân tích & trực quan hóa.

## Cấu trúc Project

```
redis-ecommerce-redis-project/
├── main.py                 # Entry point – khởi chạy GUI
├── import.py               # Script import CSV → Redis
├── requirements.txt        # Dependencies
├── README.md               # Tài liệu hướng dẫn
├── generate_docs.py        # Script tạo tài liệu DOCX
├── src/                    # Mã nguồn chính
│   ├── __init__.py
│   ├── data_loader.py      # Kết nối Redis & tải dữ liệu → DataFrame
│   ├── analysis.py         # Phân tích thống kê
│   ├── visualization.py    # Trực quan hóa (matplotlib)
│   └── gui.py              # Giao diện đồ họa (tkinter)
├── data/                   # (tùy chọn) chứa CSV gốc
├── output/                 # Biểu đồ / báo cáo xuất ra
└── *.ipynb                 # Notebook gốc (tham khảo)
```

## Cấu trúc dữ liệu trong Redis

| Key pattern              | Kiểu    | Mô tả |
|--------------------------|---------|-------|
| `user:{id}:events`       | LIST    | Danh sách JSON `{itemid, event, timestamp}` |
| `item:{id}:users`        | SET     | Tập visitor IDs đã tương tác với item |
| `item:{id}:props`        | HASH    | `{categoryid, available}` |
| `category:{id}`          | HASH    | `{parent}` (-1 nếu root) |

## Yêu cầu

- Python 3.8+
- **Redis Server** đang chạy (localhost:6379 mặc định)
- Các thư viện: xem `requirements.txt`

## Cài đặt & Chạy

### 1. Cài dependencies

```bash
pip install -r requirements.txt
```

### 2. Khởi động Redis Server

```bash
# Windows (dùng Redis cho Windows hoặc WSL)
redis-server

# Kiểm tra
redis-cli ping
# → PONG
```

### 3. Import dữ liệu CSV vào Redis

Sửa đường dẫn file CSV trong `import.py`, sau đó chạy:

```bash
python import.py
```

Script sẽ import 4 file:
- `events.csv`
- `item_properties_part1.csv`
- `item_properties_part2.csv`
- `category_tree.csv`

### 4. Chạy ứng dụng GUI

```bash
python main.py
```

## Hướng dẫn sử dụng GUI

1. **Kết nối Redis**: Nhập Host/Port/DB → Click "Kết nối Redis"
2. **Tải dữ liệu**: Click "Tải dữ liệu" (hoặc menu Dữ liệu → Tải tất cả)
3. **Xem thống kê**: Tab "Redis" (thông tin server) + Tab "Thống kê" (phân tích)
4. **Xem bảng dữ liệu**: Tab "Dữ liệu" → chọn dataset từ dropdown
5. **Vẽ biểu đồ**: Sử dụng nút trên toolbar hoặc menu "Biểu đồ"
6. **Lưu biểu đồ**: Click "Lưu" → chọn định dạng PNG/PDF/SVG

## Các loại biểu đồ

| Biểu đồ | Dữ liệu Redis |
|----------|----------------|
| Tổng quan Redis | Thống kê keys |
| Phân bổ Event | `user:*:events` |
| Top Items (events) | `user:*:events` |
| Items phổ biến (users) | `item:*:users` |
| Category Tree | `category:*` |
| Item Availability | `item:*:props` |

## License

MIT License
# redis-ecommerce
