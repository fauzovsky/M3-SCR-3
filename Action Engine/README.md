# Action Engine

Mengubah agregat sinyal 60 detik (rolling window, hasil kerja M2/SCR-2) jadi
**satu** `AudienceSnapshot` dan **satu** `ActionDecision`, mengikuti aturan
deterministik di `action_rules.json`. Sesuai batas tanggung jawab di Section
3.1 dokumen: modul ini **tidak** memanggil LLM dan **tidak** menyusun kalimat
apa pun — hanya memutuskan *"apa yang harus dibicarakan"*, bukan *"bagaimana
mengucapkannya"*.

## Isi folder

| File | Isi |
|---|---|
| `action_engine.py` | Class `ActionEngine`, entry point `evaluate()` |
| `action_rules.json` | Konfigurasi threshold, tie-break, dan pemetaan state→action→fact_type |

## Kontrak output (selaras Section 10.4 & 11 dokumen)

```python
AudienceSnapshot(state, window_seconds, state_confidence, signals, evidence_comment_ids)
ActionDecision(selected_action, action_score, required_fact_types, reason)
```

## Status enum: 4 dari 8 pasang resmi sudah aktif

| audience_state | selected_action | required_fact_types | source_intents | Status |
|---|---|---|---|---|
| `SIZE_FRICTION` | `SHOW_SIZE_GUIDE` | `["SIZE_GUIDE"]` | `["SIZE_VARIANT"]` | ✅ Aktif |
| `STOCK_FRICTION` | `CONFIRM_STOCK` | `["STOCK"]` | `["STOCK_AVAILABILITY"]` | ✅ Aktif |
| `PRODUCT_INFO_GAP` | `EXPLAIN_PRODUCT_DETAIL` | `["PRODUCT_DETAIL"]` | `["PRODUCT_DETAIL"]` | ✅ Aktif |
| `PRICE_FRICTION` | `EXPLAIN_PRICE_PROMO` | `["PRICE_PROMO"]` | `["PRICE_PROMO"]` | ✅ Aktif |
| `SHIPPING_FRICTION` | `EXPLAIN_SHIPPING` | `["SHIPPING"]` | `["SHIPPING"]` | ⏸ Ditunda (fact KB sudah siap) |
| `OBJECTION_SPIKE` | `HANDLE_OBJECTION` | `["FAQ_PLAYBOOK"]` | `["OBJECTION_COMPLAINT"]` | ⏸ Ditunda (fact KB sudah siap) |
| `PURCHASE_MOMENT` | `GUIDE_CHECKOUT` | `["CHECKOUT_GUIDE"]` | `["PURCHASE_INTENT"]` | ⏸ Ditunda (fact KB **belum ada**) |
| `NO_CLEAR_SIGNAL` | `NO_ACTION` | `[]` | — (fallback) | ✅ Aktif |

3 state yang ditunda ada di `action_rules.json` key `not_yet_implemented`
(bukan di `audience_states` yang aktif) — sengaja dipisah supaya
`ActionEngine` tidak salah pakai rule yang belum lengkap datasetnya.
Kronologi kenapa ditunda ada di `../DECISIONS_LOG.md`.

## Kebijakan threshold & tie-break

- Sebuah `audience_state` baru dipilih kalau **DUA-DUANYA** terpenuhi
  (`mode: "AND"`): minimal 2 komentar pendukung dalam 60 detik, DAN
  confidence gabungan ≥ 0.7.
- Kalau lebih dari satu state lolos threshold di window yang sama:
  menang `priority_rank` terkecil dulu, baru `state_confidence` tertinggi.
  Urutan prioritas saat ini: `SIZE_FRICTION` (1) → `STOCK_FRICTION` (2) →
  `PRODUCT_INFO_GAP` (3) → `PRICE_FRICTION` (4).
- `action_score` sengaja dibuat sedikit lebih rendah dari `state_confidence`
  (margin tetap 3%) untuk membedakan "confidence NLP" vs "kepastian
  keputusan Action Engine sendiri".

## Cara jalankan

```bash
python3 action_engine.py
```

Menjalankan simulasi manual (bukan unit test formal) dengan window contoh:
4 komentar `SIZE_VARIANT` + 1 komentar `PRICE_PROMO` → harus menghasilkan
`SIZE_FRICTION`/`SHOW_SIZE_GUIDE` (karena `priority_rank` size lebih tinggi
dan yang lolos threshold cuma size).

## Yang perlu dikonfirmasi ke M2/SCR-2

`source_intents` di `action_rules.json` memakai Intent enum resmi dari
Section 4.1 dokumen (`PRICE_PROMO`, `SIZE_VARIANT`, `STOCK_AVAILABILITY`,
`PRODUCT_DETAIL`, `SHIPPING`, `PURCHASE_INTENT`, `OBJECTION_COMPLAINT`,
`IRRELEVANT_SPAM`) — **tapi ini belum pernah diverifikasi langsung ke kode
M2**, hanya diasumsikan dari dokumen. Kalau nama intent yang benar-benar
dikeluarkan model IndoBERTweet M2 berbeda, `action_rules.json` perlu
disesuaikan.

## Langkah lanjutan yang belum ada di sini (tanggung jawab M4)

`ActionDecision.required_fact_types` masih berupa daftar nama fact_type
(string) — pemanggilan `KnowledgeBase.get_facts(...)` (lihat
`../Knowledge Base/knowledge_base.py`) untuk benar-benar mengambil fact-nya
dilakukan di layer backend (M4), bukan di modul ini, supaya `ActionEngine`
tetap murni deterministik tanpa I/O tambahan.
