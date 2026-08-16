document.addEventListener("DOMContentLoaded", () => {
  if (typeof OZU_QUIZ === "undefined") return;

  const QUIZ_LENGTH = 7;
  const PASS_SCORE = 5;

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
  const resultBadgeEl = document.getElementById("quiz-result-badge");
  const resultCommentEl = document.getElementById("quiz-result-comment");
  const retryBtn = document.getElementById("quiz-retry-btn");
  const reviewListEl = document.getElementById("quiz-review-list");

  let order = [];
  let current = 0;
  let score = 0;
  let answerLog = [];

  document.querySelectorAll("#quiz-total-1").forEach((el) => {
    el.textContent = OZU_QUIZ.length;
  });
  document.querySelectorAll("#quiz-total-2").forEach((el) => {
    el.textContent = QUIZ_LENGTH;
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
    order = shuffledIndexes(OZU_QUIZ.length).slice(0, QUIZ_LENGTH);
    current = 0;
    score = 0;
    answerLog = [];
    startScreen.style.display = "none";
    resultScreen.style.display = "none";
    gameScreen.style.display = "block";
    renderQuestion();
  }

  function renderQuestion() {
    const q = OZU_QUIZ[order[current]];
    progressText.textContent = `第${current + 1}問 / 全${QUIZ_LENGTH}問(正解数: ${score})`;
    questionEl.textContent = q.q;
    explainEl.classList.remove("show");
    explainEl.textContent = "";
    nextWrap.classList.remove("show");
    choicesEl.innerHTML = "";

    q.choices.forEach((choice, i) => {
      const btn = document.createElement("button");
      btn.className = "quiz-choice";
      btn.innerHTML = `<span class="quiz-choice-text"></span><span class="quiz-choice-badge"></span>`;
      btn.querySelector(".quiz-choice-text").textContent = choice;
      btn.addEventListener("click", () => selectAnswer(i, btn));
      choicesEl.appendChild(btn);
    });
  }

  function selectAnswer(i, btnEl) {
    const q = OZU_QUIZ[order[current]];
    const allBtns = choicesEl.querySelectorAll(".quiz-choice");
    allBtns.forEach((b) => (b.disabled = true));

    const isCorrect = i === q.answer;

    if (isCorrect) {
      btnEl.classList.add("correct");
      btnEl.querySelector(".quiz-choice-badge").textContent = "○ 正解";
      score++;
    } else {
      btnEl.classList.add("wrong");
      btnEl.querySelector(".quiz-choice-badge").textContent = "× 不正解";
      const correctBtn = allBtns[q.answer];
      correctBtn.classList.add("correct");
      correctBtn.querySelector(".quiz-choice-badge").textContent = "○ 正解";
    }

    answerLog.push({
      question: q.q,
      correct: isCorrect,
      yourAnswer: q.choices[i],
      correctAnswer: q.choices[q.answer],
    });

    explainEl.innerHTML = "";
    const explainText = document.createElement("p");
    explainText.className = "quiz-explain-text";
    explainText.textContent = q.explain;
    explainEl.appendChild(explainText);
    if (q.url) {
      const sourceLink = document.createElement("a");
      sourceLink.href = q.url;
      sourceLink.target = "_blank";
      sourceLink.rel = "noopener";
      sourceLink.className = "quiz-source-link";
      sourceLink.textContent = "→ 出典(一次情報)を見る";
      explainEl.appendChild(sourceLink);
    }
    explainEl.classList.add("show");
    nextWrap.classList.add("show");
    nextBtn.textContent = current === QUIZ_LENGTH - 1 ? "結果を見る →" : "次へ →";
  }

  function nextQuestion() {
    current++;
    if (current >= QUIZ_LENGTH) {
      showResult();
    } else {
      renderQuestion();
    }
  }

  function showResult() {
    gameScreen.style.display = "none";
    resultScreen.style.display = "block";
    scoreEl.textContent = score;

    if (score === QUIZ_LENGTH) {
      resultBadgeEl.textContent = "🎉 満点おめでとう！";
      resultBadgeEl.className = "quiz-result-badge perfect";
      resultCommentEl.textContent = "全問正解です。あなたはもう大洲マスターですね。";
    } else if (score >= PASS_SCORE) {
      resultBadgeEl.textContent = "合格";
      resultBadgeEl.className = "quiz-result-badge pass";
      resultCommentEl.textContent = `合格ラインの${PASS_SCORE}問以上正解でした。`;
    } else {
      resultBadgeEl.textContent = "不合格";
      resultBadgeEl.className = "quiz-result-badge fail";
      resultCommentEl.textContent = `合格ラインは${PASS_SCORE}問正解です。もう一度挑戦してみましょう。`;
    }

    renderReview();
  }

  function renderReview() {
    const items = answerLog
      .map((log, i) => {
        const markText = log.correct ? "○ 正解" : "× 不正解";
        const markClass = log.correct ? "correct" : "wrong";
        const answerLine = log.correct
          ? `あなたの回答: ${log.yourAnswer}`
          : `あなたの回答: ${log.yourAnswer}(正解: ${log.correctAnswer})`;
        return `
      <div class="quiz-review-item ${markClass}">
        <span class="quiz-review-mark">${markText}</span>
        <div class="quiz-review-body">
          <p class="quiz-review-q">第${i + 1}問. ${log.question}</p>
          <p class="quiz-review-a">${answerLine}</p>
        </div>
      </div>`;
      })
      .join("");

    reviewListEl.innerHTML = `<p class="quiz-review-title">全${QUIZ_LENGTH}問の正解・不正解一覧</p>${items}`;
  }

  startBtn.addEventListener("click", startQuiz);
  nextBtn.addEventListener("click", nextQuestion);
  retryBtn.addEventListener("click", startQuiz);
});
