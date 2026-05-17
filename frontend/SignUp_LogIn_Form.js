const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');

registerBtn.addEventListener('click', () => {
    container.classList.add('active');
})

loginBtn.addEventListener('click', () => {
    container.classList.remove('active');
})
function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.style.backgroundColor = isError ? "#e74c3c" : "#4CAF50"; // đỏ nếu lỗi, xanh nếu ok
  toast.style.display = "block";
  setTimeout(() => toast.style.display = "none", 3000);
}
