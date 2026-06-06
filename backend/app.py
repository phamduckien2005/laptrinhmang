import os
import sys
# Fix UnicodeEncodeError trên Windows terminal (CP1252 không hiểu tiếng Việt)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from flask import Flask, jsonify, request, send_from_directory, make_response, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
import requests
from urllib.parse import quote_plus
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
load_dotenv(os.path.join(current_dir, ".env"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "45"))

def ask_ollama(message):
    """Call local Ollama for natural chatbot replies."""
    system_prompt = (
        "Bạn là Trợ lý AI UniLib, chatbot hỗ trợ người dùng trong hệ thống "
        "thư viện UniLib. Luôn trả lời bằng tiếng Việt, thân thiện, ngắn gọn "
        "và tự nhiên. Khi người dùng hỏi bạn là ai, hãy tự giới thiệu là trợ "
        "lý AI của UniLib, không tự giới thiệu là model của Meta/Ollama. Bạn "
        "không được tự nhận UniLib là lớn nhất, tốt nhất hoặc thêm thông tin "
        "quảng bá không có trong hệ thống. "
        "có thể chào hỏi, trò chuyện cơ bản và hướng dẫn người dùng hỏi về "
        "thư viện, tìm sách, mượn sách, trả sách. Ngữ cảnh hệ thống UniLib: "
        "người dùng có thể đăng ký, đăng nhập, tìm sách, xem chi tiết sách, "
        "bấm nút Mượn sách, chọn thời hạn mượn từ 1 đến 90 ngày, xem danh "
        "sách sách đang mượn và bấm Trả sách. Không gọi thao tác mượn là mua. "
        "Không tự bịa mức phạt, lịch mở cửa, điều khoản, chính sách hoặc "
        "thông tin tổ chức nếu chưa chắc; hãy hướng dẫn người dùng kiểm tra "
        "với thủ thư hoặc dùng chức năng trên hệ thống UniLib."
    )
    user_prompt = (
        "Hãy trả lời người dùng với đúng vai trò Trợ lý AI UniLib.\n"
        f"Câu hỏi của người dùng: {message}"
    )

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "options": {
                    "temperature": 0.7,
                    "num_predict": 220,
                },
            },
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        reply = (data.get("message") or {}).get("content") or data.get("response")
        return reply.strip() if reply else None
    except requests.RequestException as exc:
        print(f"Ollama request failed: {exc}")
        return None
    except ValueError as exc:
        print(f"Ollama response is not valid JSON: {exc}")
        return None

# ===================== FLASK SETUP =====================
app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = "super_secret_key"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

# ===================== CORS HEADERS =====================
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5500'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route("/<path:path>", methods=["OPTIONS"])
@app.route("/", methods=["OPTIONS"])
def options_handler(path=None):
    return '', 200

# ===================== DATABASE SETUP =====================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

DB_PATH = os.path.join(INSTANCE_DIR, "data.db")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    DB_USER = os.getenv("MYSQL_USER", "root")
    DB_PASSWORD = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    DB_PORT = os.getenv("MYSQL_PORT", "3306")
    DB_NAME = os.getenv("MYSQL_DATABASE", "unilib")
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ===================== MODEL =====================
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_book_id = db.Column(db.String(100))
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    description = db.Column(db.Text)
    isbn = db.Column(db.String(100))
    image = db.Column(db.String(500))
    available = db.Column(db.Boolean, default=True)
    file_path = db.Column(db.String(500))
    quantity = db.Column(db.Integer, default=1)
    shelf_location = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    role = db.Column(db.String(50), default="user")
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class BorrowRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    borrow_date = db.Column(db.DateTime, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    return_date = db.Column(db.DateTime, nullable=True)
    returned = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(30), default="pending")
    reject_reason = db.Column(db.String(255))
    fine_amount = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref='borrow_records')
    book = db.relationship('Book', backref='borrow_records')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(255))

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    rating = db.Column(db.Integer, default=5)
    comment = db.Column(db.Text)
    hidden = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='reviews')
    book = db.relationship('Book', backref='reviews')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default="general")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ViolationReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=True)
    report_type = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(30), default="open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='violation_reports')
    book = db.relationship('Book', backref='violation_reports')

# ===================== INIT DATABASE =====================
with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)

    def add_column_if_missing(table_name, existing_columns, column_name, column_sql):
        if column_name not in existing_columns:
            with db.engine.begin() as connection:
                connection.exec_driver_sql(f"ALTER TABLE `{table_name}` ADD COLUMN {column_sql}")

    user_columns = [column["name"] for column in inspector.get_columns("user")]
    add_column_if_missing("user", user_columns, "email", "email VARCHAR(255)")
    add_column_if_missing("user", user_columns, "full_name", "full_name VARCHAR(255)")
    add_column_if_missing("user", user_columns, "role", "role VARCHAR(50) DEFAULT 'user'")
    add_column_if_missing("user", user_columns, "is_locked", "is_locked BOOLEAN DEFAULT 0")
    add_column_if_missing("user", user_columns, "created_at", "created_at DATETIME")

    book_columns = [column["name"] for column in inspector.get_columns("book")]
    add_column_if_missing("book", book_columns, "google_book_id", "google_book_id VARCHAR(100)")
    add_column_if_missing("book", book_columns, "quantity", "quantity INTEGER DEFAULT 1")
    add_column_if_missing("book", book_columns, "shelf_location", "shelf_location VARCHAR(100)")
    add_column_if_missing("book", book_columns, "category_id", "category_id INTEGER")

    borrow_columns = [column["name"] for column in inspector.get_columns("borrow_record")]
    add_column_if_missing("borrow_record", borrow_columns, "request_date", "request_date DATETIME")
    add_column_if_missing("borrow_record", borrow_columns, "due_date", "due_date DATETIME")
    add_column_if_missing("borrow_record", borrow_columns, "status", "status VARCHAR(30) DEFAULT 'approved'")
    add_column_if_missing("borrow_record", borrow_columns, "reject_reason", "reject_reason VARCHAR(255)")
    add_column_if_missing("borrow_record", borrow_columns, "fine_amount", "fine_amount INTEGER DEFAULT 0")

    default_categories = ["CNTT", "Kinh tế", "Marketing", "Ngoại ngữ", "Tiểu thuyết"]
    for category_name in default_categories:
        if not Category.query.filter_by(name=category_name).first():
            db.session.add(Category(name=category_name))
    db.session.commit()
    print(f" Database initialized at: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")

# ===================== AUTH API =====================
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    full_name = data.get('full_name') or username
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Thiếu tên đăng nhập hoặc mật khẩu!"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Tên người dùng đã tồn tại!"}), 400

    if email and User.query.filter_by(email=email).first():
        return jsonify({"message": "Email da ton tai!"}), 400

    role = "super_admin" if username.lower() == "admin" else "user"
    new_user = User(username=username, email=email, full_name=full_name, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "Đăng ký thành công!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"status": "error", "message": "Tài khoản không tồn tại!"}), 401

    if user.is_locked:
        return jsonify({"status": "error", "message": "Tai khoan da bi khoa!"}), 403

    if user.check_password(password):
        session["user_id"] = user.id
        session["username"] = username
        session["role"] = user.role or "user"
        return jsonify({
            "status": "success", 
            "message": "Đăng nhập thành công!", 
            "user_id": user.id,
            "username": username,
            "role": session["role"]
        }), 200
    else:
        return jsonify({"status": "error", "message": "Sai mật khẩu!"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("role", None)
    return jsonify({"status": "success", "message": "Đã đăng xuất"})

@app.route("/check-auth", methods=["GET"])
def check_auth():
    if "user_id" in session:
        return jsonify({
            "status": "success",
            "user_id": session["user_id"],
            "username": session.get("username", ""),
            "role": session.get("role", "user")
        })
    return jsonify({"status": "error"}), 401
#forgot password
@app.route('/simple-reset', methods=['POST'])
def simple_reset():
    data = request.get_json()
    email = data.get('email')
    new_password = data.get('new_password')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"status": "error", "message": "Email không tồn tại"}), 400
    
    # Có thể thêm xác minh OTP đơn giản
    if len(new_password) < 6:
        return jsonify({"status": "error", "message": "Mật khẩu phải có ít nhất 6 ký tự"}), 400
    
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({
        "status": "success", 
        "message": "Đặt lại mật khẩu thành công"
    })
# ===================== BOOKS API =====================
@app.route("/borrow", methods=["POST"])
def borrow_book():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401

    user_id = session["user_id"]
    data = request.get_json()
    try:
        borrow_days = int(data.get("borrow_days", 30))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Thời hạn mượn không hợp lệ"}), 400

    if borrow_days < 1 or borrow_days > 90:
        return jsonify({"status": "error", "message": "Thời hạn mượn phải từ 1 đến 90 ngày"}), 400

    book_id = data.get("book_id")
    if book_id:
        book = db.session.get(Book, book_id)
        if not book or (book.quantity or 1) <= 0:
            return jsonify({"status": "error", "message": "Sách không khả dụng"}), 400
    else:
        title = data.get("title")
        author = data.get("author")
        image = data.get("image")
        isbn = data.get("isbn")
        description = data.get("description")
        preview_link = data.get("preview_link")

        if not title or not author:
            return jsonify({"status": "error", "message": "Thiếu thông tin sách"}), 400

        book = Book.query.filter_by(isbn=isbn).first() if isbn else None
        if not book:
            book = Book.query.filter_by(title=title, author=author).first()
        
        if not book:
            book = Book(
                title=title,
                author=author,
                description=description or "",
                image=image,
                isbn=isbn,
                file_path=preview_link,
                available=True
            )
            db.session.add(book)
            db.session.commit()
        elif (book.quantity or 1) <= 0:
            return jsonify({"status": "error", "message": "Sách đang được mượn"}), 400
        else:
            if description and not book.description:
                book.description = description
            if preview_link and not book.file_path:
                book.file_path = preview_link

    existing = BorrowRecord.query.filter(
        BorrowRecord.user_id == user_id,
        BorrowRecord.book_id == book.id,
        BorrowRecord.status.in_(["pending", "approved", "return_pending"]),
        BorrowRecord.returned == False
    ).first()
    if existing:
        return jsonify({"status": "error", "message": "Bạn đã mượn sách này rồi!"}), 400

    now = datetime.utcnow()
    borrow = BorrowRecord(
        user_id=user_id,
        book_id=book.id,
        request_date=now,
        borrow_date=now,
        due_date=now + timedelta(days=borrow_days),
        status="pending"
    )
    db.session.add(borrow)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Mượn sách thành công!",
        "book_id": book.id,
        "borrow_id": borrow.id,
        "due_date": borrow.due_date.isoformat(),
        "borrow_days": borrow_days,
        "borrow_status": borrow.status
    })

@app.route("/return", methods=["POST"])
def return_book():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401

    data = request.get_json()
    book_id = data.get("book_id")

    try:
        book_id = int(book_id)
    except:
        return jsonify({"status": "error", "message": "book_id không hợp lệ"}), 400

    record = BorrowRecord.query.filter_by(
        user_id=session["user_id"], 
        book_id=book_id, 
        returned=False,
        status="approved"
    ).first()

    if not record:
        return jsonify({"status": "error", "message": "Không tìm thấy sách đã mượn"}), 400

    record.status = "return_pending"

    db.session.commit()
    return jsonify({"status": "success", "message": "Trả sách thành công!"}), 200

@app.route("/api/user/borrowed-count", methods=["GET"])
def get_borrowed_count():
    if "user_id" not in session:
        return jsonify({"count": 0})
    
    user_id = session["user_id"]
    count = BorrowRecord.query.filter_by(user_id=user_id, returned=False, status="approved").count()
    return jsonify({"count": count})

@app.route("/api/user/borrowed-books", methods=["GET"])
def get_borrowed_books():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    
    user_id = session["user_id"]
    
    records = BorrowRecord.query.filter_by(
        user_id=user_id, 
        returned=False,
        status="approved"
    ).join(Book, BorrowRecord.book_id == Book.id).all()
    
    borrowed_books = []
    now = datetime.utcnow()
    for record in records:
        due_date = record.due_date or (record.borrow_date + timedelta(days=30) if record.borrow_date else None)
        remaining_days = None
        if due_date:
            remaining_days = max(0, (due_date.date() - now.date()).days)

        borrowed_books.append({
            "book_id": record.book.id,
            "title": record.book.title,
            "author": record.book.author,
            "image": record.book.image,
            "description": record.book.description or "",
            "preview_link": record.book.file_path or "",
            "borrow_date": record.borrow_date.isoformat() if record.borrow_date else None,
            "due_date": due_date.isoformat() if due_date else None,
            "remaining_days": remaining_days,
            "overdue": bool(due_date and due_date < now),
            "borrow_id": record.id
        })
    
    return jsonify({
        "status": "success",
        "books": borrowed_books
    })
#quenmk
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Reset password - simple version for small project"""
    data = request.get_json()
    username = data.get('username')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    # Basic validation
    if not username or not new_password or not confirm_password:
        return jsonify({
            "status": "error", 
            "message": "Vui lòng nhập đầy đủ thông tin"
        }), 400
    
    if new_password != confirm_password:
        return jsonify({
            "status": "error", 
            "message": "Mật khẩu mới không khớp"
        }), 400
    
    if len(new_password) < 6:
        return jsonify({
            "status": "error", 
            "message": "Mật khẩu phải có ít nhất 6 ký tự"
        }), 400
    
    # Find user
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({
            "status": "error", 
            "message": "Tên đăng nhập không tồn tại"
        }), 400
    
    # Change password
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({
        "status": "success", 
        "message": "Đã đổi mật khẩu thành công! Vui lòng đăng nhập lại."
    })

#CHATBOT

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message is required"}), 400

    ollama_reply = ask_ollama(message)
    if ollama_reply:
        return jsonify({
            "reply": ollama_reply,
            "source": "ollama",
            "model": OLLAMA_MODEL,
            "confidence": 1.0
        })

    return jsonify({
        "reply": "Xin lỗi, hiện tại mình chưa kết nối được Ollama. Bạn hãy kiểm tra Ollama đang chạy bằng lệnh `ollama serve` và model `llama3.2:1b` đã được tải.",
        "source": "ollama_unavailable",
        "model": OLLAMA_MODEL,
        "confidence": 0.0
    }), 503
# ===================== BOOKS SEARCH API =====================
def normalize_google_book(item):
    info = item.get("volumeInfo", {})
    identifiers = info.get("industryIdentifiers", []) or []
    isbn = ""
    for identifier in identifiers:
        if identifier.get("type") in ("ISBN_13", "ISBN_10"):
            isbn = identifier.get("identifier", "")
            break

    image_links = info.get("imageLinks", {}) or {}
    image = image_links.get("thumbnail") or image_links.get("smallThumbnail") or ""
    if image.startswith("http://"):
        image = "https://" + image[len("http://"):]

    authors = info.get("authors") or []
    return {
        "google_id": item.get("id", ""),
        "title": info.get("title") or "Không có tiêu đề",
        "author": ", ".join(authors) if authors else "Không rõ tác giả",
        "description": info.get("description") or "Không có mô tả chi tiết cho cuốn sách này.",
        "isbn": isbn,
        "image": image,
        "preview_link": info.get("previewLink") or info.get("infoLink") or "",
        "publisher": info.get("publisher") or "",
        "published_date": info.get("publishedDate") or "",
        "available": True,
        "source": "google",
    }

@app.route("/api/books/google-search", methods=["GET"])
def search_google_books():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"status": "error", "message": "Thiếu từ khóa tìm kiếm"}), 400

    try:
        max_results = min(max(int(request.args.get("max_results", 40)), 1), 40)
    except ValueError:
        max_results = 40

    params = {
        "q": keyword,
        "maxResults": max_results,
        "printType": "books",
        "projection": "full",
        "langRestrict": request.args.get("lang", "vi"),
    }
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()
    if api_key and not api_key.lower().startswith(("your_", "paste_", "AIzaSy...".lower())):
        params["key"] = api_key

    try:
        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params=params,
            timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return jsonify({
            "status": "error",
            "message": "Không gọi được Google Books API",
            "detail": str(exc)
        }), 502

    data = response.json()
    books = [normalize_google_book(item) for item in data.get("items", [])]
    return jsonify({
        "status": "success",
        "source": "google",
        "total": len(books),
        "books": books
    })

@app.route("/api/books/search", methods=["GET"])
def search_books():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"status": "error", "message": "Thiếu từ khóa tìm kiếm"}), 400

    # Tìm kiếm theo title HOẶC author, không phân biệt hoa thường
    pattern = f"%{keyword}%"
    books = Book.query.filter(
        db.or_(
            Book.title.ilike(pattern),
            Book.author.ilike(pattern),
            Book.description.ilike(pattern),
            Book.isbn.ilike(pattern)
        )
    ).limit(40).all()

    result = []
    for b in books:
        result.append({
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "description": b.description or "",
            "isbn": b.isbn or "",
            "image": b.image or "",
            "preview_link": b.file_path or "",
            "available": b.available,
        })

    return jsonify({"status": "success", "total": len(result), "books": result})

# ===================== ADMIN API =====================
ADMIN_ROLES = {"super_admin", "admin", "librarian"}

def is_admin_user():
    user_id = session.get("user_id")
    if not user_id:
        return False
    user = db.session.get(User, user_id)
    if not user:
        return False
    return (user.role in ADMIN_ROLES) or (user.username or "").lower() == "admin"

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_admin_user():
            return jsonify({"status": "error", "message": "Admin permission required"}), 403
        return fn(*args, **kwargs)
    return wrapper

def book_payload(book):
    category = db.session.get(Category, book.category_id) if book.category_id else None
    return {
        "id": book.id,
        "google_book_id": book.google_book_id or "",
        "title": book.title or "",
        "author": book.author or "",
        "description": book.description or "",
        "isbn": book.isbn or "",
        "image": book.image or "",
        "preview_link": book.file_path or "",
        "quantity": book.quantity or 0,
        "available": bool(book.available),
        "shelf_location": book.shelf_location or "",
        "category_id": book.category_id,
        "category_name": category.name if category else "",
    }

def user_payload(user):
    active_count = BorrowRecord.query.filter_by(
        user_id=user.id,
        returned=False,
        status="approved"
    ).count()
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email or "",
        "role": user.role or "user",
        "is_locked": bool(user.is_locked),
        "status_text": "Khóa" if user.is_locked else "Hoạt động",
        "borrowed_count": active_count,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

def borrow_payload(record):
    due_date = record.due_date
    now = datetime.utcnow()
    overdue_days = 0
    if due_date and not record.returned and record.status in ("approved", "return_pending") and due_date < now:
        overdue_days = (now.date() - due_date.date()).days
    return {
        "id": record.id,
        "user_id": record.user_id,
        "username": record.user.username if record.user else "",
        "user_email": record.user.email if record.user else "",
        "book_id": record.book_id,
        "book_title": record.book.title if record.book else "",
        "book_author": record.book.author if record.book else "",
        "request_date": record.request_date.isoformat() if record.request_date else None,
        "borrow_date": record.borrow_date.isoformat() if record.borrow_date else None,
        "due_date": due_date.isoformat() if due_date else None,
        "return_date": record.return_date.isoformat() if record.return_date else None,
        "returned": bool(record.returned),
        "status": record.status or "approved",
        "reject_reason": record.reject_reason or "",
        "fine_amount": record.fine_amount or 0,
        "overdue_days": max(0, overdue_days),
    }

@app.route("/api/admin/dashboard", methods=["GET"])
@admin_required
def admin_dashboard():
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    total_users = User.query.count()
    new_users = User.query.filter(User.created_at >= month_start).count()
    total_books = Book.query.count()
    total_copies = db.session.query(db.func.coalesce(db.func.sum(Book.quantity), 0)).scalar() or 0
    active_borrows = BorrowRecord.query.filter_by(status="approved", returned=False).count()
    returned_count = BorrowRecord.query.filter_by(returned=True).count()
    overdue_count = BorrowRecord.query.filter(
        BorrowRecord.status.in_(["approved", "return_pending"]),
        BorrowRecord.returned == False,
        BorrowRecord.due_date < now
    ).count()
    top_books = db.session.query(
        Book.title,
        db.func.count(BorrowRecord.id).label("borrow_count")
    ).join(BorrowRecord, BorrowRecord.book_id == Book.id).group_by(Book.id, Book.title).order_by(db.func.count(BorrowRecord.id).desc()).limit(5).all()

    return jsonify({
        "status": "success",
        "summary": {
            "total_users": total_users,
            "new_users_this_month": new_users,
            "total_books": total_books,
            "total_copies": int(total_copies),
            "active_borrows": active_borrows,
            "returned_count": returned_count,
            "overdue_count": overdue_count,
        },
        "top_books": [{"title": row.title, "borrow_count": row.borrow_count} for row in top_books]
    })

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_users():
    keyword = request.args.get("q", "").strip()
    query = User.query
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(db.or_(
            User.username.ilike(pattern),
            User.full_name.ilike(pattern),
            User.email.ilike(pattern)
        ))
    users = query.order_by(User.id.desc()).limit(200).all()
    return jsonify({"status": "success", "users": [user_payload(user) for user in users]})

@app.route("/api/admin/users/<int:user_id>", methods=["PATCH", "DELETE"])
@admin_required
def admin_user_detail(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    if request.method == "DELETE":
        db.session.delete(user)
        db.session.commit()
        return jsonify({"status": "success"})

    data = request.get_json() or {}
    for field in ("full_name", "email", "role"):
        if field in data:
            setattr(user, field, data.get(field))
    if "is_locked" in data:
        user.is_locked = bool(data.get("is_locked"))
    db.session.commit()
    return jsonify({"status": "success", "user": user_payload(user)})

@app.route("/api/admin/users/<int:user_id>/history", methods=["GET"])
@admin_required
def admin_user_history(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    records = BorrowRecord.query.filter_by(user_id=user_id).order_by(BorrowRecord.id.desc()).all()
    return jsonify({"status": "success", "user": user_payload(user), "history": [borrow_payload(r) for r in records]})

@app.route("/api/admin/books", methods=["GET", "POST"])
@admin_required
def admin_books():
    if request.method == "GET":
        keyword = request.args.get("q", "").strip()
        query = Book.query
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(db.or_(Book.title.ilike(pattern), Book.author.ilike(pattern), Book.isbn.ilike(pattern)))
        books = query.order_by(Book.id.desc()).limit(200).all()
        return jsonify({"status": "success", "books": [book_payload(book) for book in books]})

    data = request.get_json() or {}
    book = Book(
        google_book_id=data.get("google_book_id"),
        title=data.get("title"),
        author=data.get("author"),
        description=data.get("description"),
        isbn=data.get("isbn"),
        image=data.get("image"),
        file_path=data.get("preview_link") or data.get("file_path"),
        quantity=int(data.get("quantity") or 1),
        shelf_location=data.get("shelf_location"),
        category_id=data.get("category_id") or None,
        available=True,
    )
    db.session.add(book)
    db.session.commit()
    return jsonify({"status": "success", "book": book_payload(book)}), 201

@app.route("/api/admin/books/<int:book_id>", methods=["PATCH", "DELETE"])
@admin_required
def admin_book_detail(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"status": "error", "message": "Book not found"}), 404
    if request.method == "DELETE":
        db.session.delete(book)
        db.session.commit()
        return jsonify({"status": "success"})

    data = request.get_json() or {}
    for field in ("google_book_id", "title", "author", "description", "isbn", "image", "shelf_location"):
        if field in data:
            setattr(book, field, data.get(field))
    if "preview_link" in data or "file_path" in data:
        book.file_path = data.get("preview_link") or data.get("file_path")
    if "quantity" in data:
        book.quantity = max(0, int(data.get("quantity") or 0))
    if "category_id" in data:
        book.category_id = data.get("category_id") or None
    book.available = (book.quantity or 0) > 0
    db.session.commit()
    return jsonify({"status": "success", "book": book_payload(book)})

@app.route("/api/admin/borrows", methods=["GET"])
@admin_required
def admin_borrows():
    status_filter = request.args.get("status", "").strip()
    query = BorrowRecord.query.join(User, BorrowRecord.user_id == User.id).join(Book, BorrowRecord.book_id == Book.id)
    if status_filter == "overdue":
        query = query.filter(
            BorrowRecord.status.in_(["approved", "return_pending"]),
            BorrowRecord.returned == False,
            BorrowRecord.due_date < datetime.utcnow()
        )
    elif status_filter:
        query = query.filter(BorrowRecord.status == status_filter)
    records = query.order_by(BorrowRecord.id.desc()).limit(300).all()
    return jsonify({"status": "success", "borrows": [borrow_payload(record) for record in records]})

@app.route("/api/admin/borrows/<int:borrow_id>/<action>", methods=["POST"])
@admin_required
def admin_borrow_action(borrow_id, action):
    record = db.session.get(BorrowRecord, borrow_id)
    if not record:
        return jsonify({"status": "error", "message": "Borrow record not found"}), 404
    data = request.get_json() or {}

    if action == "approve":
        if (record.book.quantity or 0) <= 0:
            return jsonify({"status": "error", "message": "Book quantity is not enough"}), 400
        record.status = "approved"
        record.borrow_date = datetime.utcnow()
        record.book.quantity = max(0, (record.book.quantity or 0) - 1)
        record.book.available = (record.book.quantity or 0) > 0
    elif action == "reject":
        record.status = "rejected"
        record.reject_reason = data.get("reason") or ""
        record.returned = True
    elif action == "confirm-return":
        record.status = "returned"
        record.returned = True
        record.return_date = datetime.utcnow()
        record.book.quantity = (record.book.quantity or 0) + 1
        record.book.available = True
    elif action == "fine":
        record.fine_amount = max(0, int(data.get("fine_amount") or 0))
    elif action == "warn":
        notification = Notification(
            title="Nhac tra sach",
            message=f"Vui long tra sach {record.book.title} dung han.",
            notification_type="reminder"
        )
        db.session.add(notification)
    else:
        return jsonify({"status": "error", "message": "Invalid action"}), 400

    db.session.commit()
    return jsonify({"status": "success", "borrow": borrow_payload(record)})

@app.route("/api/admin/categories", methods=["GET", "POST"])
@admin_required
def admin_categories():
    if request.method == "GET":
        categories = Category.query.order_by(Category.name.asc()).all()
        return jsonify({"status": "success", "categories": [{"id": c.id, "name": c.name, "description": c.description or ""} for c in categories]})
    data = request.get_json() or {}
    category = Category(name=data.get("name"), description=data.get("description"))
    db.session.add(category)
    db.session.commit()
    return jsonify({"status": "success", "category": {"id": category.id, "name": category.name, "description": category.description or ""}}), 201

@app.route("/api/admin/categories/<int:category_id>", methods=["PATCH", "DELETE"])
@admin_required
def admin_category_detail(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"status": "error", "message": "Category not found"}), 404
    if request.method == "DELETE":
        db.session.delete(category)
        db.session.commit()
        return jsonify({"status": "success"})
    data = request.get_json() or {}
    category.name = data.get("name", category.name)
    category.description = data.get("description", category.description)
    db.session.commit()
    return jsonify({"status": "success", "category": {"id": category.id, "name": category.name, "description": category.description or ""}})

@app.route("/api/admin/reviews", methods=["GET"])
@admin_required
def admin_reviews():
    reviews = Review.query.order_by(Review.id.desc()).limit(200).all()
    return jsonify({"status": "success", "reviews": [{
        "id": r.id,
        "username": r.user.username if r.user else "",
        "book_title": r.book.title if r.book else "",
        "rating": r.rating,
        "comment": r.comment or "",
        "hidden": bool(r.hidden),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in reviews]})

@app.route("/api/admin/reviews/<int:review_id>", methods=["PATCH", "DELETE"])
@admin_required
def admin_review_detail(review_id):
    review = db.session.get(Review, review_id)
    if not review:
        return jsonify({"status": "error", "message": "Review not found"}), 404
    if request.method == "DELETE":
        db.session.delete(review)
    else:
        data = request.get_json() or {}
        review.hidden = bool(data.get("hidden"))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/api/admin/notifications", methods=["GET", "POST"])
@admin_required
def admin_notifications():
    if request.method == "GET":
        notifications = Notification.query.order_by(Notification.id.desc()).limit(100).all()
        return jsonify({"status": "success", "notifications": [{
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        } for n in notifications]})
    data = request.get_json() or {}
    notification = Notification(
        title=data.get("title"),
        message=data.get("message"),
        notification_type=data.get("notification_type") or "general"
    )
    db.session.add(notification)
    db.session.commit()
    return jsonify({"status": "success"}), 201

@app.route("/api/admin/notifications/<int:notification_id>", methods=["DELETE"])
@admin_required
def admin_notification_delete(notification_id):
    notification = db.session.get(Notification, notification_id)
    if notification:
        db.session.delete(notification)
        db.session.commit()
    return jsonify({"status": "success"})

@app.route("/api/admin/reports", methods=["GET", "POST"])
@admin_required
def admin_reports():
    if request.method == "GET":
        reports = ViolationReport.query.order_by(ViolationReport.id.desc()).limit(200).all()
        return jsonify({"status": "success", "reports": [{
            "id": r.id,
            "username": r.user.username if r.user else "",
            "book_title": r.book.title if r.book else "",
            "report_type": r.report_type,
            "message": r.message or "",
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reports]})
    data = request.get_json() or {}
    report = ViolationReport(
        user_id=data.get("user_id"),
        book_id=data.get("book_id"),
        report_type=data.get("report_type") or "other",
        message=data.get("message")
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({"status": "success"}), 201

@app.route("/api/admin/reports/<int:report_id>", methods=["PATCH", "DELETE"])
@admin_required
def admin_report_detail(report_id):
    report = db.session.get(ViolationReport, report_id)
    if not report:
        return jsonify({"status": "error", "message": "Report not found"}), 404
    if request.method == "DELETE":
        db.session.delete(report)
    else:
        report.status = (request.get_json() or {}).get("status", "closed")
    db.session.commit()
    return jsonify({"status": "success"})

# ===================== STATIC FILES =====================
@app.route("/")
def serve_index():
    return send_from_directory(os.path.join(BASE_DIR, "../frontend"), "SignUp_LogIn_Form.html")

@app.route("/<path:path>")
def serve_static_files(path):
    return send_from_directory(os.path.join(BASE_DIR, "../frontend"), path)

# ===================== MAIN =====================
if __name__ == "__main__":
    print("UniLib backend running on http://localhost:3000")
    app.run(host="0.0.0.0", port=3000, debug=True)
