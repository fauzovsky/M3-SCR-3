# Validator

Memeriksa output LLM (`response_text`, `used_fact_ids`, `claims`,
`needs_fallback`) SEBELUM dikirim ke frontend, dan memutuskan
`validation_status`: `PASSED` atau `FALLBACK`. Ini komponen terakhir sebelum
Coach Card ditampilkan (Section 3.2 dokumen, step "Validator meloloskan
response atau menggantinya dengan fallback aman").

## Isi folder

| File | Isi |
|---|---|
| `validator.py` | Fungsi `validate()` + orkestrasi `run_with_validation()` (generate → validate → retry 1x → fallback template) |
| `run_validation_report.py` | Jalankan `validate()` ke semua baris `response_dataset.jsonl`, hasilkan laporan |
| `validation_report.json` | Laporan mesin (buat dibaca program lain / M4) |
| `validation_report.md` | Laporan manusia (buat submission/proposal) |

## Kebijakan validasi

1. **Retry sekali sebelum fallback.** Kalau gagal validasi, generate ulang
   1x dengan prompt koreksi (dikasih tahu persis check mana yang gagal),
   baru fallback kalau masih gagal juga. Latensi penting di live streaming,
   jadi tidak retry berkali-kali.
2. **Cross-check angka: KETAT untuk angka utama** (ukuran/lingkar dada/
   panjang/harga/gsm/persentase), **LONGGAR untuk angka kecil lain** yang
   tidak melekat ke satuan tersebut (mis. "2 orang nanya"). Angka spesifik
   dalam rentang yang disebut fact (mis. "55 kg" saat fact bilang "50-60
   kg") dianggap valid, tidak harus kutip rentang persis.
3. **Toleransi panjang:** `max_words` + 20%. Lewat dari itu baru gagal.

Urutan pemeriksaan: schema → fact_id ada di KB → fact_id memang termasuk
yang diberikan sebagai input (bukan halusinasi) → claims tertaut ke
used_fact_ids → angka utama ter-grounded → panjang respons.

## Fallback templates

Dipakai kalau LLM gagal validasi 2x (generate awal + 1 retry). Key-nya harus
persis sama dengan `selected_action` resmi:

```python
ACTION_FALLBACK_TEMPLATES = {
    "SHOW_SIZE_GUIDE": "...",
    "CONFIRM_STOCK": "...",
    "EXPLAIN_PRODUCT_DETAIL": "...",
    "EXPLAIN_PRICE_PROMO": "...",
    "NO_ACTION": "...",
}
```

`HANDLE_OBJECTION`, `EXPLAIN_SHIPPING`, `GUIDE_CHECKOUT` belum ada template
fallback-nya karena action-nya sendiri belum diaktifkan di Action Engine
(lihat `../DECISIONS_LOG.md`) — kalau lupa ditambah nanti, `.get(...,
ACTION_FALLBACK_TEMPLATES["NO_ACTION"])` di `validator.py` akan jadi
fallback darurat, tapi sebaiknya ditambah template yang sesuai action-nya.

## ⚠️ Perlu klarifikasi ke M1/Ketua

Dokumen spesifikasi punya **2 definisi `ValidationStatus` yang beda** di 2
bagian:
- Section 7.5 & contoh payload 10.4 → `validation_status: "PASSED"` atau
  `"FALLBACK"`
- Section 11 (Enum Registry) → `ValidationStatus: PASSED │ FAILED │ NOT_RUN`

`validator.py` saat ini ikut **Section 7.5/10.4** (`PASSED`/`FALLBACK`)
karena itu yang muncul di contoh JSON response nyata dan komponen Coach
Card. Ini keputusan sementara, bukan final — tolong konfirmasi ke ketua
sebelum dianggap definitif.

## Cara jalankan

```bash
python3 run_validation_report.py
```

Membaca `../Response Dataset/response_dataset.jsonl`, memvalidasi tiap
baris, menulis ulang `validation_report.json` dan `.md`. Hasil saat ini:
**60/60 PASSED (100%)**.

**Penting soal makna laporan ini:** laporan ini memvalidasi *dataset buatan
tangan* (kurasi manual tim), bukan output model LLM hasil QLoRA yang
sesungguhnya. Pass rate 100% artinya "dataset training sudah konsisten
dengan aturan Validator sendiri" — bukti bahwa data yang dipakai untuk
training bersih — **bukan** "model sudah teruji tidak berhalusinasi". Itu
baru bisa dibuktikan lewat `../LLM dengan QLoRA/qlora_inference_test.py`
setelah training beneran dijalankan di Colab.
