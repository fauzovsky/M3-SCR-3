# LLM dengan QLoRA

Fine-tuning Grounded LLM LiveCoach AI. Sesuai Section 3.1 dokumen: LLM ini
**hanya** menyusun kalimat natural dari action, evidence, dan facts yang
diberikan — **dilarang** mengganti tindakan atau menambah klaim di luar itu.

## Isi folder

| File | Isi |
|---|---|
| `system_prompt.py` | System prompt — HARUS identik dipakai saat training & inference |
| `qlora_train.py` | Script training QLoRA (Google Colab, GPU) |
| `qlora_inference_test.py` | Sanity check adapter hasil training (Google Colab) |
| `requirements_qlora.txt` | Dependency Python khusus untuk training (bukan untuk sandbox lokal) |

## ⚠️ Status: kode ini BELUM PERNAH dijalankan end-to-end

Sandbox pengembangan tim tidak punya GPU dan tidak ada akses ke
huggingface.co, jadi `qlora_train.py` dan `qlora_inference_test.py` **hanya
disusun mengikuti pola QLoRA standar** (bitsandbytes 4-bit + peft LoRA + trl
SFTTrainer) — belum dites jalan beneran. **Wajib di-smoke-test dulu di
Google Colab sebelum dipakai untuk training penuh dan sebelum diserahkan ke
M4 untuk integrasi.**

## Konfigurasi

- Base model: `Qwen/Qwen2.5-1.5B-Instruct` (gampang di-swap ke varian 3B
  kalau kualitas 1.5B kurang — tinggal ganti konstanta `BASE_MODEL`).
- LoRA rank kecil (`r=8`), 4 epoch — dataset cuma 60 contoh (lihat folder
  `../Response Dataset/`), sengaja LoRA ringan supaya tidak overfit/hafalan.
  Grounding & format JSON "dijamin ganda" oleh `system_prompt.py` yang
  dipakai persis sama saat training maupun inference production.
- `qlora_inference_test.py` sengaja pakai prompt yang TIDAK ADA persis di
  dataset training — kalau hasilnya tetap bagus, itu tanda model
  generalisasi, bukan cuma menghafal.

## Cara pakai (di Google Colab, GPU T4 gratis)

```bash
# 1. Upload ke working directory Colab:
#    - product_facts_v2.json (dari ../Knowledge Base/)
#    - response_dataset.jsonl (dari ../Response Dataset/)
#    - system_prompt.py (file ini)
!pip install -r requirements_qlora.txt
!python qlora_train.py
# Adapter hasil training tersimpan di ./livecoach-qlora-adapter/
!python qlora_inference_test.py
```

Perhatikan: `qlora_train.py` mengasumsikan `response_dataset.jsonl` ada
satu folder dengan script itu sendiri (upload flat ke Colab, bukan struktur
folder bertingkat seperti di repo ini) — sesuaikan path kalau upload dengan
cara lain.

## Eval cases di `qlora_inference_test.py` (sudah diselaraskan ke enum resmi)

3 skenario uji, dua di antaranya sengaja beda dari contoh training persis:

1. `SHOW_SIZE_GUIDE` — kombinasi BB baru yang tidak ada persis di dataset.
2. `EXPLAIN_PRODUCT_DETAIL` (sebelumnya berlabel `EXPLAIN_MATERIAL` — lihat
   `../DECISIONS_LOG.md`) — pertanyaan bahan untuk konteks cuaca.
3. `CONFIRM_STOCK` (sebelumnya `CONFIRM_STOCK_COLOR`) — fact SENGAJA
   dikosongkan untuk menguji `needs_fallback=true` benar-benar terpicu saat
   fact tidak tersedia, bukan model mengarang.

## Yang perlu dipastikan sebelum training penuh

- `system_prompt.py` dipakai **identik** saat training (`qlora_train.py`)
  dan saat inference production (M4 akan memanggil lewat model adapter) —
  kalau beda, LoRA yang sudah dilatih bisa "kaget" dengan instruksi baru.
- Jalankan `../Validator/run_validation_report.py` dulu sebelum training —
  pastikan dataset 100% PASSED (saat ini memang sudah).
