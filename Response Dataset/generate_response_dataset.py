"""
Response Dataset Generator - LiveCoach AI (M3/SCR-3)

Menghasilkan dataset training untuk grounded LLM (dipakai di step 4: QLoRA).
Setiap baris = 1 contoh (input, output) sesuai kontrak bagian 4.3 & 10.4
dokumen spesifikasi:

  input  : selected_action, audience_state, evidence_comments (maks 3),
           product_facts (fact_id + value, hasil lookup dari required_fact_types),
           tone, max_words
  output : response_text, used_fact_ids, claims, needs_fallback

Prinsip desain:
- response_text HARUS bisa ditelusuri balik ke used_fact_ids -- tidak ada
  angka/klaim yang tidak berasal dari product_facts_v2.json. ini yang nanti
  dicek ulang oleh Validator (step 5), tapi harus sudah benar dari sini.
- claims: daftar pernyataan faktual di response_text, ditautkan ke fact_id
  pendukungnya -- dipakai Validator untuk cross-check angka/klaim.
- needs_fallback=true dipakai untuk beberapa "kasus sulit" (evidence ambigu /
  fakta yang diminta tidak tersedia produk) supaya model belajar MENOLAK
  mengarang, bukan cuma belajar menjawab yang gampang.
- tone bervariasi (santai / energik / informatif) tapi SEMUA tetap grounded
  di fact yang sama -- variasi ada di gaya bicara, bukan di kebenaran fakta.
  Sesuai keputusan: LLM yang nanti pilih tone sesuai konteks, bukan diatur
  programmer per kasus.

RIWAYAT PERBAIKAN (lihat DECISIONS_LOG.md di root folder Lomba):
Per 19 Agustus 2026, label selected_action/audience_state di seluruh 60 entry
diselaraskan ke enum resmi dokumen (Section 4.2/11) -- konten response_text,
evidence_comments, dan fact_id TIDAK berubah (sudah grounded dari awal), yang
berubah HANYA metadata label:
  CONFIRM_STOCK_COLOR        -> CONFIRM_STOCK        (state: STOCK_FRICTION)
  EXPLAIN_MATERIAL           -> EXPLAIN_PRODUCT_DETAIL (state: PRODUCT_INFO_GAP)
  SHOW_PROMO_INFO            -> EXPLAIN_PRICE_PROMO   (state: PRICE_FRICTION)
  SHOW_SIZE_GUIDE tidak berubah (state: SIZE_FRICTION, sudah sesuai dari awal).
File ini sekarang menjadi lokasi CANONICAL untuk generator + dataset (folder
"Response Dataset"); salinan yang sebelumnya ada di folder "Validator" sudah
dihapus supaya tidak ada dua sumber kebenaran yang bisa saling beda (dataset
drift). Validator meng-import dataset ini dari folder sini.
"""

import json
from pathlib import Path

FACTS_PATH = Path(__file__).parent.parent / "Knowledge Base" / "product_facts_v2.json"
OUT_PATH = Path(__file__).parent / "response_dataset.jsonl"

with open(FACTS_PATH, "r", encoding="utf-8") as f:
    _facts_raw = json.load(f)["facts"]
FACT = {f["fact_id"]: f["value"] for f in _facts_raw}

ENTRIES = []


def add(action, audience_state, evidence_comments, fact_ids, tone, max_words,
        response_text, claims, needs_fallback=False):
    ENTRIES.append({
        "input": {
            "selected_action": action,
            "audience_state": audience_state,
            "evidence_comments": evidence_comments,
            "product_facts": [{"fact_id": fid, "value": FACT[fid]} for fid in fact_ids if fid in FACT],
            "tone": tone,
            "max_words": max_words,
        },
        "output": {
            "response_text": response_text,
            "used_fact_ids": fact_ids,
            "claims": claims,
            "needs_fallback": needs_fallback,
        },
    })


# ===========================================================================
# ACTION 1: SHOW_SIZE_GUIDE  (audience_state: SIZE_FRICTION)
# ===========================================================================

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["bb 55 ambil m atau l?", "aku bb 55 cocoknya apa ya"],
    ["FACT-TS01-SIZE-M"], "santai", 35,
    "Buat BB 55 kg pas banget di size M kak, lingkar dada 96-100 cm, panjang baju 67 cm. Nyaman dipake, gak kesempitan!",
    [{"fact_id": "FACT-TS01-SIZE-M", "claim_text": "Size M cocok untuk BB 50-60 kg, lingkar dada 96-100 cm"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["kalau ada L langsung checkout", "size L muat gak buat aku"],
    ["FACT-TS01-SIZE-L"], "energik", 30,
    "Gaskeun size L nya kak! Lingkar dada 104-108 cm, cocok buat BB 60-72 kg. Buruan checkout sebelum kehabisan!",
    [{"fact_id": "FACT-TS01-SIZE-L", "claim_text": "Size L cocok BB 60-72 kg, lingkar dada 104-108 cm"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["aku 160 cm pilih size apa kak", "tinggi 160 cocok size berapa"],
    ["FACT-TS01-SIZE-M"], "informatif", 30,
    "Untuk tinggi badan 158-168 cm, size yang sesuai adalah M: lingkar dada 96-100 cm, panjang baju 67 cm.",
    [{"fact_id": "FACT-TS01-SIZE-M", "claim_text": "Size M cocok TB 158-168 cm"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["anak umur 5 tahun size berapa", "buat anak TB 108 size apa"],
    ["FACT-TS01-SIZE-KIDS-110"], "santai", 35,
    "Kalau anaknya TB sekitar 108 cm, pas nih ambil size 110 ya kak, usia acuan sekitar 5 tahun, lingkar dada 58 cm.",
    [{"fact_id": "FACT-TS01-SIZE-KIDS-110", "claim_text": "Size 110 cocok TB 105-110 cm, usia acuan 5 tahun"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["anak umur 7 tahun size berapa kak"],
    ["FACT-TS01-SIZE-KIDS-122"], "informatif", 28,
    "Untuk usia acuan 7 tahun, size yang sesuai adalah 122: tinggi badan 117-122 cm, lingkar dada sekitar 62 cm.",
    [{"fact_id": "FACT-TS01-SIZE-KIDS-122", "claim_text": "Size 122 untuk usia acuan 7 tahun, TB 117-122 cm"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["remaja umur 12 tahun size apa", "anak SMP TB 150 size berapa"],
    ["FACT-TS01-SIZE-TEEN-152"], "santai", 35,
    "Buat remaja TB sekitar 150 cm, cocok size 152 kak (Remaja M), usia acuan 12-13 tahun, lingkar dada 76 cm.",
    [{"fact_id": "FACT-TS01-SIZE-TEEN-152", "claim_text": "Size 152 (Remaja M) untuk TB 147-152 cm, usia 12-13 tahun"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["remaja mau masuk dewasa size apa dong"],
    ["FACT-TS01-SIZE-TEEN-164"], "energik", 32,
    "Nih buat yang badannya udah gede, size 164 (Remaja XL) pas banget, TB 159-164 cm, mendekati dewasa XS. Order sekarang!",
    [{"fact_id": "FACT-TS01-SIZE-TEEN-164", "claim_text": "Size 164 untuk TB 159-164 cm, mendekati dewasa XS"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["badan kecil banget size apa yg pas", "aku kurus size xs muat gak"],
    ["FACT-TS01-SIZE-XS"], "informatif", 28,
    "Size XS cocok untuk lingkar dada 84-88 cm, BB 38-45 kg, TB 148-158 cm.",
    [{"fact_id": "FACT-TS01-SIZE-XS", "claim_text": "Size XS untuk BB 38-45 kg, TB 148-158 cm"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["badan besar banget ada size gak", "bb 100 ada size nya ga"],
    ["FACT-TS01-SIZE-XXXL"], "santai", 32,
    "Tenang kak, ada size XXXL! Muat buat BB 95-108 kg, lingkar dada 128-132 cm. Aman kok!",
    [{"fact_id": "FACT-TS01-SIZE-XXXL", "claim_text": "Size XXXL untuk BB 95-108 kg"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["ini ukuran S nya versi lokal apa internasional", "size S kaki lima biasanya beda ga"],
    ["FACT-TS01-SIZE-LOKAL-METHOD-NOTE", "FACT-TS01-SIZE-LOKAL-PRIA-S"], "informatif", 40,
    "Size S versi lokal: Panjang 63 cm, Lebar ketiak-ke-ketiak 43 cm -- beda cara ukur dari versi internasional yang pakai lingkar dada penuh.",
    [{"fact_id": "FACT-TS01-SIZE-LOKAL-PRIA-S", "claim_text": "Size lokal Pria S: Panjang 63 cm, Lebar 43 cm"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["size lokal L cewek berapa cm ya"],
    ["FACT-TS01-SIZE-LOKAL-WANITA-L"], "santai", 30,
    "Size L lokal buat cewek itu Panjang 61 cm, Lebar 45 cm ya kak, diukur rata dari ketiak ke ketiak.",
    [{"fact_id": "FACT-TS01-SIZE-LOKAL-WANITA-L", "claim_text": "Size lokal Wanita L: Panjang 61 cm, Lebar 45 cm"}])

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["ukuran lokal XXL cowok berapa kak"],
    ["FACT-TS01-SIZE-LOKAL-PRIA-XXL"], "energik", 28,
    "Size lokal Pria XXL: Panjang 79 cm, Lebar 60 cm, paling gede tapi masih nyaman -- gas order kak!",
    [{"fact_id": "FACT-TS01-SIZE-LOKAL-PRIA-XXL", "claim_text": "Size lokal Pria XXL: Panjang 79 cm, Lebar 60 cm"}])

# --- kasus sulit / needs_fallback untuk SHOW_SIZE_GUIDE ---

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["bayi umur 6 bulan ada size gak kak"],
    [], "informatif", 35,
    "Untuk usia bayi di bawah kisaran size anak yang tersedia, mohon maaf belum ada ukuran yang sesuai di produk ini -- silakan cek size chart lengkap di halaman produk.",
    [], needs_fallback=True)

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["ukuran lokal XXXL cewek berapa ya kak"],
    ["FACT-TS01-SIZE-LOKAL-WANITA-XXXL-CAUTION"], "informatif", 40,
    "Untuk size lokal Wanita XXXL, data pastinya sedang kami verifikasi ulang -- untuk sementara silakan tanyakan langsung ke admin toko agar tidak salah ukuran.",
    [], needs_fallback=True)

add("SHOW_SIZE_GUIDE", "SIZE_FRICTION",
    ["tinggi 145 cm size berapa ya, anak apa remaja nih bingung"],
    ["FACT-TS01-SIZE-TEEN-146"], "informatif", 30,
    "Untuk TB sekitar 145 cm, masuk size 146 (Remaja S/M): TB 141-146 cm, lingkar dada sekitar 70 cm.",
    [{"fact_id": "FACT-TS01-SIZE-TEEN-146", "claim_text": "Size 146 untuk TB 141-146 cm"}])


# ===========================================================================
# ACTION 2: CONFIRM_STOCK  (audience_state: STOCK_FRICTION)
# ===========================================================================

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["yang hitam L masih ada?", "hitam masih ready ga"],
    ["FACT-TS01-COLOR-BLACK"], "santai", 25,
    "Masih ready kak, warna Hitam tersedia untuk semua ukuran S sampai XXXL.",
    [{"fact_id": "FACT-TS01-COLOR-BLACK", "claim_text": "Warna Hitam tersedia semua ukuran dewasa S-XXXL"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["putih ready ga size L", "warna putih masih ada gak"],
    ["FACT-TS01-COLOR-WHITE"], "informatif", 30,
    "Warna Putih tersedia untuk semua ukuran kecuali dewasa XXL dan XXXL yang stoknya sudah habis.",
    [{"fact_id": "FACT-TS01-COLOR-WHITE", "claim_text": "Putih habis untuk size XXL dan XXXL dewasa"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["ada warna apa aja sih kak"],
    ["FACT-TS01-COLOR-001"], "energik", 30,
    "Ada 5 warna kece nih: Hitam, Putih, Navy, Abu Misty, Maroon! Pilih yang paling kamu suka, gas checkout!",
    [{"fact_id": "FACT-TS01-COLOR-001", "claim_text": "Tersedia 5 warna: Hitam, Putih, Navy, Abu Misty, Maroon"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["size anak masih ada semua ga kak", "stok anak lengkap ga"],
    ["FACT-TS01-STOCK-KIDS"], "santai", 28,
    "Semua ukuran anak dari 92 sampai 128 masih tersedia lengkap di semua warna ya kak!",
    [{"fact_id": "FACT-TS01-STOCK-KIDS", "claim_text": "Ukuran anak 92-128 tersedia di semua warna"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["size remaja ready semua ga"],
    ["FACT-TS01-STOCK-TEEN"], "informatif", 32,
    "Seluruh ukuran remaja (134-164) tersedia, hanya warna Putih size 164 yang stoknya terbatas.",
    [{"fact_id": "FACT-TS01-STOCK-TEEN", "claim_text": "Ukuran remaja 134-164 tersedia, Putih 164 terbatas"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["dewasa full size ready ga kak"],
    ["FACT-TS01-STOCK-ADULT"], "santai", 28,
    "Ready kak, semua ukuran dewasa dari XS sampai XXXL tersedia (cek warna spesifiknya ya)!",
    [{"fact_id": "FACT-TS01-STOCK-ADULT", "claim_text": "Ukuran dewasa XS-XXXL tersedia"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["kapan restock warna putih xl", "restock kapan kak"],
    ["FACT-TS01-STOCK-RESTOCK"], "informatif", 30,
    "Untuk jadwal restock belum ada tanggal pasti, silakan pantau pengumuman resmi di halaman produk ya.",
    [{"fact_id": "FACT-TS01-STOCK-RESTOCK", "claim_text": "Tidak ada tanggal pasti untuk restock"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["navy nya ready ga size m"],
    ["FACT-TS01-COLOR-001"], "energik", 25,
    "Navy salah satu dari 5 warna yang tersedia, size M-nya gaskeun order sekarang kak!",
    [{"fact_id": "FACT-TS01-COLOR-001", "claim_text": "Navy termasuk 5 warna yang tersedia"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["ini beneran ready stock apa preorder"],
    ["FACT-TS01-STOCK-ADULT"], "informatif", 25,
    "Ini ready stock kak, bukan preorder, untuk ukuran dewasa XS-XXXL.",
    [{"fact_id": "FACT-TS01-STOCK-ADULT", "claim_text": "Status ready stock untuk ukuran dewasa"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["hitam size anak masih ada ga"],
    ["FACT-TS01-COLOR-BLACK", "FACT-TS01-STOCK-KIDS"], "santai", 30,
    "Warna Hitam untuk size anak masih lengkap kok kak, semua size 92-128 ready!",
    [{"fact_id": "FACT-TS01-COLOR-BLACK", "claim_text": "Hitam tersedia semua ukuran"},
     {"fact_id": "FACT-TS01-STOCK-KIDS", "claim_text": "Ukuran anak 92-128 tersedia"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["abu misty ready ga buat remaja"],
    ["FACT-TS01-COLOR-001", "FACT-TS01-STOCK-TEEN"], "energik", 30,
    "Abu Misty ready buat semua size remaja! Cus checkout sebelum warna favorit ini habis!",
    [{"fact_id": "FACT-TS01-COLOR-001", "claim_text": "Abu Misty termasuk warna tersedia"},
     {"fact_id": "FACT-TS01-STOCK-TEEN", "claim_text": "Ukuran remaja tersedia"}])

# --- kasus sulit ---

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["putih xxl ada ga kak, pengen banget"],
    ["FACT-TS01-COLOR-WHITE"], "informatif", 30,
    "Mohon maaf kak, warna Putih untuk size XXL saat ini stoknya habis. Warna lain di size yang sama masih tersedia.",
    [{"fact_id": "FACT-TS01-COLOR-WHITE", "claim_text": "Putih habis untuk size XXL dan XXXL"}], needs_fallback=False)

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["ada warna gold ga kak?", "ada rose gold ga"],
    [], "informatif", 30,
    "Mohon maaf, warna yang ditanyakan tidak tersedia untuk produk ini -- warna yang ada adalah Hitam, Putih, Navy, Abu Misty, dan Maroon.",
    [], needs_fallback=True)

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["maroon nya ready ga size xl", "maroon ada ga"],
    ["FACT-TS01-COLOR-001", "FACT-TS01-STOCK-ADULT"], "santai", 28,
    "Maroon ready kak buat size XL, semua ukuran dewasa masih tersedia!",
    [{"fact_id": "FACT-TS01-COLOR-001", "claim_text": "Maroon termasuk warna tersedia"},
     {"fact_id": "FACT-TS01-STOCK-ADULT", "claim_text": "Ukuran dewasa XS-XXXL tersedia"}])

add("CONFIRM_STOCK", "STOCK_FRICTION",
    ["semua warna ready buat size remaja ga sih"],
    ["FACT-TS01-COLOR-001", "FACT-TS01-STOCK-TEEN"], "informatif", 32,
    "Untuk ukuran remaja, kelima warna tersedia, kecuali Putih size 164 yang stoknya terbatas.",
    [{"fact_id": "FACT-TS01-COLOR-001", "claim_text": "5 warna tersedia"},
     {"fact_id": "FACT-TS01-STOCK-TEEN", "claim_text": "Ukuran remaja tersedia, Putih 164 terbatas"}])


# ===========================================================================
# ACTION 3: EXPLAIN_PRODUCT_DETAIL  (audience_state: PRODUCT_INFO_GAP)
# ===========================================================================

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["bahannya apa kak?", "ini bahannya apaan"],
    ["FACT-TS01-MATERIAL-COMPOSITION-001"], "santai", 35,
    "Bahannya 100% Cotton Combed 24s kak, ring-spun, gak ada campuran serat sintetis sama sekali. Adem dipake!",
    [{"fact_id": "FACT-TS01-MATERIAL-COMPOSITION-001", "claim_text": "100% Cotton Combed 24s, tanpa campuran sintetis"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["nerawang gak ini kalau dipake", "tebel gak bahannya"],
    ["FACT-TS01-MATERIAL-002"], "informatif", 30,
    "Kainnya tidak nerawang, gramasi 180 gsm dengan rajutan single knit rapat jadi tidak mudah melar.",
    [{"fact_id": "FACT-TS01-MATERIAL-002", "claim_text": "Gramasi 180 gsm, tidak nerawang, tidak mudah melar"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["aman ga buat kulit anak yang sensitif", "anakku alergi gampang, aman ga bahannya"],
    ["FACT-TS01-MATERIAL-SAFETY-001"], "informatif", 40,
    "Aman kak, kain diproduksi mengikuti kerangka acuan uji zat berbahaya OEKO-TEX Standard 100, dan untuk size anak kandungan timbal mengikuti batas acuan CPSIA maksimal 100 ppm.",
    [{"fact_id": "FACT-TS01-MATERIAL-SAFETY-001", "claim_text": "Diuji sesuai kerangka OEKO-TEX Standard 100, batas timbal sesuai CPSIA untuk size anak"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["simbol cucinya ngikutin standar apa", "cara baca label perawatannya gimana"],
    ["FACT-TS01-MATERIAL-CARE-STD-001"], "informatif", 32,
    "Simbol perawatan di label mengikuti sistem ISO 3758, mencakup instruksi cuci, pemutihan, pengeringan, dan setrika.",
    [{"fact_id": "FACT-TS01-MATERIAL-CARE-STD-001", "claim_text": "Simbol perawatan mengikuti ISO 3758"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["ada campuran polyester ga sih ini"],
    ["FACT-TS01-MATERIAL-COMPOSITION-001"], "santai", 30,
    "Nggak ada kak, ini murni 100% Cotton Combed 24s, gak dicampur polyester atau serat lain.",
    [{"fact_id": "FACT-TS01-MATERIAL-COMPOSITION-001", "claim_text": "100% Cotton Combed 24s tanpa campuran"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["gampang melar ga sih kalau sering dipake"],
    ["FACT-TS01-MATERIAL-002"], "energik", 28,
    "Nggak gampang melar kak! Rajutannya rapat 180 gsm, awet dipake gonta-ganti gaya. Order sekarang!",
    [{"fact_id": "FACT-TS01-MATERIAL-002", "claim_text": "Rajutan rapat 180 gsm, tidak mudah melar"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["adem ga bahannya buat cuaca panas"],
    ["FACT-TS01-MATERIAL-COMPOSITION-001", "FACT-TS01-MATERIAL-002"], "santai", 35,
    "Adem banget kak, 100% cotton combed yang breathable, gramasi pas 180 gsm gak bikin gerah.",
    [{"fact_id": "FACT-TS01-MATERIAL-COMPOSITION-001", "claim_text": "100% cotton combed"},
     {"fact_id": "FACT-TS01-MATERIAL-002", "claim_text": "Gramasi 180 gsm"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["ini beneran cotton combed atau cuma ngaku2"],
    ["FACT-TS01-MATERIAL-COMPOSITION-001"], "informatif", 35,
    "Betul, komposisinya 100% Cotton Combed 24s ring-spun sesuai yang tertera, tanpa campuran serat sintetis.",
    [{"fact_id": "FACT-TS01-MATERIAL-COMPOSITION-001", "claim_text": "100% Cotton Combed 24s ring-spun"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["boleh dry clean ga kalau bahannya ini"],
    ["FACT-TS01-MATERIAL-CARE-STD-001"], "informatif", 30,
    "Metode perawatan yang direkomendasikan mengikuti simbol pada label sesuai standar ISO 3758 -- cek simbol dry clean di label untuk kepastian.",
    [{"fact_id": "FACT-TS01-MATERIAL-CARE-STD-001", "claim_text": "Instruksi perawatan mengikuti simbol ISO 3758 di label"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["ada zat kimia berbahaya ga buat bayi baru lahir"],
    ["FACT-TS01-MATERIAL-SAFETY-001"], "informatif", 40,
    "Kain ini mengikuti kerangka acuan pengujian zat berbahaya OEKO-TEX Standard 100, namun untuk bayi baru lahir tetap disarankan cek label detail karena size infant belum tersedia di produk ini.",
    [{"fact_id": "FACT-TS01-MATERIAL-SAFETY-001", "claim_text": "Diuji sesuai kerangka OEKO-TEX Standard 100"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["kok murah, bahannya ori cotton beneran ga"],
    ["FACT-TS01-MATERIAL-COMPOSITION-001", "FACT-TS01-MATERIAL-002"], "energik", 38,
    "Beneran ori kak, 100% Cotton Combed 24s gramasi 180 gsm -- harga bersahabat tapi kualitas tetap dijaga. Yuk order!",
    [{"fact_id": "FACT-TS01-MATERIAL-COMPOSITION-001", "claim_text": "100% Cotton Combed 24s"},
     {"fact_id": "FACT-TS01-MATERIAL-002", "claim_text": "Gramasi 180 gsm"}])

# --- kasus sulit ---

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["bahannya bebas nikel ga buat yang alergi logam"],
    [], "informatif", 35,
    "Mohon maaf, kami belum punya data spesifik soal kandungan nikel untuk produk ini -- kalau ada riwayat alergi logam tertentu, disarankan konsultasi dulu sebelum membeli.",
    [], needs_fallback=True)

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["ini organic cotton bersertifikat GOTS bukan"],
    ["FACT-TS01-MATERIAL-COMPOSITION-001"], "informatif", 35,
    "Produk ini 100% Cotton Combed 24s, namun kami tidak memiliki data sertifikasi GOTS untuk produk ini -- mohon jangan disamakan dengan klaim organic bersertifikat.",
    [{"fact_id": "FACT-TS01-MATERIAL-COMPOSITION-001", "claim_text": "100% Cotton Combed 24s"}], needs_fallback=True)

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["bahannya combed apa carded sih ini"],
    ["FACT-TS01-MATERIAL-COMPOSITION-001"], "informatif", 30,
    "Bahannya Cotton Combed 24s (ring-spun) kak, bukan carded -- serat sudah disisir jadi lebih halus.",
    [{"fact_id": "FACT-TS01-MATERIAL-COMPOSITION-001", "claim_text": "Cotton Combed 24s ring-spun"}])

add("EXPLAIN_PRODUCT_DETAIL", "PRODUCT_INFO_GAP",
    ["cocok ga buat kulit anak yang gampang gatal"],
    ["FACT-TS01-MATERIAL-SAFETY-001", "FACT-TS01-MATERIAL-COMPOSITION-001"], "santai", 38,
    "Cocok kak, ini 100% cotton combed yang lembut, dan diuji sesuai kerangka OEKO-TEX Standard 100 buat memastikan aman di kulit.",
    [{"fact_id": "FACT-TS01-MATERIAL-SAFETY-001", "claim_text": "Diuji sesuai kerangka OEKO-TEX Standard 100"},
     {"fact_id": "FACT-TS01-MATERIAL-COMPOSITION-001", "claim_text": "100% cotton combed"}])


# ===========================================================================
# ACTION 4: EXPLAIN_PRICE_PROMO  (audience_state: PRICE_FRICTION)
# ===========================================================================

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["harganya berapa kak", "berapaan ini"],
    ["FACT-TS01-PRICE-001"], "informatif", 20,
    "Harga normal Rp 89.000 per pcs kak.",
    [{"fact_id": "FACT-TS01-PRICE-001", "claim_text": "Harga normal Rp 89.000"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["ada promo gak buat yang beli 2", "beli 2 dapet diskon ga"],
    ["FACT-TS01-PROMO-001"], "energik", 35,
    "Ada dong! Beli 2 pcs cuma Rp 159.000, hemat Rp 19.000 selama live ini aja. Jangan sampai kelewatan!",
    [{"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Beli 2 pcs Rp 159.000, hemat Rp 19.000"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["bisa pake voucher toko ga"],
    ["FACT-TS01-PROMO-002"], "informatif", 30,
    "Voucher toko bisa digunakan sesuai ketentuan platform, tidak ada voucher tambahan khusus dari host di luar itu.",
    [{"fact_id": "FACT-TS01-PROMO-002", "claim_text": "Voucher toko sesuai ketentuan platform"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["mahal amat sih, ada diskon ga"],
    ["FACT-TS01-PRICE-001", "FACT-TS01-PROMO-001"], "santai", 35,
    "Harga normalnya Rp 89.000 kak, tapi kalau ambil 2 pcs jadi Rp 159.000 aja, lebih hemat!",
    [{"fact_id": "FACT-TS01-PRICE-001", "claim_text": "Harga normal Rp 89.000"},
     {"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Promo 2 pcs Rp 159.000"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["promo ini sampe kapan kak"],
    ["FACT-TS01-PROMO-001"], "energik", 25,
    "Promo beli 2 Rp 159.000 ini cuma berlaku selama live berlangsung -- buruan checkout sekarang!",
    [{"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Promo berlaku selama sesi live"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["kalo beli 3 gimana ada potongan lagi ga"],
    ["FACT-TS01-PROMO-001", "FACT-TS01-PRICE-001"], "informatif", 35,
    "Promo resmi yang berlaku saat ini adalah beli 2 pcs Rp 159.000; untuk kombinasi jumlah lain mengikuti harga normal Rp 89.000 per pcs.",
    [{"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Promo hanya berlaku untuk beli 2 pcs seharga Rp 159.000"},
     {"fact_id": "FACT-TS01-PRICE-001", "claim_text": "Harga normal Rp 89.000 per pcs"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["gimana caranya dapetin harga promo"],
    ["FACT-TS01-PROMO-001"], "santai", 30,
    "Gampang kak, tinggal checkout 2 pcs aja langsung otomatis dapet harga Rp 159.000 selama live berlangsung.",
    [{"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Beli 2 pcs otomatis Rp 159.000"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["harganya sama semua size ga sih"],
    ["FACT-TS01-PRICE-001"], "informatif", 25,
    "Sama kak, harga Rp 89.000 berlaku untuk semua ukuran anak, remaja, dan dewasa.",
    [{"fact_id": "FACT-TS01-PRICE-001", "claim_text": "Harga sama untuk semua ukuran"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["ada kode voucher khusus dari host ga"],
    ["FACT-TS01-PROMO-002"], "santai", 30,
    "Untuk voucher tambahan khusus dari host belum ada kak, tapi tetap bisa pakai voucher toko yang berlaku di platform.",
    [{"fact_id": "FACT-TS01-PROMO-002", "claim_text": "Tidak ada voucher tambahan khusus host"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["worth it ga beli 2 pcs"],
    ["FACT-TS01-PROMO-001"], "energik", 30,
    "Worth it banget kak! Beli 2 pcs cuma Rp 159.000, udah hemat Rp 19.000 dibanding beli satuan. Gas checkout!",
    [{"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Beli 2 pcs hemat Rp 19.000 dibanding harga satuan"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["diskonnya gede ga sih worth ga checkout sekarang"],
    ["FACT-TS01-PRICE-001", "FACT-TS01-PROMO-001"], "energik", 35,
    "Lumayan banget kak! Harga normal Rp 89.000 per pcs, tapi kalau ambil 2 pcs cuma Rp 159.000 -- checkout sekarang mumpung live!",
    [{"fact_id": "FACT-TS01-PRICE-001", "claim_text": "Harga normal Rp 89.000 per pcs"},
     {"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Beli 2 pcs jadi Rp 159.000"}])

# --- kasus sulit ---

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["bisa nego harga ga kak"],
    ["FACT-TS01-PRICE-001", "FACT-TS01-PROMO-001"], "santai", 30,
    "Untuk harga live ini fixed ya kak, Rp 89.000 per pcs atau Rp 159.000 untuk 2 pcs, belum bisa nego lagi.",
    [{"fact_id": "FACT-TS01-PRICE-001", "claim_text": "Harga fixed Rp 89.000 per pcs"},
     {"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Harga fixed Rp 159.000 untuk 2 pcs"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["ada flash sale jam 12 malam ga kak"],
    [], "informatif", 35,
    "Mohon maaf, kami tidak punya informasi soal flash sale di luar promo yang sedang berjalan saat ini -- pantau terus untuk info promo berikutnya.",
    [], needs_fallback=True)

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["kalo beli 1 doang boleh ga, ga mau 2"],
    ["FACT-TS01-PRICE-001"], "santai", 25,
    "Boleh banget kak, beli 1 pcs tetap bisa, harganya Rp 89.000.",
    [{"fact_id": "FACT-TS01-PRICE-001", "claim_text": "Beli 1 pcs harga Rp 89.000"}])

add("EXPLAIN_PRICE_PROMO", "PRICE_FRICTION",
    ["ongkirnya masuk promo juga ga kak"],
    ["FACT-TS01-PROMO-001"], "informatif", 32,
    "Promo Rp 159.000 untuk 2 pcs itu harga produk saja, ongkir dihitung terpisah otomatis oleh sistem checkout.",
    [{"fact_id": "FACT-TS01-PROMO-001", "claim_text": "Promo beli 2 pcs Rp 159.000 harga produk"}])


with open(OUT_PATH, "w", encoding="utf-8") as f:
    for entry in ENTRIES:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

print(f"Total entries: {len(ENTRIES)}")
from collections import Counter
print(Counter(e["input"]["selected_action"] for e in ENTRIES))
print(Counter(e["input"]["tone"] for e in ENTRIES))
print("needs_fallback=True count:", sum(1 for e in ENTRIES if e["output"]["needs_fallback"]))
