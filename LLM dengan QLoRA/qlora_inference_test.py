"""
Sanity check adapter hasil QLoRA -- dijalankan di Colab SETELAH qlora_train.py
selesai. Tujuannya cek 2 hal sebelum diserahkan ke M4 untuk integrasi:
  1. Output selalu JSON valid sesuai skema.
  2. used_fact_ids yang disebut model benar-benar ada di product_facts yang diberikan
     (tanda model tidak mengarang / halusinasi fakta).

Pakai prompt yang SENGAJA TIDAK ADA di response_dataset.jsonl -- ini bukan
angka training, jadi hasil bagus di sini artinya modelnya generalisasi,
bukan hanya menghafal.
"""

import json

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from system_prompt import SYSTEM_PROMPT

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_DIR = "livecoach-qlora-adapter"

# Prompt uji -- kombinasi baru yang tidak persis ada di dataset training
# [19 Agt 2026] selected_action/audience_state di bawah disamakan ke enum resmi
# dokumen (Section 4.2/11) -- lihat DECISIONS_LOG.md di root folder Lomba.
EVAL_CASES = [
    {
        "selected_action": "SHOW_SIZE_GUIDE",
        "audience_state": "SIZE_FRICTION",
        "evidence_comments": ["bb 70 cocok size apa ya kak", "aku agak gendutan nih"],
        "product_facts": [
            {"fact_id": "FACT-TS01-SIZE-XL", "value": "Size XL (dewasa): lingkar dada 112-116 cm, panjang baju 75 cm, cocok untuk BB 72-85 kg, TB 168-178 cm."}
        ],
        "tone": "santai",
        "max_words": 30,
    },
    {
        "selected_action": "EXPLAIN_PRODUCT_DETAIL",
        "audience_state": "PRODUCT_INFO_GAP",
        "evidence_comments": ["ini bahannya panas ga buat cuaca jakarta"],
        "product_facts": [
            {"fact_id": "FACT-TS01-MATERIAL-002", "value": "Kain tidak nerawang, gramasi 180 gsm, rajutan single knit rapat sehingga tidak mudah melar."}
        ],
        "tone": "informatif",
        "max_words": 30,
    },
    {
        # sengaja fact yang dibutuhkan TIDAK diberikan -- harus needs_fallback=true
        "selected_action": "CONFIRM_STOCK",
        "audience_state": "STOCK_FRICTION",
        "evidence_comments": ["ada warna pink ga kak"],
        "product_facts": [],
        "tone": "informatif",
        "max_words": 30,
    },
]


def load_model():
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb_config, device_map="auto"
    )
    model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    model.eval()
    return model, tokenizer


def generate(model, tokenizer, case: dict) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(case, ensure_ascii=False)},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    output = model.generate(
        **inputs,
        max_new_tokens=256,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )
    text = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return text.strip()


def check_output(raw_text: str, given_fact_ids: set) -> dict:
    result = {"valid_json": False, "used_fact_ids_grounded": False, "raw": raw_text}
    try:
        parsed = json.loads(raw_text)
        result["valid_json"] = True
        used = set(parsed.get("used_fact_ids", []))
        result["used_fact_ids_grounded"] = used.issubset(given_fact_ids)
        result["parsed"] = parsed
    except json.JSONDecodeError:
        pass
    return result


def main():
    model, tokenizer = load_model()

    for i, case in enumerate(EVAL_CASES):
        print(f"\n=== Eval case {i+1}: {case['selected_action']} ===")
        raw = generate(model, tokenizer, case)
        given_ids = {f["fact_id"] for f in case["product_facts"]}
        result = check_output(raw, given_ids)

        print("Valid JSON:", result["valid_json"])
        print("used_fact_ids grounded (tidak mengarang):", result["used_fact_ids_grounded"])
        print("Output:", result.get("parsed", result["raw"]))


if __name__ == "__main__":
    main()
