# Sau Tuần 4 | Sao lưu online và xác minh SQLite trước khi công bố bản sao.

"""Create a verified SQLite snapshot at a new path using the online backup API."""

import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile

from src import db


def backup_database(destination: Path) -> Path:
    source = db.DB_PATH.resolve()
    destination = destination.expanduser().absolute()
    if not source.is_file():
        raise FileNotFoundError(f"Database not found: {source}")
    # Kiểm tra cả symlink đã hỏng để bảo vệ mọi tên file đích đã tồn tại.
    if os.path.lexists(destination):
        raise FileExistsError(f"Backup destination already exists: {destination}")

    # Đặt file tạm cùng thư mục đích để công bố trong cùng filesystem.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        prefix=".helpdesk-backup-", suffix=".db", dir=destination.parent, delete=False
    ) as temporary:
        snapshot = Path(temporary.name)

    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(snapshot)) as copy:
                # SQLite tạo snapshot nhất quán kể cả khi ứng dụng đang truy cập DB.
                original.backup(copy)
                if copy.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                    raise RuntimeError("The backup database did not pass SQLite quick_check.")
        # Chỉ công bố sau quick_check. rename trên Windows và link trên POSIX
        # đều giữ nguyên file đích nếu có tiến trình khác tạo đích trước.
        if os.name == "nt":
            snapshot.rename(destination)
        else:
            os.link(snapshot, destination)
    finally:
        # Dọn bản tạm cả khi sao lưu hoặc kiểm tra thất bại.
        snapshot.unlink(missing_ok=True)

    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="Path for the new .db snapshot")
    print(f"Backup saved to {backup_database(parser.parse_args().destination)}")


if __name__ == "__main__":
    main()
