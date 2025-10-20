const API_BASE = "http://localhost:3000/api/books";
let socket;

// Initialize WebSocket
socket = io("http://localhost:3000");

socket.on("connect", () => {
  console.log("Connected to WebSocket server");
  addNotification("Kết nối WebSocket thành công!");
});

socket.on("newBook", (data) => {
  addNotification(
    `${data.message} "${data.book.title}" bởi ${data.book.author}`
  );
  loadBooks();
});

socket.on("bookDeleted", (data) => {
  addNotification(data.message);
  loadBooks();
});

socket.on("connect_error", (error) => {
  console.error("WebSocket connection error:", error);
  addNotification("Lỗi kết nối WebSocket. Kiểm tra server!");
});

// Load all books (Đã cập nhật: Thêm hiển thị ảnh bìa sách)
async function loadBooks() {
  try {
    const response = await fetch(API_BASE);
    if (!response.ok) throw new Error("Failed to fetch books");
    const books = await response.json();
    const list = document.getElementById("booksList");
    list.innerHTML = "";
    if (books.length === 0) {
      list.innerHTML = "<li>Chưa có sách nào. Thêm sách mới để bắt đầu!</li>";
      return;
    }
    books.forEach((book) => {
      const li = document.createElement("li");
      // Thêm ảnh bìa sách (placeholder nếu không có)
      const imgSrc = book.image
        ? `http://localhost:3000/static/images/${book.image}`
        : "https://via.placeholder.com/100x150?text=No+Image";
      li.innerHTML = `
        <img src="${imgSrc}" alt="${
        book.title
      }" style="width: 100px; height: 150px; float: left; margin-right: 10px;" />
        <strong>${book.title}</strong> bởi ${book.author}<br>
        <small>Mô tả: ${
          book.description
            ? book.description.substring(0, 100) + "..."
            : "Không có mô tả"
        }</small><br>
        <small>Trạng thái: ${book.available ? "Có sẵn" : "Đã mượn"} | ISBN: ${
        book.isbn || "N/A"
      }</small><br>
        <button onclick="deleteBook('${book.id}')">Xóa Sách</button>
      `;
      list.appendChild(li);
    });
  } catch (err) {
    console.error("Error loading books:", err);
    document.getElementById("booksList").innerHTML =
      '<li class="error">Lỗi tải danh sách sách. Kiểm tra server!</li>';
  }
}

// Add new book (Đã cập nhật: Sử dụng FormData để upload ảnh)
document.getElementById("addBookForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  // Tạo FormData để hỗ trợ upload file
  const formData = new FormData();
  formData.append("title", document.getElementById("title").value);
  formData.append("author", document.getElementById("author").value);
  formData.append("description", document.getElementById("description").value);
  formData.append("isbn", document.getElementById("isbn").value);
  const imageFile = document.getElementById("image").files[0];
  if (imageFile) formData.append("image", imageFile);

  try {
    const response = await fetch(API_BASE, {
      method: "POST",
      body: formData, // Dùng FormData thay JSON để upload ảnh
    });
    if (response.ok) {
      addNotification("Sách đã được thêm thành công!");
      document.getElementById("addBookForm").reset();
      loadBooks();
    } else {
      const error = await response.json();
      addNotification(`Lỗi: ${error.error}`);
    }
  } catch (err) {
    console.error("Error adding book:", err);
    addNotification("Lỗi kết nối server khi thêm sách.");
  }
});

// Delete book
async function deleteBook(id) {
  if (confirm("Bạn có chắc muốn xóa sách này?")) {
    try {
      const response = await fetch(`${API_BASE}/${id}`, { method: "DELETE" });
      if (response.ok) {
        const result = await response.json();
        addNotification(result.message);
        loadBooks();
      } else {
        const error = await response.json();
        addNotification(`Lỗi: ${error.error}`);
      }
    } catch (err) {
      console.error("Error deleting book:", err);
      addNotification("Lỗi kết nối server khi xóa sách.");
    }
  }
}

// AI Search
async function searchBooks() {
  const query = document.getElementById("searchInput").value.trim();
  if (!query) {
    alert("Vui lòng nhập từ khóa tìm kiếm!");
    return;
  }
  const resultsDiv = document.getElementById("searchResults");
  resultsDiv.innerHTML = "<p>Đang tìm kiếm...</p>";
  try {
    const response = await fetch(
      `${API_BASE}/search?query=${encodeURIComponent(query)}`
    );
    if (!response.ok) throw new Error("Search failed");
    const results = await response.json();
    if (results.length === 0) {
      resultsDiv.innerHTML = "<p>Không tìm thấy sách phù hợp.</p>";
      return;
    }
    resultsDiv.innerHTML =
      "<h3>Kết quả Tìm kiếm (AI Semantic hoặc SQL Fallback):</h3><ul>" +
      results
        .map(
          (book) =>
            `<li><strong>${book.title}</strong> bởi ${book.author}` +
            (book.similarity
              ? ` (Độ tương đồng: ${Math.round(book.similarity * 100)}%)`
              : "") +
            `<br><small>${book.description.substring(0, 100)}...</small></li>`
        )
        .join("") +
      "</ul>";
  } catch (err) {
    console.error("Error searching:", err);
    resultsDiv.innerHTML =
      '<p class="error">Lỗi tìm kiếm. Kiểm tra server!</p>';
  }
}

// Add notification
function addNotification(message) {
  const list = document.getElementById("notificationsList");
  const li = document.createElement("li");
  li.className = "notification";
  li.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong>: ${message}`;
  list.appendChild(li);
  list.scrollTop = list.scrollHeight;
}

// Load books on page load
window.addEventListener("load", loadBooks);
