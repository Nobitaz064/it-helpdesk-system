# Tuần 2 | Tạo kết nối SQLite dùng chung cho service và dashboard.

import os
import sqlite3
from pathlib import Path

# Dựa vào đường dẫn file để chạy được từ thư mục làm việc khác.
BASE_DIR = Path(__file__).resolve().parent.parent
# Sau Tuần 4 | HELPDESK_DB_PATH chọn DB cho demo, pilot, test hoặc bản khôi phục.
configured_path = os.environ.get("HELPDESK_DB_PATH")
DB_PATH = (
    Path(configured_path).expanduser().resolve()
    if configured_path
    else BASE_DIR / "database" / "helpdesk.db"
)


# Kiểm tra file trước khi kết nối vì sqlite3.connect() tự tạo file rỗng nếu đường dẫn chưa có.
def get_connection():
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)
    # SQLite cần bật kiểm tra khóa ngoại trên từng kết nối. Bỏ dòng này thì SQLite có thể
    # chấp nhận liên kết tới user hoặc danh mục không tồn tại.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Tuần 2 | Chạy trực tiếp để kiểm tra đường dẫn, bảng, khóa ngoại và dữ liệu mẫu.
if __name__ == "__main__":
    conn = get_connection()

    try:
        required = {
            "USERS",
            "CATEGORIES",
            "TICKETS",
            "TICKET_HISTORY"
        }

        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }

        if not required.issubset(tables):
            raise RuntimeError(
                f"Missing tables: {required - tables}"
            )

        print("Connection: OK")
        print("Database:", DB_PATH)
        print("Tables:", ", ".join(sorted(required)))

        print(
            "Foreign keys:",
            conn.execute("PRAGMA foreign_keys").fetchone()[0]
        )

        ticket = conn.execute(
            "SELECT TICKET_ID, STATUS FROM TICKETS "
            "WHERE TICKET_ID = ?",
            (1,)
        ).fetchone()

        print("Ticket #1:", ticket)

        count = conn.execute(
            "SELECT COUNT(*) FROM TICKET_HISTORY "
            "WHERE TICKET_ID = ?",
            (1,)
        ).fetchone()[0]

        print("History count:", count)

    finally:
        conn.close()
