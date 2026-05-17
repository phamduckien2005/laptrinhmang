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
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ===================== MODEL =====================
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    description = db.Column(db.Text)
    isbn = db.Column(db.String(100))
    image = db.Column(db.String(500))
    available = db.Column(db.Boolean, default=True)
    file_path = db.Column(db.String(500))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class BorrowRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    return_date = db.Column(db.DateTime, nullable=True)
    returned = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='borrow_records')
    book = db.relationship('Book', backref='borrow_records')

# ===================== INIT DATABASE =====================
with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    borrow_columns = [column["name"] for column in inspector.get_columns("borrow_record")]
    if "due_date" not in borrow_columns:
        with db.engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE borrow_record ADD COLUMN due_date DATETIME")
    print(f" Database initialized at: {DB_PATH}")

# ===================== AUTH API =====================
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Thiếu tên đăng nhập hoặc mật khẩu!"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Tên người dùng đã tồn tại!"}), 400

    new_user = User(username=username)
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

    if user.check_password(password):
        session["user_id"] = user.id
        session["username"] = username
        return jsonify({
            "status": "success", 
            "message": "Đăng nhập thành công!", 
            "user_id": user.id,
            "username": username
        }), 200
    else:
        return jsonify({"status": "error", "message": "Sai mật khẩu!"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return jsonify({"status": "success", "message": "Đã đăng xuất"})

@app.route("/check-auth", methods=["GET"])
def check_auth():
    if "user_id" in session:
        return jsonify({
            "status": "success",
            "user_id": session["user_id"],
            "username": session.get("username", "")
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
        if not book or not book.available:
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
        elif not book.available:
            return jsonify({"status": "error", "message": "Sách đang được mượn"}), 400
        else:
            if description and not book.description:
                book.description = description
            if preview_link and not book.file_path:
                book.file_path = preview_link

    existing = BorrowRecord.query.filter_by(user_id=user_id, book_id=book.id, returned=False).first()
    if existing:
        return jsonify({"status": "error", "message": "Bạn đã mượn sách này rồi!"}), 400

    now = datetime.utcnow()
    borrow = BorrowRecord(
        user_id=user_id,
        book_id=book.id,
        borrow_date=now,
        due_date=now + timedelta(days=borrow_days)
    )
    book.available = False
    db.session.add(borrow)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Mượn sách thành công!",
        "book_id": book.id,
        "borrow_id": borrow.id,
        "due_date": borrow.due_date.isoformat(),
        "borrow_days": borrow_days
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
        returned=False
    ).first()

    if not record:
        return jsonify({"status": "error", "message": "Không tìm thấy sách đã mượn"}), 400

    record.returned = True
    record.return_date = datetime.utcnow()

    book = db.session.get(Book, book_id)
    if book:
        book.available = True

    db.session.commit()
    return jsonify({"status": "success", "message": "Trả sách thành công!"}), 200

@app.route("/api/user/borrowed-count", methods=["GET"])
def get_borrowed_count():
    if "user_id" not in session:
        return jsonify({"count": 0})
    
    user_id = session["user_id"]
    count = BorrowRecord.query.filter_by(user_id=user_id, returned=False).count()
    return jsonify({"count": count})

@app.route("/api/user/borrowed-books", methods=["GET"])
def get_borrowed_books():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    
    user_id = session["user_id"]
    
    records = BorrowRecord.query.filter_by(
        user_id=user_id, 
        returned=False
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
