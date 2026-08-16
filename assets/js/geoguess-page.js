document.addEventListener("DOMContentLoaded", () => {
  if (typeof L === "undefined" || typeof OZU_GEOGUESS_PHOTOS === "undefined") return;

  const ROUND_LENGTH = Math.min(5, OZU_GEOGUESS_PHOTOS.length);
  const CORRECT_RADIUS_M = 30;
  const OZU_CENTER = [33.5049, 132.5457];
  const OZU_ZOOM = 13;

  const GSI_TILE = "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png";
  const GSI_ATTR =
    '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル</a>(国土地理院)';

  const noDataEl = document.getElementById("geo-no-data");
  const startScreen = document.getElementById("geo-start");
  const startBtn = document.getElementById("geo-start-btn");
  const gameScreen = document.getElementById("geo-game");
  const resultScreen = document.getElementById("geo-result");

  if (ROUND_LENGTH === 0) {
    if (noDataEl) noDataEl.style.display = "block";
    if (startScreen) startScreen.style.display = "none";
    return;
  }

  const progressText = document.getElementById("geo-progress-text");
  const photoEl = document.getElementById("geo-photo");
  const mapEl = document.getElementById("geo-map");
  const guessBtn = document.getElementById("geo-guess-btn");
  const resultBox = document.getElementById("geo-round-result");
  const resultBadge = document.getElementById("geo-round-badge");
  const resultDistance = document.getElementById("geo-round-distance");
  const nextWrap = document.getElementById("geo-next-wrap");
  const nextBtn = document.getElementById("geo-next-btn");
  const scoreEl = document.getElementById("geo-score");
  const finalBadgeEl = document.getElementById("geo-final-badge");
  const finalCommentEl = document.getElementById("geo-final-comment");
  const retryBtn = document.getElementById("geo-retry-btn");
  const reviewListEl = document.getElementById("geo-review-list");

  let order = [];
  let current = 0;
  let score = 0;
  let answerLog = [];
  let map = null;
  let guessMarker = null;
  let answerMarker = null;
  let answerCircle = null;
  let guessLatLng = null;
  let hasAnswered = false;

  function shuffledIndexes(n) {
    const arr = Array.from({ length: n }, (_, i) => i);
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  // 2点間の距離をメートルで計算(ハーバサイン公式)
  function distanceMeters(lat1, lng1, lat2, lng2) {
    const R = 6371000;
    const toRad = (deg) => (deg * Math.PI) / 180;
    const dLat = toRad(lat2 - lat1);
    const dLng = toRad(lng2 - lng1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  function ensureMap() {
    if (map) return;
    map = L.map(mapEl).setView(OZU_CENTER, OZU_ZOOM);
    L.tileLayer(GSI_TILE, { attribution: GSI_ATTR, maxZoom: 18 }).addTo(map);
    map.on("click", (e) => {
      if (hasAnswered) return;
      placeGuessMarker(e.latlng);
    });
  }

  function placeGuessMarker(latlng) {
    guessLatLng = latlng;
    if (guessMarker) {
      guessMarker.setLatLng(latlng);
    } else {
      guessMarker = L.marker(latlng, { draggable: true }).addTo(map);
      guessMarker.on("dragend", () => {
        guessLatLng = guessMarker.getLatLng();
      });
    }
    guessBtn.disabled = false;
  }

  function startGame() {
    order = shuffledIndexes(OZU_GEOGUESS_PHOTOS.length).slice(0, ROUND_LENGTH);
    current = 0;
    score = 0;
    answerLog = [];
    startScreen.style.display = "none";
    resultScreen.style.display = "none";
    gameScreen.style.display = "block";
    ensureMap();
    renderRound();
  }

  function renderRound() {
    const p = OZU_GEOGUESS_PHOTOS[order[current]];
    hasAnswered = false;
    guessLatLng = null;
    progressText.textContent = `第${current + 1}問 / 全${ROUND_LENGTH}問(正解数: ${score})`;
    photoEl.src = `../assets/img/geoguess/${p.file}`;
    photoEl.alt = "この写真の撮影場所を地図上で当ててください";

    if (guessMarker) {
      map.removeLayer(guessMarker);
      guessMarker = null;
    }
    if (answerMarker) {
      map.removeLayer(answerMarker);
      answerMarker = null;
    }
    if (answerCircle) {
      map.removeLayer(answerCircle);
      answerCircle = null;
    }
    map.setView(OZU_CENTER, OZU_ZOOM);
    setTimeout(() => map.invalidateSize(), 50);

    guessBtn.disabled = true;
    guessBtn.style.display = "inline-block";
    resultBox.classList.remove("show");
    nextWrap.classList.remove("show");
  }

  function submitGuess() {
    if (!guessLatLng || hasAnswered) return;
    hasAnswered = true;
    const p = OZU_GEOGUESS_PHOTOS[order[current]];
    const dist = distanceMeters(guessLatLng.lat, guessLatLng.lng, p.lat, p.lng);
    const isCorrect = dist <= CORRECT_RADIUS_M;
    if (isCorrect) score++;

    answerMarker = L.marker([p.lat, p.lng], {
      icon: L.divIcon({ className: "", html: '<span class="geo-answer-pin">正解</span>' }),
    }).addTo(map);
    answerCircle = L.circle([p.lat, p.lng], {
      radius: CORRECT_RADIUS_M,
      color: "#2e7d46",
      fillOpacity: 0.1,
    }).addTo(map);

    const bounds = L.latLngBounds([guessLatLng, [p.lat, p.lng]]);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 17 });

    resultBadge.textContent = isCorrect ? "○ 正解！" : "× 不正解";
    resultBadge.className = "geo-round-badge " + (isCorrect ? "correct" : "wrong");
    resultDistance.textContent = `実際の撮影場所との距離: 約${Math.round(dist)}m(正解ラインは半径${CORRECT_RADIUS_M}m以内)`;
    resultBox.classList.add("show");
    guessBtn.style.display = "none";
    nextWrap.classList.add("show");
    nextBtn.textContent = current === ROUND_LENGTH - 1 ? "結果を見る →" : "次の写真へ →";

    answerLog.push({ index: current, correct: isCorrect, distance: Math.round(dist) });
  }

  function nextRound() {
    current++;
    if (current >= ROUND_LENGTH) {
      showFinalResult();
    } else {
      renderRound();
    }
  }

  function showFinalResult() {
    gameScreen.style.display = "none";
    resultScreen.style.display = "block";
    scoreEl.textContent = score;

    if (score === ROUND_LENGTH) {
      finalBadgeEl.textContent = "🎉 全問正解！";
      finalBadgeEl.className = "geo-result-badge perfect";
      finalCommentEl.textContent = "お見事です。大洲の街をかなり歩き込んでいますね。";
    } else if (score >= Math.ceil(ROUND_LENGTH / 2)) {
      finalBadgeEl.textContent = "なかなかの土地勘";
      finalBadgeEl.className = "geo-result-badge pass";
      finalCommentEl.textContent = "半分以上正解でした。大洲通りと言っていいレベルです。";
    } else {
      finalBadgeEl.textContent = "もう少し";
      finalBadgeEl.className = "geo-result-badge fail";
      finalCommentEl.textContent = "また挑戦して、大洲の街に詳しくなってください。";
    }

    reviewListEl.innerHTML =
      `<p class="geo-review-title">全${ROUND_LENGTH}問の結果</p>` +
      answerLog
        .map((log, i) => {
          const markText = log.correct ? "○ 正解" : "× 不正解";
          const markClass = log.correct ? "correct" : "wrong";
          return `
      <div class="geo-review-item ${markClass}">
        <span class="geo-review-mark">${markText}</span>
        <span class="geo-review-body">第${i + 1}問. 距離 約${log.distance}m</span>
      </div>`;
        })
        .join("");
  }

  startBtn.addEventListener("click", startGame);
  guessBtn.addEventListener("click", submitGuess);
  nextBtn.addEventListener("click", nextRound);
  retryBtn.addEventListener("click", startGame);
});
