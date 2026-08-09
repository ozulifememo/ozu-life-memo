document.addEventListener("DOMContentLoaded", () => {
  if (typeof OZU_QUIZ === "undefined") return;

  const startScreen = document.getElementById("quiz-start");
  const startBtn = document.getElementById("quiz-start-btn");
  const gameScreen = document.getElementById("quiz-game");
  const resultScreen = document.getElementById("quiz-result");
  const progressText = document.getElementById("quiz-progress-text");
  const questionEl = document.getElementById("quiz-question");
  const choicesEl = document.getElementById("quiz-choices");
  const explainEl = document.getElementById("quiz-explain");
  const nextWrap = document.getElementById("quiz-next-wrap");
  const nextBtn = document.getElementById("quiz-next-btn");
  const scoreEl = document.getElementById("quiz-score");
  const resultCommentEl = document.getElementById("quiz-result-comment");
  const retryBtn = document.getElementById("quiz-retry-btn");

  let order = [];
  let current = 0;
  let score = 0;

  document.querySelectorAll("#quiz-total-1, #quiz-total-2").forEach((el) => {
    el.textContent = OZU_QUIZ.length;
  });

  function shuffledIndexes(n) {
    const arr = Array.from({ length: n }, (_, i) => i);
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function startQuiz() {
    order = shuffledIndexes(OZU_QUIZ.length);
    current = 0;
    score = 0;
    startScreen.style.display = "none";
    resultScreen.style.display = "none";
    gameScreen.style.display = "block";
    renderQuestion();
  }

  function renderQuestion() {
    const q = OZU_QUIZ[order[current]];
    progressText.textContent = `第${current + 1}問 / 全${OZU_QUIZ.length}問(正解数: ${score})`;
    questionEl.textContent = q.q;
    explainEl.classList.remove("show");
    explainEl.textContent = "";
    nextWrap.classList.remove("show");
    choicesEl.innerHTML = "";

    q.choices.forEach((choice, i) => {
      const btn = document.createElement("button");
      btn.className = "quiz-choice";
      btn.textContent = choice;
      btn.addEventListener("click", () => selectAnswer(i, btn));
      choicesEl.appendChild(btn);
    });
  }

  function selectAnswer(i, btnEl) {
    const q = OZU_QUIZ[order[current]];
    const allBtns = choicesEl.querySelectorAll(".quiz-choice");
    allBtns.forEach((b) => (b.disabled = true));

    if (i === q.answer) {
      btnEl.classList.add("correct");
      score++;
    } else {
      btnEl.classList.add("wrong");
      allBtns[q.answer].classList.add("correct");
    }

    explainEl.textContent = q.explain;
    explainEl.classList.add("show");
    nextWrap.classList.add("show");
    nextBtn.textContent = current === OZU_QUIZ.length - 1 ? "結果を見る →" : "次へ →";
  }

  function nextQuestion() {
    current++;
    if (current >= OZU_QUIZ.length) {
      showResult();
    } else {
      renderQuestion();
    }
  }

  function showResult() {
    gameScreen.style.display = "none";
    resultScreen.style.display = "block";
    scoreEl.textContent = score;
    const rate = score / OZU_QUIZ.length;
    let comment;
    if (score === OZU_QUIZ.length) comment = "満点です。大洲マスター認定！";
    else if (rate >= 0.7) comment = "かなり大洲に詳しいですね。";
    else if (rate >= 0.4) comment = "まずまず。記事を読み返すと発見があるかも。";
    else comment = "これから大洲を知っていきましょう。";
    resultCommentEl.textContent = comment;
  }

  startBtn.addEventListener("click", startQuiz);
  nextBtn.addEventListener("click", nextQuestion);
  retryBtn.addEventListener("click", startQuiz);
});
