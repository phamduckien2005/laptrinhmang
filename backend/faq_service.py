import json
import os
import re
import requests
from difflib import SequenceMatcher
from typing import Tuple, Optional, List, Dict

DATA_PATH = os.path.join(os.path.dirname(__file__), "instance", "faq.json")
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

# ================== LOAD FAQ ==================
def load_faq():
    try:
        if not os.path.exists(DATA_PATH):
            print(f"Không tìm thấy file FAQ tại: {DATA_PATH}")
            return get_default_faq()
        
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Đã tải {len(data)} câu hỏi từ FAQ")
            return data
            
    except Exception as e:
        print(f"Lỗi khi đọc FAQ: {e}")
        return get_default_faq()

def get_default_faq():
    return [
        {"question": "mượn sách", "answer": "Tìm sách và bấm Mượn sách."},
        {"question": "trả sách", "answer": "Vào mục Đã mượn, bấm Trả."},
    ]

FAQ_DATA = load_faq()

# ================== GOOGLE BOOKS ==================
def search_google_books(query: str, max_results: int = 4) -> List[Dict]:
    try:
        params = {
            "q": query + " language:vi",  # Ưu tiên sách tiếng Việt
            "maxResults": max_results,
            "orderBy": "relevance"
        }
        
        response = requests.get(GOOGLE_BOOKS_API, params=params, timeout=8)
        
        if response.status_code == 200:
            data = response.json()
            books = []
            
            for item in data.get("items", [])[:max_results]:
                volume_info = item.get("volumeInfo", {})
                
                book = {
                    "title": volume_info.get("title", "Không có tiêu đề"),
                    "authors": ", ".join(volume_info.get("authors", ["Không rõ"])),
                    "description": (volume_info.get("description", "Không có mô tả")[:150] + "...") if volume_info.get("description") else "Không có mô tả",
                    "categories": ", ".join(volume_info.get("categories", [])[:2]),
                    "pageCount": volume_info.get("pageCount", ""),
                    "thumbnail": volume_info.get("imageLinks", {}).get("thumbnail", ""),
                }
                books.append(book)
            
            return books
        return []
            
    except Exception as e:
        print(f"Lỗi Google Books: {e}")
        return []

def get_book_recommendations(topic: str) -> str:
    books = search_google_books(topic)
    
    if not books:
        return f"Không tìm thấy sách về '{topic}'. Bạn có thể thử tìm với từ khóa khác hoặc đến quầy thủ thư để được tư vấn."
    
    response = f" **Gợi ý sách về {topic}:**\n\n"
    
    for i, book in enumerate(books, 1):
        response += f"{i}. **{book['title']}**\n"
        response += f"Tác giả: {book['authors']}\n"
        
        if book['categories']:
            response += f"Thể loại: {book['categories']}\n"
        
        response += f" {book['description']}\n\n"
    
    response += "💡 *Những sách này có thể có tại thư viện UniLib. Hãy đến quầy thủ thư để tìm hiểu thêm!*"
    
    return response

# ================== SMART FAQ MATCHING ==================
def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\sáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def find_in_faq(user_message: str) -> Optional[str]:
    """Tìm trong FAQ - chỉ trả về nếu thực sự khớp"""
    if not FAQ_DATA:
        print("FAQ_DATA trống")
        return None
    
    user_norm = normalize(user_message)
    print(f"Đang tìm FAQ cho: '{user_norm}'")
    
    # Tìm khớp chính xác trước
    for item in FAQ_DATA:
        faq_norm = normalize(item["question"])
        print(f"  • So sánh với: '{faq_norm}'")
        
        # Kiểm tra khớp chính xác hơn
        if faq_norm in user_norm or user_norm in faq_norm:
            print(f"Tìm thấy khớp chính xác: '{faq_norm}'")
            return item["answer"]
        
        # Kiểm tra khớp tương đối
        similarity = SequenceMatcher(None, user_norm, faq_norm).ratio()
        if similarity > 0.7:
            print(f"Tìm thấy khớp tương đối ({similarity:.2f}): '{faq_norm}'")
            return item["answer"]
    
    print(" Không tìm thấy trong FAQ")
    return None

# ================== MAIN FUNCTION - FIXED ==================
def find_best_answer(user_message: str, threshold: float = 0.0) -> Tuple[str, float]:
    
    user_lower = user_message.lower()
    print(f"\n{'='*50}")
    print(f" Query: '{user_message}'")
    print(f"Lower: '{user_lower}'")
    if "chào" in user_lower or "hello" in user_lower or "hi" in user_lower:
        print("Đây là câu chào")
        return "Xin chào! Tôi là trợ lý thư viện UniLib. Tôi có thể gợi ý sách hoặc trả lời câu hỏi về thư viện. Bạn cần gì ạ?", 1.0
    
    if "cảm ơn" in user_lower or "thanks" in user_lower:
        print("Đây là lời cảm ơn")
        return "Cảm ơn bạn! Nếu có thắc mắc gì khác, cứ hỏi tôi nhé!", 1.0
    
    # 2. KIỂM TRA FAQ TRƯỚC
    print("📋 Đang kiểm tra FAQ...")
    faq_answer = find_in_faq(user_message)
    if faq_answer:
        print("Trả lời từ FAQ")
        return faq_answer, 0.9
    
    # 3. KIỂM TRA CÂU HỎI GỢI Ý SÁCH
    book_keywords = [
        "gợi ý sách", "đề xuất sách", "nên đọc sách", 
        "sách hay", "sách nào hay", "tìm sách về",
        "kiếm sách về", "có sách về", "sách về"
    ]
    
    is_book_request = any(keyword in user_lower for keyword in book_keywords)
    
    if is_book_request:
        print("Đây là câu hỏi gợi ý sách, gọi Google Books...")
        
        # Trích xuất chủ đề
        topic = user_lower
        
        # Loại bỏ các từ hỏi
        remove_words = ["gợi ý", "đề xuất", "nên đọc", "sách", "sách hay", "sách nào", "tìm", "kiếm", "có", "về", "bạn", "cho", "tôi", "một", "vài", "cuốn"]
        for word in remove_words:
            topic = topic.replace(word, "")
        
        topic = topic.strip()
        
        # Nếu topic rỗng, dùng mặc định
        if not topic or len(topic) < 2:
            topic = "sách hay nhất"
        
        print(f"Topic: '{topic}'")
        
        # Gọi Google Books
        response = get_book_recommendations(topic)
        return response, 0.8
    print("🤔 Không tìm thấy câu trả lời phù hợp")
    return "Tôi có thể giúp bạn:\n• Gợi ý sách (ví dụ: 'Gợi ý sách về AI')\n• Trả lời câu hỏi về thư viện\n• Hướng dẫn mượn/trả sách\n\nBạn muốn hỏi gì ạ?", 0.3

# ================== TEST ==================
if __name__ == "__main__":
    if os.path.exists(DATA_PATH):
        print(f"File FAQ tồn tại: {DATA_PATH}")
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            faq_content = json.load(f)
            print(f"Số lượng FAQ: {len(faq_content)}")
            for i, item in enumerate(faq_content[:3], 1):
                print(f"  {i}. {item['question']}")
            if len(faq_content) > 3:
                print(f"  ... và {len(faq_content) - 3} câu hỏi khác")
    else:
        print(f"File FAQ không tồn tại: {DATA_PATH}")

