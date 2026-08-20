"""
Action Engine - LiveCoach AI (M3/SCR-3: LLM, Knowledge, Policy)

Tanggung jawab modul ini HANYA satu hal: mengubah agregat sinyal 60 detik
(hasil rolling window dari M2/SCR-2) menjadi SATU audience_snapshot dan
SATU action_decision, mengikuti aturan deterministik di action_rules.json.

Modul ini TIDAK memanggil LLM dan TIDAK menyusun kalimat apa pun -- itu
tanggung jawab Grounded LLM (langkah 3-4). Action Engine hanya memutuskan
"apa yang harus dibicarakan", bukan "bagaimana mengucapkannya".

Kontrak output selaras dengan bagian 10.4 dan 11 dokumen spesifikasi:
- AudienceSnapshot: state, window_seconds, state_confidence, signals, evidence_comment_ids
- ActionDecision: selected_action, action_score, required_fact_types

CATATAN INTEGRASI (perlu dikonfirmasi ke M2/SCR-2):
`source_intents` di action_rules.json sekarang memakai Intent enum RESMI dari
dokumen Section 4.1 (PRICE_PROMO, SIZE_VARIANT, STOCK_AVAILABILITY,
PRODUCT_DETAIL, dst) -- tetap perlu dikonfirmasi ke M2/SCR-2 karena itu output
asli model IndoBERTweet milik mereka, kode M3 belum pernah melihat kode M2
secara langsung.

RIWAYAT PERBAIKAN (lihat DECISIONS_LOG.md di root folder Lomba untuk detail):
action_rules.json sebelumnya (v1) memakai audience_state/selected_action
custom (mis. STOCK_COLOR_CONCERN, MATERIAL_SAFETY_CONCERN, SHOW_PROMO_INFO)
yang TIDAK cocok dengan enum resmi di Section 4.2 & 11 dokumen spesifikasi.
Per 19 Agustus 2026 ditulis ulang (v2) supaya persis memakai 8 enum resmi;
4 dari 8 pasang audience_state/selected_action sudah aktif (SIZE_FRICTION,
STOCK_FRICTION, PRODUCT_INFO_GAP, PRICE_FRICTION), 3 sisanya sengaja ditunda
(lihat key "not_yet_implemented" di action_rules.json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


RULES_PATH = Path(__file__).parent / "action_rules.json"


# ---------------------------------------------------------------------------
# Data contracts (selaras dengan TypeScript contract di dokumen bagian 11)
# ---------------------------------------------------------------------------

@dataclass
class AudienceSnapshot:
    state: str
    window_seconds: int
    state_confidence: float
    signals: Dict[str, int]
    evidence_comment_ids: List[str]


@dataclass
class ActionDecision:
    selected_action: str
    action_score: float
    required_fact_types: List[str]
    reason: str


@dataclass
class WindowIntentSignal:
    """Satu baris agregat dari rolling window 60 detik milik M2.
    intent -> (jumlah komentar pendukung, confidence rata-rata, contoh comment_id)
    """
    intent: str
    support_count: int
    avg_confidence: float
    evidence_comment_ids: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ActionEngine:
    def __init__(self, rules_path: Path = RULES_PATH):
        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules = json.load(f)

        self.threshold = self.rules["threshold_policy"]
        self.tie_break = self.rules["tie_break_policy"]
        self.states = {s["state"]: s for s in self.rules["audience_states"]}
        self.fallback = self.rules["fallback_state"]

    def _passes_threshold(self, support_count: int, confidence: float) -> bool:
        min_count = self.threshold["min_supporting_comments_60s"]
        min_conf = self.threshold["min_state_confidence"]
        if self.threshold["mode"] == "AND":
            return support_count >= min_count and confidence >= min_conf
        return support_count >= min_count or confidence >= min_conf

    def evaluate(
        self,
        window_signals: List[WindowIntentSignal],
        window_seconds: int = 60,
    ) -> tuple[AudienceSnapshot, ActionDecision]:
        """Titik masuk utama. Dipanggil backend setiap kali rolling window
        60 detik diperbarui (bagian 3.2 dokumen: "Backend memperbarui
        rolling window 60 detik... Jika sinyal cukup, Action Engine memilih
        satu action").
        """

        # 1. Map tiap WindowIntentSignal ke audience_state yang relevan,
        #    lalu saring yang lolos threshold.
        candidates = []
        for state_name, rule in self.states.items():
            relevant = [
                sig for sig in window_signals if sig.intent in rule["source_intents"]
            ]
            if not relevant:
                continue

            support_count = sum(s.support_count for s in relevant)
            # confidence gabungan: rata-rata tertimbang jumlah komentar
            total_conf = sum(s.avg_confidence * s.support_count for s in relevant)
            confidence = round(total_conf / support_count, 4) if support_count else 0.0

            if not self._passes_threshold(support_count, confidence):
                continue

            evidence_ids = [cid for s in relevant for cid in s.evidence_comment_ids][:3]

            candidates.append(
                {
                    "state": state_name,
                    "rule": rule,
                    "support_count": support_count,
                    "confidence": confidence,
                    "evidence_comment_ids": evidence_ids,
                }
            )

        # 2. Tidak ada yang lolos threshold -> NO_CLEAR_SIGNAL / NO_ACTION
        if not candidates:
            snapshot = AudienceSnapshot(
                state=self.fallback["state"],
                window_seconds=window_seconds,
                state_confidence=0.0,
                signals={"support_count": 0},
                evidence_comment_ids=[],
            )
            decision = ActionDecision(
                selected_action=self.fallback["selected_action"],
                action_score=0.0,
                required_fact_types=self.fallback["required_fact_types"],
                reason="Belum ada pola kuat dalam 60 detik terakhir.",
            )
            return snapshot, decision

        # 3. Tie-break: priority_rank ASC, lalu confidence DESC
        candidates.sort(
            key=lambda c: (c["rule"]["priority_rank"], -c["confidence"])
        )
        winner = candidates[0]
        rule = winner["rule"]

        snapshot = AudienceSnapshot(
            state=winner["state"],
            window_seconds=window_seconds,
            state_confidence=winner["confidence"],
            signals={"support_count": winner["support_count"]},
            evidence_comment_ids=winner["evidence_comment_ids"],
        )

        # action_score sengaja dibuat sedikit berbeda dari state_confidence
        # (NLP confidence vs kepastian keputusan Action Engine sendiri) --
        # kebijakan MVP: margin tetap 3%, angka final dibatasi 0-1.
        action_score = round(min(1.0, winner["confidence"] * 0.97), 4)

        decision = ActionDecision(
            selected_action=rule["selected_action"],
            action_score=action_score,
            required_fact_types=rule["required_fact_types"],
            reason=rule["reason_template"].format(support_count=winner["support_count"]),
        )

        return snapshot, decision


# ---------------------------------------------------------------------------
# Demo / sanity check manual (bukan unit test formal -- lihat catatan di bawah)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = ActionEngine()

    # Simulasi window 60 detik: 4 komentar soal ukuran, 1 soal harga
    window = [
        WindowIntentSignal(
            intent="SIZE_VARIANT",
            support_count=4,
            avg_confidence=0.91,
            evidence_comment_ids=["CMT-018", "CMT-014"],
        ),
        WindowIntentSignal(
            intent="PRICE_PROMO",
            support_count=1,
            avg_confidence=0.6,
            evidence_comment_ids=["CMT-020"],
        ),
    ]

    snapshot, decision = engine.evaluate(window)
    print("AudienceSnapshot:", snapshot)
    print("ActionDecision:", decision)
