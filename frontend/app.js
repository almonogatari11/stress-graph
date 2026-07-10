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
  "bunuh diri", "mengakhiri hidup", "menyakiti diri", "self harm",
  "ingin mati", "tidak ingin hidup", "mengakhiri semuanya"
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
      throw new Error(errBody.detail || `Request gagal (${res.status})`);
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
    `PERTANYAAN ${String(idx + 1).padStart(2, "0")} / ${total}`;
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
  nextBtn.textContent = idx === total - 1 ? "Lihat Hasil →" : "Selanjutnya →";
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
  nextBtn.innerHTML = `<span class="loading-spinner"></span> Memproses...`;

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
    nextBtn.textContent = "Lihat Hasil →";
    alert("Gagal mengirim kuesioner. Pastikan server backend berjalan.");
  }
}

// ---------------------------------------------------------------------------
// ML FORM
// ---------------------------------------------------------------------------

const ML_FIELD_LABELS = {
  anxiety_level: "Tingkat kecemasan (0-21)",
  self_esteem: "Kepercayaan diri (0-30)",
  mental_health_history: "Riwayat masalah kesehatan mental (0=Tidak, 1=Ya)",
  depression: "Tingkat depresi (0-27)",
  headache: "Frekuensi sakit kepala (0=Tidak pernah, 5=Selalu)",
  blood_pressure: "Tekanan darah (1=Normal, 2=Di atas normal, 3=Tinggi)",
  sleep_quality: "Kualitas tidur (0=Sangat buruk, 5=Sangat baik)",
  breathing_problem: "Masalah pernapasan (0=Tidak, 5=Sering)",
  noise_level: "Tingkat kebisingan lingkungan (0=Sangat sepi, 5=Sangat bising)",
  living_conditions: "Kondisi tempat tinggal (0=Sangat buruk, 5=Sangat baik)",
  safety: "Rasa aman di lingkungan (0=Tidak aman, 5=Sangat aman)",
  basic_needs: "Pemenuhan kebutuhan dasar (0=Tidak terpenuhi, 5=Terpenuhi)",
  academic_performance: "Performa akademik (0=Sangat buruk, 5=Sangat baik)",
  study_load: "Beban belajar/tugas (0=Sangat ringan, 5=Sangat berat)",
  teacher_student_relationship: "Hubungan dengan dosen/guru (0=Sangat buruk, 5=Sangat baik)",
  future_career_concerns: "Kekhawatiran karir masa depan (0=Tidak khawatir, 5=Sangat khawatir)",
  social_support: "Dukungan sosial dari keluarga/teman (0=Tidak ada, 5=Sangat kuat)",
  peer_pressure: "Tekanan dari teman sebaya (0=Tidak ada, 5=Sangat tinggi)",
  extracurricular_activities: "Keaktifan di kegiatan ekstrakurikuler (0=Tidak aktif, 5=Sangat aktif)",
  bullying: "Pengalaman perundungan/bullying (0=Tidak pernah, 5=Sering)",
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
  btn.innerHTML = `<span class="loading-spinner"></span> Memproses...`;

  try {
    const result = await apiCall("/api/ml/predict", {
      method: "POST",
      body: JSON.stringify(featureValues),
    });
    state.mlResult = result;
    state.mlFeatures = featureValues;

    // ✅ LANGSUNG ke halaman hasil tanpa perlu chat dulu
    renderFinalResult();
    goToView("hasil");
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "Lihat Hasil Pengukuran →";
    alert("Gagal memproses prediksi ML. Coba lagi.");
  }
}

// ---------------------------------------------------------------------------
// HALAMAN HASIL (langsung dari PSS-10 + ML)
// ---------------------------------------------------------------------------

function getInterpretation(pssCategory, mlCategory) {
  const categories = [pssCategory, mlCategory];
  const tinggi = categories.filter(c => c === "Tinggi").length;
  const sedang = categories.filter(c => c === "Sedang").length;

  if (tinggi >= 2) {
    return "Kedua metode menunjukkan tingkat stress TINGGI. Sangat disarankan untuk segera " +
      "menghubungi layanan konseling kampus atau berbicara dengan orang yang dipercaya. " +
      "Jangan ragu untuk mencari bantuan profesional.";
  } else if (tinggi === 1) {
    return "Terdapat indikasi stress yang cukup signifikan. Pertimbangkan untuk mengatur " +
      "jadwal lebih baik, istirahat cukup, dan berbagi cerita dengan teman atau konselor kampus.";
  } else if (sedang >= 1) {
    return "Tingkat stress kamu berada di level sedang. Pertahankan kebiasaan positif seperti " +
      "olahraga, tidur cukup, dan jaga koneksi sosial dengan teman dan keluarga.";
  } else {
    return "Tingkat stress kamu tergolong rendah. Tetap pertahankan gaya hidup sehat dan " +
      "keseimbangan antara belajar dan istirahat.";
  }
}

function renderFinalResult() {
  // Nama
  if (state.nama) {
    document.getElementById("result-nama-display").textContent =
      `Hasil untuk: ${state.nama}${state.jurusan ? " · " + state.jurusan : ""}`;
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
  el.textContent = category || "—";
  el.className = "score-category";
  if (category === "Rendah") el.classList.add("category-rendah");
  else if (category === "Sedang") el.classList.add("category-sedang");
  else if (category === "Tinggi") el.classList.add("category-tinggi");
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
  const colorMap = { Rendah: "#6B9080", Sedang: "#D98E3F", Tinggi: "#C0533E" };
  const pssColor = colorMap[pssCategory] || "#0b66d1";
  const mlColor  = colorMap[mlCategory]  || "#0b66d1";

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
      `Halo${greetName}! Saya di sini untuk mendengarkan. ` +
      `Ceritakan apapun yang sedang kamu rasakan — tekanan kuliah, ` +
      `masalah sehari-hari, atau hal yang bikin kamu semangat. 😊`
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
      "Maaf, terjadi gangguan koneksi. Coba kirim pesan lagi ya."
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
