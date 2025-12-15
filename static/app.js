document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-confirm]");
  if (btn) {
    const msg = btn.getAttribute("data-confirm") || "Continue?";
    if (!confirm(msg)) {
      e.preventDefault();
      e.stopPropagation();
    }
    return;
  }

  const noticeBtn = e.target.closest(".notice-link");
  if (noticeBtn) {
    const modal = document.getElementById("noticeModal");
    if (!modal) return;
    const title = modal.querySelector("#modalTitle");
    const date = modal.querySelector("#modalDate");
    const content = modal.querySelector("#modalContent");
    title.textContent = noticeBtn.dataset.title || "";
    date.textContent = noticeBtn.dataset.date || "";
    content.textContent = noticeBtn.dataset.content || "";
    modal.classList.add("active");
    modal.setAttribute("aria-hidden", "false");
    return;
  }

  if (e.target.matches("[data-close-modal]") || e.target.classList.contains("notice-modal")) {
    closeModal();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

function closeModal() {
  const modal = document.getElementById("noticeModal");
  if (modal) {
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
  }
}