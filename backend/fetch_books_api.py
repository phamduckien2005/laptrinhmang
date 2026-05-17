import requests
import time
import random
from datetime import datetime
from app import db, Book, app

# ===================== CẤU HÌNH =====================
API_KEY = "AIzaSyCkR6xFNpyCQ4tdAcw3E1_8VrrT24XkLn8"
MAX_RESULTS = 40
TOTAL_BOOKS_TARGET = 3000
WAIT_TIME = 0.3  # tạm nghỉ giữa các request
QUERIES = [
    # AI & Machine Learning
    "Artificial Intelligence", "AI books", "Deep Learning", "Machine Learning",
    "Neural Networks", "Data Science", "Computer Vision", "NLP", "Reinforcement Learning",

    # Programming & Software
    "Python programming", "JavaScript programming", "C++ programming", "Web Development",
    "Algorithms", "Data Structures", "Software Engineering", "Programming Design Patterns",

    # Cloud & Database
    "Cloud computing", "AWS", "Azure", "Google Cloud", "SQL", "NoSQL", "Database systems",

    # IoT & Robotics
    "Internet of Things", "IoT Sensors", "Embedded Systems", "Robotics", "Automation",

    # Misc & Science
    "Cybersecurity", "Quantum computing", "Bioinformatics", "Mathematics", "Physics", "Chemistry"
]


# ===================== HÀM LẤY DỮ LIỆU =====================
def fetch_books_from_google(query, start_index):
    """Gọi API Google Books"""
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "startIndex": start_index,
        "maxResults": MAX_RESULTS,
        "projection": "full",
        "langRestrict": "en",
        "key": API_KEY
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        print(f"⚠️ Lỗi {r.status_code}: {r.text[:100]}")
        return []
    data = r.json()
    return data.get("items", [])

def extract_book_info(item):
    """Trích xuất thông tin cần thiết"""
    info = item.get("volumeInfo", {})
    title = info.get("title", "Unknown Title")[:200]
    authors = ", ".join(info.get("authors", ["Unknown Author"]))[:100]
    description = info.get("description", "No description available.")[:500]
    isbn = None
    for i in info.get("industryIdentifiers", []):
        if i["type"] in ("ISBN_10", "ISBN_13"):
            isbn = i["identifier"]
            break
    if not isbn:
        isbn = f"ISBN-{random.randint(1000000000,9999999999)}"
    image = info.get("imageLinks", {}).get("thumbnail", "")
    preview_link = info.get("previewLink", "")
    available = random.choice([True, False])
    return dict(
        title=title, author=authors, description=description,
        isbn=isbn, image=image, available=available,
        file_path=preview_link
    )

# ===================== CHẠY CHƯƠNG TRÌNH =====================
if __name__ == "__main__":
    print("📘 Database initialized at:", app.config["SQLALCHEMY_DATABASE_URI"])
    total_added = 0
    seen = set()

    with app.app_context():
        for query in QUERIES:
            print(f"\n🔎 Đang lấy sách chủ đề: {query}")
            start_index = 0

            while total_added < TOTAL_BOOKS_TARGET:
                items = fetch_books_from_google(query, start_index)
                if not items:
                    print("❌ Hết kết quả hoặc lỗi API.")
                    break

                added_now = 0
                for item in items:
                    info = extract_book_info(item)
                    key = (info["title"], info["author"])
                    if key in seen:
                        continue
                    seen.add(key)

                    # Kiểm tra trùng trong DB
                    if not Book.query.filter_by(title=info["title"], author=info["author"]).first():
                        book = Book(**info)
                        db.session.add(book)
                        added_now += 1
                        total_added += 1

                    if total_added >= TOTAL_BOOKS_TARGET:
                        break

                db.session.commit()
                print(f"✅ Đã thêm {added_now} sách... (Tổng: {total_added})")
                if added_now == 0:
                    break

                start_index += MAX_RESULTS
                time.sleep(WAIT_TIME)

                if total_added >= TOTAL_BOOKS_TARGET:
                    break

        print(f"\n🎉 Hoàn tất! Tổng số: {total_added} sách.")
        print("🕒 Kết thúc lúc:", datetime.now().strftime("%H:%M:%S"))
