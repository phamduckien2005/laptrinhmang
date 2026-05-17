import csv
import os
from app import db, Book, app  # 🔥 tái sử dụng model Book và cấu hình Flask đã có

# =================== IMPORT CSV VÀO DATABASE =====================

def import_from_csv(csv_path="books_from_google.csv"):
    """Đọc file CSV và chèn vào database UniLib"""
    if not os.path.exists(csv_path):
        print(f"❌ Không tìm thấy file: {csv_path}")
        return

    with app.app_context():  # Đảm bảo có context của Flask
        added = 0
        skipped = 0

        with open(csv_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                title = row.get("title", "").strip()
                author = row.get("author", "").strip()
                description = row.get("description", "").strip()
                isbn = row.get("isbn", "").strip()
                image = row.get("image", "").strip()
                available = row.get("available", "True").strip().lower() in ["true", "1", "yes"]

                if not title or not author:
                    skipped += 1
                    continue

                # Tránh thêm trùng
                if Book.query.filter_by(title=title, author=author).first():
                    skipped += 1
                    continue

                # Tạo đối tượng Book
                book = Book(
                    title=title,
                    author=author,
                    description=description or "No description available.",
                    isbn=isbn or None,
                    image=image or None,
                    available=available
                )
                db.session.add(book)
                added += 1

            db.session.commit()

        print(f"✅ Đã import {added} sách mới vào database.")
        if skipped:
            print(f"⚠️ Bỏ qua {skipped} sách trùng hoặc thiếu dữ liệu.")

if __name__ == "__main__":
    csv_path = os.path.join(os.path.dirname(__file__), "books_from_google.csv")
    import_from_csv(csv_path)
