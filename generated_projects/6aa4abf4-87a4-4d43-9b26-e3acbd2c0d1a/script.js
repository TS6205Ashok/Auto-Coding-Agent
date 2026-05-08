const GENERATED_VERSION = "Project Agent Generated Starter v1";
const GOAL_STATE = [1, 2, 3, 4, 5, 6, 7, 8, 0];
let boardState = [...GOAL_STATE];
let moveCount = 0;

const boardElement = document.getElementById("puzzleBoard");
const moveCounter = document.getElementById("moveCounter");
const statusMessage = document.getElementById("statusMessage");
const shuffleButton = document.getElementById("shuffleButton");
const resetButton = document.getElementById("resetButton");

shuffleButton.addEventListener("click", startGame);
resetButton.addEventListener("click", resetBoard);

renderBoard();

function startGame() {
  boardState = shuffleBoard([...GOAL_STATE]);
  moveCount = 0;
  updateMoveCounter();
  statusMessage.textContent = "Game started. Put the numbers back in order.";
  renderBoard();
}

function resetBoard() {
  boardState = [...GOAL_STATE];
  moveCount = 0;
  updateMoveCounter();
  statusMessage.textContent = "Board reset. Click Shuffle / Start to play again.";
  renderBoard();
}

function shuffleBoard(state) {
  const shuffled = [...state];
  do {
    for (let index = shuffled.length - 1; index > 0; index -= 1) {
      const swapIndex = Math.floor(Math.random() * (index + 1));
      [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
    }

  } while (!isSolvable(shuffled) || isSolved(shuffled));
  return shuffled;
}

function isSolvable(state) {
  let inversions = 0;
  const filtered = state.filter((value) => value !== 0);
  for (let left = 0; left < filtered.length; left += 1) {
    for (let right = left + 1; right < filtered.length; right += 1) {
      if (filtered[left] > filtered[right]) {
        inversions += 1;
      }
    }
  }
  return inversions % 2 === 0;
}

function isSolved(state) {
  return state.every((value, index) => value === GOAL_STATE[index]);
}

function renderBoard() {
  boardElement.replaceChildren();

  boardState.forEach((value, index) => {
    if (value === 0) {
      const emptyTile = document.createElement("div");
      emptyTile.className = "empty-tile";
      emptyTile.setAttribute("aria-hidden", "true");
      boardElement.appendChild(emptyTile);
      return;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "tile";
    button.textContent = String(value);
    button.addEventListener("click", () => attemptMove(index));
    boardElement.appendChild(button);
  });
}

function attemptMove(index) {
  const emptyIndex = boardState.indexOf(0);
  const validMoves = getAdjacentIndexes(emptyIndex);
  if (!validMoves.includes(index)) {
    statusMessage.textContent = "That tile cannot move. Choose a tile next to the empty space.";
    return;
  }

  [boardState[index], boardState[emptyIndex]] = [boardState[emptyIndex], boardState[index]];
  moveCount += 1;
  updateMoveCounter();
  renderBoard();

  if (isSolved(boardState)) {
    statusMessage.textContent = `You solved the puzzle in ${moveCount} moves. Great job!`;
    return;
  }

  statusMessage.textContent = "Nice move. Keep going!";
}

function getAdjacentIndexes(index) {
  const row = Math.floor(index / 3);
  const column = index % 3;
  const adjacent = [];

  if (row > 0) adjacent.push(index - 3);
  if (row < 2) adjacent.push(index + 3);
  if (column > 0) adjacent.push(index - 1);
  if (column < 2) adjacent.push(index + 1);

  return adjacent;
}

function updateMoveCounter() {
  moveCounter.textContent = `Moves: ${moveCount}`;
}
