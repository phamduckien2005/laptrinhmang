import os
import time
import subprocess
from datetime import datetime
from app import db, Book

# =================== CONFIG =====================
BASE_DIR = os.path.dirname(__file__)
FETCH_SCRIPT = os.path.join(BASE_DIR, "fetch_books_api.py")
IMPORT_SCRIPT = os.path.join(BASE_DIR, "import_google_csv.py")
CSV_PATH = os.path.join(BASE_DIR, "books_from_google.csv")

# =================== MAIN SCRIPT =====================
def run_command(cmd):
    """Chạy lệnh Python phụ và hiển thị log realtime"""
    process = subprocess.Popen(
        cmd, shell=True, cwd=BASE_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(line.strip())
    return process.returncode

def main():
    print("="*60)
    print("📚 BẮT ĐẦU QUY TRÌNH CẬP NHẬT SÁCH UNI-LIB")
    print("="*60)
    start_time = time.time()

    # ----------- Bước 1: Lấy dữ liệu từ Google Books API -----------
    print("\n🚀 [1/2] Đang chạy fetch_books_api.py ...")
    ret1 = run_command(f"python {FETCH_SCRIPT}")
    if ret1 != 0:
        print("❌ Lỗi khi chạy fetch_books_api.py. Dừng quy trình.")
        return

    # Kiểm tra file CSV có tồn tại không
    if not os.path.exists(CSV_PATH):
        print(f"❌ Không tìm thấy file {CSV_PATH}. Kiểm tra lại script fetch_books_api.py")
        return

    # ----------- Bước 2: Nhập dữ liệu CSV vào database -----------
    print("\n📥 [2/2] Đang import dữ liệu vào database ...")
    ret2 = run_command(f"python {IMPORT_SCRIPT}")
    if ret2 != 0:
        print("⚠️ Lỗi khi chạy import_google_csv.py, nhưng có thể một phần dữ liệu đã được thêm.")

    # ----------- Tổng kết -----------
    with db.session.begin():
        total_books = Book.query.count()

    end_time = time.time()
    elapsed = end_time - start_time
    print("\n✅ Hoàn thành cập nhật UniLib!")
    print(f"📚 Tổng số sách hiện có trong hệ thống: {total_books}")
    print(f"⏱️ Thời gian chạy: {elapsed:.2f} giây")
    print("="*60)

if __name__ == "__main__":
    main()
