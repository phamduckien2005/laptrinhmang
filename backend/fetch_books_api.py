import requests
import csv
import time
import random
from datetime import datetime

# Cấu hình API (Chỉnh sửa ở đây)
API_KEY = 'AIzaSyCkR6xFNpyCQ4tdAcw3E1_8VrrT24XkLn8'  # Thay bằng key từ Bước 1 (AIzaSyB...xyz)
QUERY = 'AI books'  # Query tìm kiếm: "AI books" – thay bằng 'sách AI' hoặc 'library management books'
MAX_RESULTS_PER_PAGE = 40  # Số sách/trang (max của API)
TOTAL_BOOKS = 1000  # Mục tiêu lấy (nếu hit limit, lấy ít hơn)
OUTPUT_FILE = 'books_from_google.csv'  # File CSV xuất ra (trong backend/)

# Headers cho API (bắt buộc để tránh block)
headers = {
    'User-Agent': 'UniLib Project (hangbie995@gmail.com)'  # Thay email thật để tuân thủ Google policy
}

def fetch_books(start_index, num_results):
    """Lấy 1 trang sách từ Google Books API"""
    url = 'https://www.googleapis.com/books/v1/volumes'
    params = {
        'q': QUERY,
        'startIndex': start_index,
        'maxResults': num_results,
        'key': API_KEY,
        'projection': 'full',  # Lấy full metadata (title, authors, description, isbn)
        'langRestrict': 'en'  # Giới hạn tiếng Anh ('vi' cho tiếng Việt, nhưng kết quả ít)
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'error' in data:
            print(f"Lỗi API: {data['error']['message']}")
            return None
        return data
    else:
        print(f"Lỗi HTTP {response.status_code}: {response.text[:200]}...")  # In lỗi ngắn
        return None

def extract_book_info(volume):
    """Trích xuất metadata từ 1 volume (sách)"""
    info = volume.get('volumeInfo', {})
    title = info.get('title', 'Unknown Title').strip()[:200]  # Giới hạn title
    authors = ', '.join(info.get('authors', ['Unknown Author']))[:100]
    description = info.get('description', 'No description available.').strip()[:300]  # Giới hạn description cho AI search
    if len(description) > 0 and not description.endswith('.'):
        description += '.'  # Thêm dấu chấm nếu thiếu
    
    # ISBN (ưu tiên ISBN-13, nếu không dùng ISBN-10 hoặc fake)
    isbn = ''
    identifiers = info.get('industryIdentifiers', [])
    for iden in identifiers:
        if iden['type'] in ['ISBN_13', 'ISBN_10']:
            isbn = iden['identifier']
            break
    if not isbn:
        isbn = f"ISBN-{random.randint(1000000000, 9999999999)}"  # Fake ISBN unique
    
    # Kéo ảnh bìa từ API (thumbnail URL)
    image_url = info.get('imageLinks', {}).get('thumbnail', '')  # URL ảnh bìa từ Google Books API
    
    available = random.choice([True, False])  # Random true/false cho available (có sẵn/đã mượn)
    
    return {
        'title': title,
        'author': authors,
        'description': description,
        'isbn': isbn,
        'image': image_url,  # Thêm URL ảnh bìa từ API
        'available': available
    }

# Main script: Lấy dữ liệu phân trang
print(f"Bắt đầu lấy dữ liệu sách với query '{QUERY}'...")
print(f"Mục tiêu: {TOTAL_BOOKS} sách. Rate limit: 1000 query/ngày.")
print(f"API Key: {'OK' if API_KEY != 'YOUR_API_KEY_HERE' else 'CẢNH BÁO: Thay API_KEY trước khi chạy!'}")

all_books = []
start_index = 0
page_count = 0
while len(all_books) < TOTAL_BOOKS:
    print(f"\n--- Trang {page_count + 1} --- Đang lấy từ index {start_index}... (Đã có {len(all_books)} sách)")
    
    data = fetch_books(start_index, MAX_RESULTS_PER_PAGE)
    if not data or 'items' not in data:
        print("Không có dữ liệu nữa hoặc lỗi API. Dừng lấy.")
        break
    
    page_books = data['items']
    if not page_books:
        print("Trang rỗng – có lẽ hết kết quả.")
        break
    
    for i, volume in enumerate(page_books, 1):
        book_info = extract_book_info(volume)
        all_books.append(book_info)
        print(f"  + Sách {len(all_books)}: {book_info['title'][:50]}...")
        
        if len(all_books) >= TOTAL_BOOKS:
            print(f"Đã đạt mục tiêu {TOTAL_BOOKS} sách!")
            break
    
    start_index += MAX_RESULTS_PER_PAGE
    page_count += 1
    
    # Kiểm tra total items từ API (nếu hết)
    total_items = data.get('totalItems', 0)
    if start_index >= total_items:
        print(f"Đã lấy hết {total_items} kết quả từ API.")
        break
    
    # Delay để tránh rate limit (0.2s/query – an toàn cho 1000/ngày)
    time.sleep(0.2)
    
    # Kiểm tra nếu hit quota (API trả error)
    if 'error' in data and 'quotaExceeded' in str(data['error']).lower():
        print("Cảnh báo: Hit rate limit (1000 query/ngày). Dừng và chờ 24h.")
        break

# Xuất ra CSV nếu có dữ liệu
if all_books:
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['title', 'author', 'description', 'isbn', 'image', 'available']  # Thêm 'image' vào fieldnames
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_books)
    
    print(f"\n🎉 Thành công! Đã lấy {len(all_books)} sách và xuất vào '{OUTPUT_FILE}'.")
    print(f"File CSV: {OUTPUT_FILE} (cột: title, author, description, isbn, image, available).")
    print(f"Số trang lấy: {page_count}. Total query: {page_count} (dưới limit nếu <1000).")
else:
    print("\n❌ Không lấy được sách nào. Kiểm tra:")
    print("- API_KEY đúng chưa? (Thay 'YOUR_API_KEY_HERE').")
    print("- QUERY hợp lệ? (Thử 'programming books' nếu 'AI books' ít kết quả).")
    print("- Rate limit? Chờ 24h hoặc tạo project mới.")
    print("- Internet ổn định? Thử query nhỏ: TOTAL_BOOKS=100.")

# In 5 sách mẫu để kiểm tra
print("\n📚 5 sách mẫu lấy được:")
for i, book in enumerate(all_books[:5], 1):
    status = "Có sẵn" if book['available'] else "Đã mượn"
    print(f"{i}. {book['title']} bởi {book['author']}")
    print(f"   Mô tả: {book['description'][:100]}...")
    print(f"   ISBN: {book['isbn']} | Ảnh: {book['image'] or 'Không có'} | Trạng thái: {status}\n")

# Lưu thời gian chạy
end_time = datetime.now()
print(f"Hoàn thành lúc: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")