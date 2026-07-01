"""Local CPU validation of the FULL GRPO loop — no big model download, no GPU.

Uses the cached Qwen2.5 tokenizer + a TINY RANDOM Qwen2 model (built from config) so
the reward func, GRPOConfig divisibility, generation, optimizer.step, and the oracle
audit callback all execute the SAME code paths as scripts/train_grpo.py on the pod —
catching integration bugs locally before renting a GPU. The model outputs garbage (we
test the LOOP, not quality). Run:  python scripts/validate_grpo_local.py
"""
from __future__ import annotations
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch  # noqa: E402
from transformers import AutoTokenizer, Qwen2Config, Qwen2ForCausalLM  # noqa: E402
from trl import GRPOConfig, GRPOTrainer  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_grpo import build_dataset, make_reward, oracle_callback  # noqa: E402
import glob  # noqa: E402


def main() -> int:
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")
    cfg = Qwen2Config(vocab_size=len(tok), hidden_size=64, intermediate_size=128,
                      num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                      max_position_embeddings=1024, tie_word_embeddings=True)
    model = Qwen2ForCausalLM(cfg)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    glob_pat = "tasks/veval_prob00[1-3]*"
    ds = build_dataset(glob_pat)
    audit_dirs = sorted(glob.glob(glob_pat))[:2]
    out = "runs/grpo_val"

    gcfg = GRPOConfig(output_dir=out, max_steps=2, per_device_train_batch_size=2,
                      num_generations=2, learning_rate=1e-4, logging_steps=1,
                      use_vllm=False, bf16=False, fp16=False, max_completion_length=32,
                      max_prompt_length=256, report_to=[])
    trainer = GRPOTrainer(
        model=model, reward_funcs=[make_reward(out)], args=gcfg, train_dataset=ds,
        processing_class=tok,
        callbacks=[oracle_callback(audit_dirs, out, tokenizer=tok, audit_every=1,
                                   max_new_tokens=32)],
    )
    print(f"[val] built: dataset={len(ds)} audit={len(audit_dirs)} — running 2 GRPO steps on CPU")
    trainer.train()
    print("[val] OK — full GRPO loop (generate + reward + optimizer.step + oracle audit) ran clean")
    cpath = os.path.join(out, "rhg_curve.jsonl")
    if os.path.exists(cpath):
        print("[val] RHG curve written:")
        print(open(cpath).read().strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
