"""
QLoRA fine-tuning untuk Grounded LLM LiveCoach AI - M3/SCR-3.

WAJIB DIJALANKAN DI GOOGLE COLAB (GPU T4 gratis) atau environment lain yang
punya GPU + akses internet ke huggingface.co. Sandbox pengembangan tim tidak
punya GPU/akses HF, jadi script ini TIDAK dites end-to-end di sini -- hanya
disusun mengikuti pola QLoRA standar (bitsandbytes 4-bit + peft LoRA + trl
SFTTrainer). Wajib di-smoke-test dulu di Colab sebelum dipakai untuk
training penuh.

Strategi (sesuai keputusan): dataset kecil (60 contoh) -> LoRA RINGAN
(rank kecil, epoch sedikit) supaya tidak overfit, karena grounding &
format JSON sudah "dijamin ganda" oleh system_prompt.py yang dipakai
persis sama saat training maupun inference production.

Langkah pakai di Colab:
  1. Upload product_facts_v2.json, response_dataset.jsonl, system_prompt.py
     ke working directory Colab.
  2. !pip install -r requirements_qlora.txt
  3. python qlora_train.py
  4. Adapter hasil training tersimpan di ./livecoach-qlora-adapter/
"""

import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer

from system_prompt import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Konfigurasi -- gampang di-swap ke model lain kalau kualitas 1.5B kurang
# ---------------------------------------------------------------------------

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"   # ganti ke "Qwen/Qwen2.5-3B-Instruct" kalau perlu kualitas lebih
DATASET_PATH = Path("response_dataset.jsonl")
OUTPUT_DIR = "livecoach-qlora-adapter"
MAX_SEQ_LENGTH = 1024

LORA_CONFIG = LoraConfig(
    r=8,                # rank kecil -- dataset cuma 60 contoh, hindari overfit
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # attention layers Qwen2
)

TRAINING_ARGS = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=4,             # epoch sedikit -- data kecil, rawan overfit/hafalan
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,  # efektif batch size 8
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=5,
    save_strategy="epoch",
    bf16=torch.cuda.is_available(),
    report_to="none",
)


# ---------------------------------------------------------------------------
# 1. Load dan format dataset jadi chat template
# ---------------------------------------------------------------------------

def load_dataset(path: Path) -> Dataset:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            user_payload = {
                "selected_action": entry["input"]["selected_action"],
                "audience_state": entry["input"]["audience_state"],
                "evidence_comments": entry["input"]["evidence_comments"],
                "product_facts": entry["input"]["product_facts"],
                "tone": entry["input"]["tone"],
                "max_words": entry["input"]["max_words"],
            }
            assistant_payload = entry["output"]

            rows.append(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                        {"role": "assistant", "content": json.dumps(assistant_payload, ensure_ascii=False)},
                    ]
                }
            )
    return Dataset.from_list(rows)


def formatting_func(example, tokenizer):
    return tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False
    )


# ---------------------------------------------------------------------------
# 2. Load base model 4-bit + siapkan LoRA
# ---------------------------------------------------------------------------

def build_model_and_tokenizer():
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LORA_CONFIG)
    model.print_trainable_parameters()

    return model, tokenizer


# ---------------------------------------------------------------------------
# 3. Main
# ---------------------------------------------------------------------------

def main():
    dataset = load_dataset(DATASET_PATH)
    print(f"Loaded {len(dataset)} training examples.")

    model, tokenizer = build_model_and_tokenizer()

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=TRAINING_ARGS,
        formatting_func=lambda ex: formatting_func(ex, tokenizer),
        max_seq_length=MAX_SEQ_LENGTH,
        tokenizer=tokenizer,
    )

    trainer.train()

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Adapter tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
