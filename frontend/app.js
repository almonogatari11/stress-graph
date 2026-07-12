// ============================================================================
// app.js — Stressgraph
// Alur: Landing → Identitas → PSS-10 → ML Form → HASIL LANGSUNG → AI Chat (opsional)
// ============================================================================

// ---------------------------------------------------------------------------
// STATE GLOBAL
// ---------------------------------------------------------------------------
const state = {
  assessmentId: null,
  nama: "",
  jurusan: "",
  questions: [],
  likertLabels: [],
  currentQuestionIndex: 0,
  answers: [],
  pssResult: null,
  mlResult: null,
  mlFeatures: {},
  chatStarted: false,
};

const CRISIS_KEYWORDS = [
  // Indonesian
  "bunuh diri", "mengakhiri hidup", "menyakiti diri", "ingin mati", "tidak ingin hidup", "mengakhiri semuanya",
  // English equivalents and common phrases
  "suicide", "suicidal", "kill myself", "end my life", "want to die", "i want to die", "hurt myself", "self-harm", "self harm",
  // methods (helpful to catch urgent phrases)
  "cut myself", "cutting", "hang myself", "poison myself", "jump off", "jump from building",
];

// ---------------------------------------------------------------------------
// NAVIGASI
// ---------------------------------------------------------------------------

function goToView(viewName) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(`view-${viewName}`).classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (viewName === "kuesioner" && state.questions.length === 0) {
    loadQuestions();
  }
}

function resetApp() {
  state.assessmentId = null;
  state.nama = "";
  state.jurusan = "";
  state.currentQuestionIndex = 0;
  state.answers = new Array(10).fill(null);
  state.pssResult = null;
  state.mlResult = null;
  state.mlFeatures = {};
  state.chatStarted = false;

  document.getElementById("input-nama").value = "";
  document.getElementById("input-jurusan").value = "";
  document.getElementById("identitas-step").style.display = "block";
  document.getElementById("quiz-step").style.display = "none";
  document.getElementById("chat-messages").innerHTML = "";
  document.getElementById("chat-section").style.display = "none";
  const cb = document.getElementById("crisis-banner");
  if (cb) cb.classList.remove("show");

  goToView("landing");
}

// ---------------------------------------------------------------------------
// HELPER API
// ---------------------------------------------------------------------------

async function apiCall(path, options = {}) {
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Request failed (${res.status})`);
    }
    return await res.json();
  } catch (err) {
    console.error("API error:", err);
    throw err;
  }
}

// ---------------------------------------------------------------------------
// KUESIONER PSS-10
// ---------------------------------------------------------------------------

async function loadQuestions() {
  const data = await apiCall("/api/pss10/questions");
  state.questions = data.questions;
  state.likertLabels = data.likert_labels;
  state.answers = new Array(state.questions.length).fill(null);
}

function startQuestionnaire() {
  state.nama = document.getElementById("input-nama").value.trim();
  state.jurusan = document.getElementById("input-jurusan").value.trim();
  document.getElementById("identitas-step").style.display = "none";
  document.getElementById("quiz-step").style.display = "block";
  state.currentQuestionIndex = 0;
  renderQuestion();
}

function renderQuestion() {
  const idx = state.currentQuestionIndex;
  const q   = state.questions[idx];
  const total = state.questions.length;

  document.getElementById("question-number").textContent =
    `QUESTION ${String(idx + 1).padStart(2, "0")} / ${total}`;
  document.getElementById("question-text").textContent = q.text;
  document.getElementById("progress-fill").style.width = `${((idx + 1) / total) * 100}%`;

  const container = document.getElementById("likert-options");
  container.innerHTML = "";
  state.likertLabels.forEach((label, value) => {
    const el = document.createElement("div");
    el.className = "likert-option" + (state.answers[idx] === value ? " selected" : "");
    el.innerHTML = `<span class="likert-dot"></span><span class="likert-label">${label}</span>`;
    el.onclick = () => selectAnswer(value);
    container.appendChild(el);
  });

  const prevBtn = document.getElementById("btn-prev");
  const nextBtn = document.getElementById("btn-next");
  prevBtn.disabled = idx === 0;
  prevBtn.style.visibility = idx === 0 ? "hidden" : "visible";
  nextBtn.disabled = state.answers[idx] === null;
  nextBtn.textContent = idx === total - 1 ? "View Results →" : "Next →";
}

function selectAnswer(value) {
  state.answers[state.currentQuestionIndex] = value;
  renderQuestion();
}

function prevQuestion() {
  if (state.currentQuestionIndex > 0) {
    state.currentQuestionIndex--;
    renderQuestion();
  }
}

async function nextQuestion() {
  const isLast = state.currentQuestionIndex === state.questions.length - 1;
  if (!isLast) {
    state.currentQuestionIndex++;
    renderQuestion();
  } else {
    await submitPSS10();
  }
}

async function submitPSS10() {
  const nextBtn = document.getElementById("btn-next");
  nextBtn.disabled = true;
  nextBtn.innerHTML = `<span class="loading-spinner"></span> Processing...`;

  try {
    const result = await apiCall("/api/pss10/submit", {
      method: "POST",
      body: JSON.stringify({
        nama: state.nama || null,
        jurusan: state.jurusan || null,
        answers: state.answers,
      }),
    });
    state.assessmentId = result.assessment_id;
    state.pssResult = result;

    goToView("ml");
    await renderMLForm();
  } catch (err) {
    nextBtn.disabled = false;
    nextBtn.textContent = "View Results →";
    alert("Failed to submit questionnaire. Ensure the backend server is running.");
  }
}

// ---------------------------------------------------------------------------
// ML FORM
// ---------------------------------------------------------------------------

const ML_FIELD_LABELS = {
  anxiety_level: "Anxiety level (0-21)",
  self_esteem: "Self-esteem (0-30)",
  mental_health_history: "History of mental health issues (0=No, 1=Yes)",
  depression: "Depression severity (0-27)",
  headache: "Headache frequency (0=Never, 5=Always)",
  blood_pressure: "Blood pressure (1=Normal, 2=Above normal, 3=High)",
  sleep_quality: "Sleep quality (0=Very poor, 5=Very good)",
  breathing_problem: "Breathing problems (0=None, 5=Frequent)",
  noise_level: "Room noise level (0=Very quiet, 5=Very noisy)",
  living_conditions: "Living conditions (0=Very poor, 5=Very good)",
  safety: "Perceived safety (0=Not safe, 5=Very safe)",
  basic_needs: "Basic needs fulfillment (0=Not met, 5=Met)",
  academic_performance: "Academic performance (0=Very poor, 5=Very good)",
  study_load: "Study load (0=Very light, 5=Very heavy)",
  teacher_student_relationship: "Teacher-student relationship (0=Very poor, 5=Very good)",
  future_career_concerns: "Future career concerns (0=Not worried, 5=Very worried)",
  social_support: "Social support (0=None, 5=Strong)",
  peer_pressure: "Peer pressure (0=None, 5=High)",
  extracurricular_activities: "Extracurricular activity level (0=None, 5=High)",
  bullying: "Bullying experience (0=Never, 5=Often)",
};

async function renderMLForm() {
  const data = await apiCall("/api/ml/features");
  const container = document.getElementById("ml-form-fields");
  container.innerHTML = "";

  data.features.forEach(feat => {
    const label = ML_FIELD_LABELS[feat] || feat;
    const div = document.createElement("div");
    div.className = "field-group";
    div.innerHTML = `
      <label for="ml_${feat}">${label}</label>
      <input type="number" id="ml_${feat}" min="0" max="30" value="0"
        style="width:100%;padding:10px 14px;border:1.5px solid var(--paper-line);
        border-radius:var(--radius);font-size:0.95rem;background:var(--paper);" />
    `;
    container.appendChild(div);
  });
}

async function submitMLFeatures() {
  const data = await apiCall("/api/ml/features");
  const featureValues = {};
  data.features.forEach(feat => {
    const el = document.getElementById(`ml_${feat}`);
    featureValues[feat] = el ? parseFloat(el.value) || 0 : 0;
  });

  const btn = document.getElementById("btn-submit-ml");
  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> Processing...`;

  try {
    const result = await apiCall("/api/ml/predict", {
      method: "POST",
      body: JSON.stringify(featureValues),
    });
    state.mlResult = result;
    state.mlFeatures = featureValues;

    renderFinalResult();
    goToView("hasil");
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "View Final Results →";
    alert("Failed to process ML prediction. Please try again.");
  }
}

// ---------------------------------------------------------------------------
// HALAMAN HASIL (langsung dari PSS-10 + ML)
// ---------------------------------------------------------------------------

function normalizeCategory(category) {
  if (!category) return null;
  const normalized = String(category).trim().toLowerCase();
  if (normalized === "rendah" || normalized === "low") return "Low";
  if (normalized === "sedang" || normalized === "moderate") return "Moderate";
  if (normalized === "tinggi" || normalized === "high") return "High";
  return category;
}

function getInterpretation(pssCategory, mlCategory) {
  const categories = [normalizeCategory(pssCategory), normalizeCategory(mlCategory)];
  const high = categories.filter(c => c === "High").length;
  const moderate = categories.filter(c => c === "Moderate").length;

  if (high >= 2) {
    return "Both methods indicate HIGH stress. Please contact campus counseling or a trusted professional as soon as possible.";
  } else if (high === 1) {
    return "There is a significant indication of stress. Consider improving rest, time planning, and sharing your concerns with friends or campus counselors.";
  } else if (moderate >= 1) {
    return "Your stress level is moderate. Maintain positive habits like exercise, adequate sleep, and social connection.";
  } else {
    return "Your stress level is low. Keep up healthy habits and balance between study and rest.";
  }
}

function renderFinalResult() {
  // Nama
  if (state.nama) {
    document.getElementById("result-nama-display").textContent =
      `Results for: ${state.nama}${state.jurusan ? " · " + state.jurusan : ""}`;
  }

  // PSS-10
  const pssScore = state.pssResult.total_score;
  const pssCategory = state.pssResult.category;
  document.getElementById("result-pss-score").textContent = `${pssScore}/40`;
  setCategoryBadge("result-pss-category", pssCategory);

  // ML
  const mlConfidence = state.mlResult ? state.mlResult.confidence : null;
  const mlCategory   = state.mlResult ? state.mlResult.predicted_category : null;
  if (mlConfidence !== null) {
    document.getElementById("result-ml-confidence").textContent = `${mlConfidence}%`;
    setCategoryBadge("result-ml-category", mlCategory);
  }

  // Interpretasi otomatis dari PSS + ML
  document.getElementById("result-interpretation").textContent =
    getInterpretation(pssCategory, mlCategory);

  // Grafik
  renderChart(pssScore, mlConfidence, pssCategory, mlCategory);
}

function setCategoryBadge(elementId, category) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const normalized = normalizeCategory(category);
  el.textContent = normalized || "—";
  el.className = "score-category";
  if (normalized === "Low") el.classList.add("category-rendah");
  else if (normalized === "Moderate") el.classList.add("category-sedang");
  else if (normalized === "High") el.classList.add("category-tinggi");
}

let chartInstance = null;

function renderChart(pssScore, mlConfidence, pssCategory, mlCategory) {
  const canvas = document.getElementById("resultChart");
  const fallback = document.getElementById("chart-fallback");

  if (typeof Chart === "undefined") {
    if (canvas) canvas.style.display = "none";
    if (fallback) fallback.style.display = "block";
    return;
  }

  const pssNormalized = Math.round((pssScore / 40) * 100);

  // Warna berdasarkan kategori
  const colorMap = { Low: "#6B9080", Moderate: "#D98E3F", High: "#C0533E" };
  const pssColor = colorMap[normalizeCategory(pssCategory)] || "#0b66d1";
  const mlColor  = colorMap[normalizeCategory(mlCategory)]  || "#0b66d1";

  if (chartInstance) chartInstance.destroy();

  chartInstance = new Chart(canvas, {
    type: "bar",
    data: {
      labels: ["PSS-10 (dinormalisasi 0-100)", "Random Forest (confidence %)"],
      datasets: [{
        data: [pssNormalized, mlConfidence || 0],
        backgroundColor: [pssColor, mlColor],
        borderRadius: 8,
        maxBarThickness: 100,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => `${ctx.parsed.y}%` } },
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: "#e6eef9" },
          ticks: { font: { family: "Inter" } },
        },
        x: {
          grid: { display: false },
          ticks: { font: { family: "Inter" } },
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// AI CHAT (opsional, muncul setelah klik tombol di halaman hasil)
// ---------------------------------------------------------------------------

function goToChat() {
  const chatSection = document.getElementById("chat-section");
  chatSection.style.display = "block";
  chatSection.scrollIntoView({ behavior: "smooth" });

  if (!state.chatStarted) {
    state.chatStarted = true;
    const greetName = state.nama ? `, ${state.nama}` : "";
    addChatBubble("assistant",
      `Hello${greetName}! I'm here to listen. ` +
      `Share whatever you're feeling — coursework pressure, daily worries, or things that lift you up. 😊`
    );
  }
}

function addChatBubble(role, content) {
  const container = document.getElementById("chat-messages");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = content;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
  const container = document.getElementById("chat-messages");
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble assistant typing";
  bubble.id = "typing-indicator";
  bubble.innerHTML = `<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>`;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  addChatBubble("user", message);
  input.value = "";

  // Cek kata kunci krisis
  const lower = message.toLowerCase();
  const isCrisis = CRISIS_KEYWORDS.some(kw => lower.includes(kw));
  if (isCrisis) {
    document.getElementById("crisis-banner").classList.add("show");
  }

  const sendBtn = document.getElementById("btn-send-chat");
  sendBtn.disabled = true;
  input.disabled = true;
  showTypingIndicator();

  const startTime = Date.now();

  try {
    const result = await apiCall("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({
        assessment_id: state.assessmentId,
        message: message,
      }),
    });

    // Minimum 2 detik typing indicator supaya terasa natural
    const elapsed = Date.now() - startTime;
    if (elapsed < 2000) {
      await new Promise(r => setTimeout(r, 2000 - elapsed));
    }

    removeTypingIndicator();
    addChatBubble("assistant", result.reply);

  } catch (err) {
    removeTypingIndicator();
    addChatBubble("assistant",
      "Sorry, there's a connection issue. Please try sending your message again."
    );
  } finally {
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

// ---------------------------------------------------------------------------
// INIT
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  state.answers = new Array(10).fill(null);
});