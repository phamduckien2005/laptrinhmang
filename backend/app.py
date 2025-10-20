import os
from werkzeug.utils import secure_filename  # Cho upload file an toàn
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
from dotenv import load_dotenv
import requests
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'unilib-secret-key'  # Required for SocketIO
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable for performance

# Thêm CORS để cho phép fetch từ local file hoặc Live Server
from flask_cors import CORS
CORS(app, resources={r"/*": {"origins": "*"}})  # * cho tất cả origin (an toàn cho dev)

# Initialize SQLAlchemy and SocketIO
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# SQL Model for Book (Table: books)
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    available = db.Column(db.Boolean, default=True)
    image = db.Column(db.String(200), nullable=True)  # Phải có dòng này!
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'description': self.description,
            'isbn': self.isbn,
            'available': self.available,
            'image': self.image,  # Thêm image vào dict
            'createdAt': self.created_at.isoformat()
        }

# Create tables and indexes (run on startup)
with app.app_context():
    db.create_all()
    # Create indexes for faster search
    # Create indexes for faster search (SQLAlchemy 2.0+ compatible)
try:
    with db.engine.connect() as connection:
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_title ON books (title)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_author ON books (author)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_description ON books (description)"))
        connection.commit()
    print("Database tables and indexes created.")
except Exception as e:
    print(f"Index creation error (may already exist): {e}")
# Route: GET /api/books - Fetch all books
@app.route('/api/books', methods=['GET'])
def get_books():
    try:
        books = Book.query.all()
        return jsonify([book.to_dict() for book in books])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route: POST /api/books - Add new book (emit WebSocket notification)
@app.route('/api/books', methods=['POST'])
def add_book():
    try:
        data = request.json
        if not data.get('title') or not data.get('author') or not data.get('description'):
            return jsonify({'error': 'Title, author, and description are required'}), 400
        
        # Check for duplicate ISBN if provided
        if data.get('isbn'):
            existing = Book.query.filter_by(isbn=data['isbn']).first()
            if existing:
                return jsonify({'error': 'ISBN already exists'}), 400
        
        book = Book(
            title=data['title'],
            author=data['author'],
            description=data['description'],
            isbn=data.get('isbn'),
            available=data.get('available', True)
        )
        db.session.add(book)
        db.session.commit()
        
        # WebSocket: Emit real-time notification
        socketio.emit('newBook', {
            'message': 'Sách mới đã được thêm!',
            'book': book.to_dict()
        })
        
        return jsonify(book.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Route: DELETE /api/books/<id> - Delete book (emit WebSocket notification)
@app.route('/api/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    try:
        book = Book.query.get_or_404(book_id)
        db.session.delete(book)
        db.session.commit()
        
        # WebSocket: Emit real-time notification
        socketio.emit('bookDeleted', {
            'message': 'Sách đã bị xóa!',
            'id': book_id
        })
        
        return jsonify({'message': 'Xóa thành công'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Route: GET /api/books/search - AI-powered smart search with SQL fallback
@app.route('/api/books/search', methods=['GET'])
def search_books():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        # Step 1: Fetch all books for AI semantic search
        books = Book.query.all()
        books_dict = [book.to_dict() for book in books]

        # Step 2: AI Semantic Search using Hugging Face
        api_url = 'https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2'
        headers = {'Authorization': f'Bearer {os.getenv("HUGGINGFACE_API_KEY")}'}

        # Encode query
        query_response = requests.post(api_url, headers=headers, json=[query])
        if query_response.status_code != 200:
            raise Exception(f'AI API error: {query_response.status_code}')
        query_embedding = query_response.json()[0]

        # Encode each book's description and compute similarity
        results = []
        for book in books_dict:
            if not book.get('description'):
                continue
            book_response = requests.post(api_url, headers=headers, json=[book['description']])
            if book_response.status_code != 200:
                continue
            book_embedding = book_response.json()[0]

            # Simple cosine similarity
            similarity = sum(a * b for a, b in zip(query_embedding, book_embedding))
            similarity = max(0, similarity)

            if similarity > 0.1:  # Threshold
                book['similarity'] = float(similarity)
                results.append(book)

        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return jsonify(results[:10])  # Top 10

    except Exception as e:
        print(f'AI Search error: {e}')
        # Fallback: SQL LIKE search
        fallback_results = Book.query.filter(
        db.or_(
        db.func.lower(Book.title).like(f'%{query.lower()}%'),  # Case-insensitive cho title
        db.func.lower(Book.author).like(f'%{query.lower()}%'),  # Case-insensitive cho author
        db.func.lower(Book.description).like(f'%{query.lower()}%')  # Case-insensitive cho description
        )
        ).limit(10).all()
        
        fallback = []
        for book in fallback_results:
            book_dict = book.to_dict()
            book_dict['similarity'] = 1.0  # Default for fallback
            fallback.append(book_dict)
        
        return jsonify(fallback)

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print(f'User connected: {request.sid}')
    emit('connected', {'message': 'Connected to UniLib!'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'User disconnected: {request.sid}')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    print(f'Starting UniLib server on port {port}...')
    print(f'Database file: {os.path.abspath("unilib.db")}')
    socketio.run(app, debug=True, host='0.0.0.0', port=port)