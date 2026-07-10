# Stressgraph — Pengukuran Tingkat Stress Mahasiswa

Aplikasi web untuk mengukur tingkat stress mahasiswa menggunakan **PSS-10** (Perceived
Stress Scale, instrumen psikologi baku internasional) yang dikombinasikan dengan
**AI Chat Assessment** untuk konteks personal tambahan.

## Struktur Project

```
stress-app/
├── backend/              <- Server API (Python + FastAPI)
│   ├── app/
│   │   ├── main.py        <- Semua endpoint API
│   │   ├── pss10.py       <- Logic scoring PSS-10
│   │   ├── ai_chat.py     <- Integrasi Gemini API + fallback lokal
│   │   ├── models.py      <- Struktur tabel database
│   │   ├── database.py    <- Koneksi SQLite
│   │   └── schemas.py     <- Validasi data
│   ├── requirements.txt
│   └── .env.example       <- Template untuk API key (salin jadi .env)
│
├── frontend/             <- Frontend statis / build Vite
│   ├── index.html        <- Entry page utama
│   ├── chatbot.html      <- Halaman chat AI
│   ├── app.js            <- Logika UI utama
│   ├── config.js         <- Konfigurasi alamat backend
│   ├── styles.css        <- Styling aplikasi
│   └── login/            <- Halaman login/registrasi
├── dist/                 <- Hasil build frontend untuk deployment
├── vite.config.js        <- Konfigurasi Vite dengan root frontend
└── README.md
```

## Cara Menjalankan (Langkah demi Langkah)

### Perbaikan Terbaru
- Frontend sekarang menampilkan detail error backend jika request `PSS-10` atau `ML` gagal.
- AI chat backend sudah lebih tahan terhadap package/API key yang belum terpasang; kalau provider eksternal tidak tersedia, server tetap memberikan fallback respons dukungan.
- `index.html` sekarang menggunakan host browser untuk membangun `API_BASE_URL`, sehingga tidak mudah rusak di environment lokal.
- Navigasi badge step kini aman dari error `Cannot read properties of null (reading 'classList')`.

### 1. Siapkan API Key Gemini (GRATIS, tanpa kartu kredit)

1. Buka https://aistudio.google.com/apikey → login dengan akun Google
2. Klik **Create API Key** → copy key-nya (format `AIzaSy...`)
3. Tidak perlu isi billing/kartu kredit untuk free tier ini

**Penting soal kuota gratis Gemini:** Google sering mengubah angka kuota free tier
tanpa pemberitahuan (pernah dipotong 50-80% sekaligus), jadi jangan jadikan angka
manapun yang Anda baca di internet sebagai patokan pasti. Aplikasi ini memakai model
`gemini-2.5-flash-lite` karena kuota & rate limit-nya biasanya lebih besar dibanding
`gemini-2.5-flash` biasa. Untuk cek kuota TERKINI khusus akun Anda, buka
https://aistudio.google.com/usage atau https://ai.google.dev/gemini-api/docs/rate-limits

**Tips menghemat kuota saat testing/development:**
- Setiap pesan di AI chat = 1 request ke Gemini. Satu sesi penuh (kuesioner + ~5-6
  balasan chat) bisa memakai 5-6 request.
- Kalau muncul error `429 RESOURCE_EXHAUSTED` saat testing, itu artinya kuota harian
  habis — tunggu sampai reset (tengah malam waktu Pasifik AS / sekitar siang-sore
  WIB hari berikutnya), atau buat API key baru di **Google Cloud project yang
  berbeda** (kuota terikat per-project, bukan per-key).
- Untuk demo pameran sungguhan, sebaiknya batasi jumlah orang yang mencoba sekaligus,
  atau siapkan 2-3 API key cadangan dari project Google Cloud berbeda sebagai backup.

### 2. Setup Backend

```bash
cd backend

# (Opsional tapi disarankan) buat virtual environment
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install semua dependency
pip install -r requirements.txt

# Salin file environment dan isi API key Anda
cp .env.example .env
# Lalu edit file .env, ganti GEMINI_API_KEY dengan key asli Anda
# Jika ingin menggunakan fallback Groq, tambahkan juga GROQ_API_KEY

# Jalankan server
uvicorn app.main:app --reload
or
python -m uvicorn app.main:app --reload
```

Jika berhasil, akan muncul tulisan server berjalan di `http://127.0.0.1:8000`.

**Cek apakah backend berjalan dengan benar:** buka browser ke
`http://localhost:8000/docs` — Anda akan melihat dokumentasi API otomatis (Swagger UI).
Ini bagus untuk ditunjukkan ke juri sebagai bukti arsitektur API yang rapi.

### 3. Setup Frontend

Frontend ini adalah file statis (HTML/CSS/JS biasa), jadi cukup dibuka langsung,
TAPI browser modern kadang membatasi `fetch()` dari file lokal (`file://`).
Cara paling aman: jalankan server statis sederhana juga.

```bash
# Jalankan dari root project, atau jika Anda menggunakan folder frontend, sesuaikan pathnya
python3 -m http.server 5500
```

jika menggunakan tailwind menggunakan perintah
```bash
npm run
npm run dev
```

Lalu buka browser ke: `http://localhost:5500`

### 4. Pastikan config.js sudah benar

Buka `config.js` (atau `frontend/config.js` jika Anda menjalankan frontend dari folder `frontend`), pastikan `API_BASE_URL` mengarah ke backend Anda:

```js
const API_BASE_URL = "http://localhost:8000";
```

Jika backend dan frontend dijalankan di komputer yang sama, biasanya tidak perlu diubah.

## Alur Pengguna (User Flow)

1. **Landing page** — perkenalan aplikasi + disclaimer
2. **Identitas** (opsional) — nama & jurusan
3. **Kuesioner PSS-10** — 10 pertanyaan, jawab dengan skala 0-4
4. **AI Chat Assessment** — AI menggali konteks tambahan (tidur, beban tugas, dukungan
   sosial, dll), lalu menghasilkan skor penyesuaian dan rekomendasi
5. **Hasil Akhir** — skor PSS-10, skor AI, grafik perbandingan, ringkasan, dan rekomendasi

## Tentang PSS-10

PSS-10 dikembangkan oleh Cohen, Kamarck, & Mermelstein (1983/1988) dan banyak dipakai
di riset internasional untuk mengukur *perceived stress* (persepsi stress, bukan
diagnosis klinis). Skor 0-40, dengan kategori umum:
- 0–13 = Rendah
- 14–26 = Sedang
- 27–40 = Tinggi

4 dari 10 pertanyaan adalah *positive items* yang di-reverse-score (logic ini sudah
diimplementasikan dengan benar di `backend/app/pss10.py` dan sudah ditest).

## Catatan Etis Penting

- Aplikasi ini adalah **alat bantu skrining**, BUKAN alat diagnosis klinis.
- AI tidak diperbolehkan berpura-pura menjadi psikolog/terapis (sudah diatur di
  system instruction `backend/app/ai_chat.py`).
- Jika pengguna menunjukkan tanda krisis (menyakiti diri, dll), aplikasi akan
  menampilkan informasi kontak bantuan darurat (Layanan Sejiwa 119 ext 8) dan
  menghentikan proses skoring — bukan mencoba menangani sendiri.
- Untuk presentasi/pameran, pastikan disclaimer ini tetap terlihat dan dijelaskan
  ke audiens, supaya jelas posisi aplikasi sebagai alat bantu, bukan pengganti
  tenaga profesional.

## Pengembangan Lanjutan (Ide untuk Skripsi/Presentasi)

Beberapa hal yang bisa ditambahkan jika ada waktu lebih:

- **Admin dashboard**: endpoint `/api/dashboard/stats` di backend sudah disiapkan
  untuk menampilkan statistik agregat (total responden, rata-rata skor, distribusi
  kategori) — tinggal dibuatkan halaman frontend-nya.
- **Model ML terlatih**: untuk nilai akademis lebih tinggi, bagian "AI adjustment"
  bisa diperkuat dengan model klasifikasi (Random Forest/Decision Tree) yang dilatih
  dari dataset student-stress publik (banyak tersedia di Kaggle), dikombinasikan
  dengan pendekatan LLM yang sudah ada.
- **Ekspor laporan PDF**: hasil assessment per mahasiswa bisa diekspor jadi PDF
  untuk dibawa konsultasi ke layanan konseling kampus.
- **Multi-bahasa**: untuk presentasi internasional, bisa ditambahkan toggle
  Bahasa Indonesia / English.

## Lisensi & Atribusi

PSS-10 adalah instrumen akademik yang bebas dipakai untuk riset/edukasi dengan
atribusi yang sesuai ke penulis aslinya (Cohen, S., Kamarck, T., & Mermelstein, R., 1983,
*A global measure of perceived stress*, Journal of Health and Social Behavior).
