#!/usr/bin/env python3
"""Download and verify the local English-to-Chinese translation model."""

from __future__ import annotations

from transformers import MarianMTModel, MarianTokenizer

from translate_abstracts import normalize_translation


MODEL_NAME = "Helsinki-NLP/opus-mt-en-zh"


def main() -> int:
    print(f"Downloading/loading {MODEL_NAME} ...")
    tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
    model = MarianMTModel.from_pretrained(MODEL_NAME)
    model.eval()
    sentence = (
        "Vision-Language-Action models are increasingly important for "
        "real-world robot manipulation."
    )
    inputs = tokenizer([sentence], return_tensors="pt", padding=True, truncation=True)
    output = model.generate(**inputs, max_new_tokens=128)
    translated = normalize_translation(tokenizer.decode(output[0], skip_special_tokens=True))
    print("Local translator is ready.")
    print(translated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
