let dragFrom = null;

function el(id) { return document.getElementById(id); }

function renderBoard(board) {
  const boardEl = el("board");
  boardEl.innerHTML = "";

  for (let i = 0; i < board.length; i++) {
    const n = board[i];

    const tile = document.createElement("div");
    tile.className = "tile";

    const img = document.createElement("img");
    img.src = window.PUZZLE_IMG_BASE + n + ".jpg";
    img.draggable = !window.PUZZLE_LOCKED;

    // 드래그 시작
    img.addEventListener("dragstart", () => { dragFrom = i; });

    // 드롭은 tile에서 받는 게 UX가 좋음(타일 빈 공간에도 drop 가능)
    tile.addEventListener("dragover", (e) => {
      if (window.PUZZLE_LOCKED) return;
      e.preventDefault();
    });

    tile.addEventListener("drop", async (e) => {
      if (window.PUZZLE_LOCKED) return;
      e.preventDefault();

      const to = i;
      if (dragFrom === null || dragFrom === to) return;

      const res = await fetch("/api/games/puzzle/swap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ a: dragFrom, b: to })
      });

      const data = await res.json();
      if (!res.ok) {
        alert(data.error || "swap failed");
        return;
      }

      el("turns").innerText = data.turns;
      renderBoard(data.board);

      if (data.passed) {
        el("result").style.display = "block";
      } else if (data.locked) {
        alert("Turn limit exceeded. Reset or change limit.");
      }

      dragFrom = null;
    });

    tile.appendChild(img);
    boardEl.appendChild(tile);
  }
}

function init() {
  // ✅ 서버에서 내려준 보드로 시작 (랜덤 금지)
  const board = window.PUZZLE_INIT_BOARD;
  if (!Array.isArray(board) || board.length !== 25) {
    alert("Puzzle init board missing");
    return;
  }
  renderBoard(board);
}

init();
