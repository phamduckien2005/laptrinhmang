import csv
from app import app, db, Book  # Import app để tạo context

CSV_FILE = 'books_from_google.csv'  # File CSV từ script lấy sách

# Tạo application context để sử dụng db.session
with app.app_context():
    # Xóa DB cũ nếu cần (comment nếu giữ dữ liệu cũ)
    Book.query.delete()
    db.session.commit()

    imported = 0
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['title'] == 'title': continue  # Skip header
            book = Book(
                title=row['title'][:200],  # Giới hạn length để tránh DB error
                author=row['author'][:100],
                description=row['description'][:500],
                isbn=row['isbn'],
                available=row['available'].lower() == 'true'
            )
            db.session.add(book)
            imported += 1
            if imported % 100 == 0:
                db.session.commit()
                print(f"Imported {imported} books...")
    db.session.commit()
    print(f"✅ Imported {imported} books into unilib.db!")

    # Test DB trong context
    books = Book.query.limit(5).all()
    print("\n5 sách mẫu trong DB:")
    for b in books:
        print(f"- {b.title} by {b.author} (Available: {b.available}) | Created: {b.created_at}")