"""
Knowledge Base loader & retrieval helper - LiveCoach AI (M3/SCR-3)

Menjawab gap yang ditemukan saat review: sebelumnya tidak ada kode yang
menjembatani ActionDecision.required_fact_types (output Action Engine, lihat
../Action Engine/action_engine.py) dengan daftar fact aktual yang harus
dikirim ke Grounded LLM. Modul ini menyediakan jembatan itu.

Cara pakai (lihat juga blok __main__ di bawah untuk contoh langsung):

    from knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    facts = kb.get_facts(["SIZE_GUIDE"])          # -> List[dict fact_id + value]
    facts = kb.get_facts(["STOCK", "PRICE_PROMO"]) # boleh multi fact_type sekaligus

Catatan penting:
- Pencocokan required_fact_types dilakukan terhadap field "fact_type" (nilai resmi
  sesuai kontrak dokumen Section 4.2/10.4), BUKAN terhadap field "category" yang
  lebih granular (mis. SIZE_GUIDE_ANAK, SIZE_GUIDE_DEWASA_LOKAL). "category" tetap
  disimpan di data mentah untuk kebutuhan organisasi/QA internal tim, tapi tidak
  dipakai untuk logic pencocokan kontrak.
- Fact dengan internal_only=true (saat ini hanya FACT-TS01-STANDARD-REFERENCE-001)
  TIDAK PERNAH dikembalikan oleh get_facts(), supaya tidak pernah bocor ke prompt
  LLM atau ke penonton. Fact ini murni referensi standar teknis internal tim.
- required_fact_types untuk state SHIPPING_FRICTION / OBJECTION_SPIKE / PURCHASE_MOMENT
  (fact_type SHIPPING / FAQ_PLAYBOOK / CHECKOUT_GUIDE) SUDAH bisa di-query lewat modul
  ini (fact-nya sudah ditag), walau action_rules.json belum mengaktifkan ketiga state
  itu. Lihat README.md di folder ini dan di ../Action Engine/README.md untuk detail
  kenapa ketiga ini sengaja ditunda (bukan kelupaan).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

FACTS_PATH = Path(__file__).parent / "product_facts_v2.json"


class KnowledgeBase:
    def __init__(self, facts_path: Path = FACTS_PATH):
        with open(facts_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.schema_version: str = raw["schema_version"]
        self.product_id: str = raw["product_id"]
        self._facts: List[dict] = raw["facts"]
        self._by_id: Dict[str, dict] = {f["fact_id"]: f for f in self._facts}

    def get_facts(self, fact_types: List[str]) -> List[dict]:
        """Kembalikan semua fact publik (internal_only=false/tidak ada) yang
        fact_type-nya termasuk dalam `fact_types`. Urutan mengikuti urutan asli
        di product_facts_v2.json supaya deterministik antar pemanggilan."""
        wanted = set(fact_types)
        return [
            {"fact_id": f["fact_id"], "value": f["value"]}
            for f in self._facts
            if not f.get("internal_only") and f.get("fact_type") in wanted
        ]

    def get_by_id(self, fact_id: str) -> Optional[dict]:
        """Lookup satu fact by ID -- dipakai Validator untuk cek used_fact_ids."""
        f = self._by_id.get(fact_id)
        if f is None or f.get("internal_only"):
            return None
        return {"fact_id": f["fact_id"], "value": f["value"]}

    def all_public_fact_ids(self) -> List[str]:
        return [f["fact_id"] for f in self._facts if not f.get("internal_only")]


if __name__ == "__main__":
    kb = KnowledgeBase()
    print(f"Loaded {len(kb.all_public_fact_ids())} public facts (schema {kb.schema_version}).")

    for ft in ["SIZE_GUIDE", "STOCK", "PRICE_PROMO", "PRODUCT_DETAIL", "SHIPPING", "FAQ_PLAYBOOK", "CHECKOUT_GUIDE"]:
        matches = kb.get_facts([ft])
        print(f"  fact_type={ft:<15} -> {len(matches)} fact")

    print("\nContoh required_fact_types=['SIZE_GUIDE'] (potongan pertama):")
    for f in kb.get_facts(["SIZE_GUIDE"])[:3]:
        print(" -", f["fact_id"], ":", f["value"][:70], "...")
