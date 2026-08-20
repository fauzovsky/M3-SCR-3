# Knowledge Base

Fakta produk statis (bukan vector database — lihat Section 1.1 & 3.1
dokumen: *"Knowledge Base menyediakan fakta produk terverifikasi berdasarkan
fact type"* dan *"dilarang menebak fakta yang tidak tersedia"*). Satu produk
demo aktif: `TSHIRT-01` (Essential Cotton T-Shirt, anak–remaja–dewasa).

## Isi folder

| File | Isi |
|---|---|
| `product_facts_v2.json` | 61 fact (60 publik + 1 internal-only), schema `product_facts.v3` |
| `knowledge_base.py` | Loader + fungsi retrieval `get_facts(fact_types)` |

## Struktur satu fact

```json
{
  "fact_id": "FACT-TS01-SIZE-M",
  "category": "SIZE_GUIDE_DEWASA",
  "question_trigger": ["ukuran M", "bb 55 ukuran apa"],
  "value": "Size M (dewasa): lingkar dada 96-100 cm, panjang baju 67 cm, ...",
  "fact_type": "SIZE_GUIDE"
}
```

- **`fact_type`** — nilai RESMI sesuai kontrak dokumen (Section 4.2/10.4):
  `PRICE_PROMO`, `SIZE_GUIDE`, `STOCK`, `PRODUCT_DETAIL`, `SHIPPING`,
  `FAQ_PLAYBOOK`, `CHECKOUT_GUIDE`. **Ini yang dipakai untuk mencocokkan
  `required_fact_types` dari Action Engine.**
- **`category`** — sub-tag granular internal (mis. `SIZE_GUIDE_ANAK` vs
  `SIZE_GUIDE_DEWASA_LOKAL`), dipertahankan untuk kebutuhan organisasi/QA tim,
  **bukan** untuk logic pencocokan kontrak.
- **`question_trigger`** — contoh pertanyaan pemicu, referensi manual saat
  menyusun dataset training (lihat folder `Response Dataset`), bukan dipakai
  runtime.
- Fact dengan `"internal_only": true` (saat ini hanya
  `FACT-TS01-STANDARD-REFERENCE-001`, berisi rujukan standar teknis seperti
  SNI/ISO/OEKO-TEX) **tidak pernah** dikembalikan oleh `get_facts()` — jangan
  pernah dikirim ke prompt LLM atau ditampilkan ke penonton.

## Distribusi fact_type saat ini

| fact_type | Jumlah fact | Siap dipakai action resmi? |
|---|---|---|
| `SIZE_GUIDE` | 35 | Ya — `SHOW_SIZE_GUIDE` aktif |
| `PRODUCT_DETAIL` | 11 | Ya — `EXPLAIN_PRODUCT_DETAIL` aktif |
| `STOCK` | 6 | Ya — `CONFIRM_STOCK` aktif |
| `FAQ_PLAYBOOK` | 3 | Fact siap, `HANDLE_OBJECTION` **belum diaktifkan** |
| `PRICE_PROMO` | 3 | Ya — `EXPLAIN_PRICE_PROMO` aktif |
| `SHIPPING` | 2 | Fact siap, `EXPLAIN_SHIPPING` **belum diaktifkan** |
| `CHECKOUT_GUIDE` | 0 | **Belum ada fact sama sekali** — perlu dibuat dari nol |

## Cara pakai

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase()
facts = kb.get_facts(["SIZE_GUIDE"])            # sesuai required_fact_types dari Action Engine
one_fact = kb.get_by_id("FACT-TS01-SIZE-M")      # dipakai Validator utk cek used_fact_ids
```

Jalankan `python3 knowledge_base.py` untuk demo cepat (tampilkan jumlah fact
per `fact_type`).

## Catatan sumber & keterbatasan

`product_facts_v2.json` sudah transparan menandai bagian mana yang
benar-benar dicek ke dokumen standar (mis. komposisi serat, label
perawatan), dan mana yang masih *"nilai kerja tim untuk demo"* yang belum
diverifikasi ke dokumen resmi (lihat field `generated_note` di dalam file,
dan fact `FACT-TS01-STANDARD-REFERENCE-001` untuk detail acuan tiap
kategori). Satu fact (`FACT-TS01-SIZE-LOKAL-WANITA-XXXL-CAUTION`) secara
eksplisit menandai kemungkinan data sumber salah cetak — dibiarkan apa
adanya sebagai contoh kasus `needs_fallback=true` di dataset training
(lihat folder `Response Dataset`), **bukan** untuk dijawab pasti ke
penonton.

## Kalau mau lanjut mengaktifkan action yang masih tertunda

- `SHIPPING_FRICTION`/`OBJECTION_SPIKE`: fact sudah siap (`fact_type=SHIPPING`
  dan `fact_type=FAQ_PLAYBOOK`), tinggal tambah rule di
  `../Action Engine/action_rules.json` + dataset di `../Response Dataset/`.
- `PURCHASE_MOMENT`: perlu tambah fact baru dengan `fact_type=CHECKOUT_GUIDE`
  dulu (mis. cara checkout, syarat COD, cara pakai voucher saat checkout)
  sebelum bisa lanjut ke rule/dataset.
