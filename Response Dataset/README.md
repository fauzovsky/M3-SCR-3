# Response Dataset

Dataset (input, output) untuk fine-tuning Grounded LLM — lokasi **canonical**
(satu-satunya) untuk generator dan hasil dataset training. Folder `Validator`
mengambil dataset dari sini, bukan menyimpan salinan sendiri, supaya tidak
ada dua sumber kebenaran yang bisa saling beda (dataset drift).

## Isi folder

| File | Isi |
|---|---|
| `generate_response_dataset.py` | Script yang mendefinisikan seluruh 60 contoh & menulis `response_dataset.jsonl` |
| `response_dataset.jsonl` | Hasil generate — 1 baris = 1 contoh (input, output) |

## Format satu baris

```json
{
  "input": {
    "selected_action": "SHOW_SIZE_GUIDE",
    "audience_state": "SIZE_FRICTION",
    "evidence_comments": ["bb 55 ambil m atau l?", "aku bb 55 cocoknya apa ya"],
    "product_facts": [{"fact_id": "FACT-TS01-SIZE-M", "value": "Size M (dewasa): ..."}],
    "tone": "santai",
    "max_words": 35
  },
  "output": {
    "response_text": "Buat BB 55 kg pas banget di size M kak, ...",
    "used_fact_ids": ["FACT-TS01-SIZE-M"],
    "claims": [{"fact_id": "FACT-TS01-SIZE-M", "claim_text": "Size M cocok untuk BB 50-60 kg, ..."}],
    "needs_fallback": false
  }
}
```

Sesuai kontrak Section 4.3 & 10.4 dokumen. `input` = apa yang diterima LLM;
`output` = apa yang HARUS dihasilkan LLM dalam JSON.

## Distribusi saat ini (60 contoh, sudah 100% pakai enum resmi)

| selected_action | audience_state | Jumlah | needs_fallback=true |
|---|---|---|---|
| `SHOW_SIZE_GUIDE` | `SIZE_FRICTION` | 15 | 2 |
| `CONFIRM_STOCK` | `STOCK_FRICTION` | 15 | 2 |
| `EXPLAIN_PRODUCT_DETAIL` | `PRODUCT_INFO_GAP` | 15 | 2 |
| `EXPLAIN_PRICE_PROMO` | `PRICE_FRICTION` | 15 | 0 |

Tone tersebar: informatif 29, santai 19, energik 12 — supaya model belajar
menyesuaikan gaya bicara sesuai field `tone`, bukan menghafal satu gaya.

`EXPLAIN_SHIPPING`, `HANDLE_OBJECTION`, `GUIDE_CHECKOUT` **belum punya
contoh sama sekali** — lihat `../DECISIONS_LOG.md` §6 untuk alasan
ditunda dan urutan prioritas kalau mau dilanjutkan.

## Prinsip desain (tidak berubah dari versi sebelumnya)

- `response_text` HARUS bisa ditelusuri balik ke `used_fact_ids` — tidak ada
  angka/klaim yang tidak berasal dari `product_facts_v2.json`. Ini yang
  nanti dicek ulang oleh Validator, tapi harus sudah benar dari sini.
- `claims` menautkan tiap pernyataan faktual ke `fact_id` pendukungnya —
  dipakai Validator untuk cross-check angka.
- `needs_fallback=true` dipakai untuk beberapa "kasus sulit" (evidence
  ambigu / fakta yang diminta tidak tersedia) supaya model belajar MENOLAK
  mengarang, bukan cuma belajar menjawab yang gampang. Total 6 dari 60
  contoh (10%) sengaja dibuat begini.

## Cara jalankan

```bash
python3 generate_response_dataset.py
```

Menulis ulang `response_dataset.jsonl` dan mencetak ringkasan distribusi ke
terminal untuk sanity check cepat.

## Kalau mau menambah action baru (SHIPPING/OBJECTION/CHECKOUT)

1. Pastikan fact dengan `fact_type` yang sesuai sudah ada di
   `../Knowledge Base/product_facts_v2.json` (cek lewat
   `KnowledgeBase.get_facts(...)`).
2. Tambah blok `add(...)` baru di `generate_response_dataset.py` — pola dan
   gaya penulisan ikuti blok `ACTION` yang sudah ada (evidence realistis,
   tone bervariasi, sertakan 1-2 "kasus sulit" dengan `needs_fallback=True`).
3. Jalankan ulang script ini, lalu jalankan
   `../Validator/run_validation_report.py` untuk pastikan semua entry baru
   lolos validasi sebelum dipakai training.
