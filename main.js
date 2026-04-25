// Toggle "New Task" form
const toggleBtn = document.getElementById("toggleAddForm");
const addForm   = document.getElementById("addForm");
const cancelBtn = document.getElementById("cancelAdd");

if (toggleBtn && addForm) {
  toggleBtn.addEventListener("click", () => {
    const isHidden = addForm.style.display === "none";
    addForm.style.display = isHidden ? "block" : "none";
    toggleBtn.textContent = isHidden ? "✕ Close" : "+ New Task";
    if (isHidden) addForm.querySelector("input[name='title']").focus();
  });
}

if (cancelBtn && addForm) {
  cancelBtn.addEventListener("click", () => {
    addForm.style.display = "none";
    toggleBtn.textContent = "+ New Task";
  });
}

// Auto-dismiss flash messages after 4s
document.querySelectorAll(".flash").forEach(el => {
  setTimeout(() => {
    el.style.transition = "opacity 0.4s";
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 400);
  }, 4000);
});
