"""
Menjalankan Validator (validator.py) ke setiap baris response_dataset.jsonl
(sekarang di folder "Response Dataset", lihat DATASET_PATH) dan menyimpan
hasilnya sebagai file laporan -- bukti bahwa dataset training yang dipakai
untuk QLoRA (step 4) sudah lolos aturan Validator (step 5) sebelum dipakai.

PENTING: laporan ini memvalidasi DATASET BUATAN TANGAN (kurasi manual tim),
bukan output model LLM hasil QLoRA yang sesungguhnya -- QLoRA belum pernah
dijalankan end-to-end karena sandbox pengembangan tidak punya GPU (lihat
README di folder "LLM dengan QLoRA"). Pass rate 100% di sini artinya "dataset
training sudah konsisten dengan aturan Validator", BUKAN "model sudah teruji
tidak berhalusinasi" -- itu baru bisa dibuktikan lewat qlora_inference_test.py
setelah training beneran jalan di Colab.
"""

import json
from pathlib import Path

from validator import validate

DATASET_PATH = Path(__file__).parent.parent / "Response Dataset" / "response_dataset.jsonl"
REPORT_JSON_PATH = Path(__file__).parent / "validation_report.json"
REPORT_MD_PATH = Path(__file__).parent / "validation_report.md"


def main():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]

    results = []
    for i, entry in enumerate(entries):
        raw = json.dumps(entry["output"], ensure_ascii=False)
        result = validate(raw, entry["input"]["product_facts"], entry["input"]["max_words"])
        results.append(
            {
                "index": i,
                "selected_action": entry["input"]["selected_action"],
                "response_text": entry["output"]["response_text"],
                "validation_status": result.validation_status,
                "failed_checks": result.failed_checks,
            }
        )

    total = len(results)
    passed = sum(1 for r in results if r["validation_status"] == "PASSED")
    failed = total - passed

    by_action = {}
    for r in results:
        a = r["selected_action"]
        by_action.setdefault(a, {"total": 0, "passed": 0})
        by_action[a]["total"] += 1
        if r["validation_status"] == "PASSED":
            by_action[a]["passed"] += 1

    # --- simpan JSON (buat dibaca program lain / M4) ---
    report = {
        "dataset_path": str(DATASET_PATH.name),
        "total_entries": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "by_action": by_action,
        "results": results,
    }
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # --- simpan Markdown (buat dibaca manusia / dilampirkan ke submission) ---
    lines = [
        "# Validation Report - response_dataset.jsonl",
        "",
        f"**Total entries:** {total}  ",
        f"**PASSED:** {passed}  ",
        f"**FAILED:** {failed}  ",
        f"**Pass rate:** {report['pass_rate'] * 100:.1f}%",
        "",
        "## Per action",
        "",
        "| Action | Passed | Total |",
        "|---|---|---|",
    ]
    for action, stat in by_action.items():
        lines.append(f"| {action} | {stat['passed']} | {stat['total']} |")

    failed_results = [r for r in results if r["validation_status"] != "PASSED"]
    lines.append("")
    lines.append("## Detail entry yang FAILED")
    lines.append("")
    if not failed_results:
        lines.append("Tidak ada -- seluruh entry lolos validasi.")
    else:
        for r in failed_results:
            lines.append(f"### Entry {r['index']} ({r['selected_action']})")
            lines.append(f"- response_text: {r['response_text']}")
            lines.append(f"- failed_checks: {r['failed_checks']}")
            lines.append("")

    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"PASSED: {passed}/{total}")
    print(f"Laporan disimpan: {REPORT_JSON_PATH.name}, {REPORT_MD_PATH.name}")


if __name__ == "__main__":
    main()
