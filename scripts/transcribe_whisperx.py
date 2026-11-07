#!/usr/bin/env python
"""Word-timed transcript with WhisperX on the local GPU (Windows / NVIDIA).

Drop-in replacement for `scripts/studio.py transcribe` (which needs MLX Whisper on Apple
Silicon). Writes the same three files so the rest of the studio reads them unchanged:
  <output>.transcript.json  full WhisperX result (segments with word timings)
  <output>.txt               plain text
  <output>.words.json        [{"text","start","end","probability"}]

Run it with the WhisperX venv's Python, not the system Python:
  ~/.cache/reels-editing-engine/whisperx-venv/Scripts/python.exe scripts/transcribe_whisperx.py \
      projects/<slug>/raw/<file> --output projects/<slug>/work/transcripts/<stem>.transcript.json
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--language", default="pt")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    try:
        import torch
        import whisperx
    except ImportError as error:
        sys.exit(f"WhisperX venv required (run with its python.exe): {error}")

    source = args.source.resolve(strict=True)
    output = (args.output or source.with_name(source.stem + ".transcript.json")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    for path in [output, output.with_suffix(".txt"), output.with_suffix(".words.json")]:
        if path.exists():
            sys.exit(f"Refusing to overwrite {path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    print(f"device={device} model={args.model} language={args.language}", flush=True)

    audio = whisperx.load_audio(str(source))
    model = whisperx.load_model(args.model, device, compute_type=compute, language=args.language)
    result = model.transcribe(audio, batch_size=args.batch_size, language=args.language)
    detected = result.get("language", args.language)

    align_model, metadata = whisperx.load_align_model(language_code=detected, device=device)
    aligned = whisperx.align(result["segments"], align_model, metadata, audio, device,
                             return_char_alignments=False)
    segments = aligned["segments"]

    # Words without timings (digits, symbols) inherit the midpoint of their neighbours so the
    # cut step never sees a gap; probability stays None to flag them.
    words = []
    for segment in segments:
        for word in segment.get("words", []):
            words.append({"text": word["word"].strip(), "start": word.get("start"),
                          "end": word.get("end"), "probability": word.get("score")})
    for index, word in enumerate(words):
        if word["start"] is None or word["end"] is None:
            prev_end = next((w["end"] for w in reversed(words[:index]) if w["end"] is not None), 0.0)
            next_start = next((w["start"] for w in words[index + 1:] if w["start"] is not None), prev_end)
            word["start"], word["end"] = prev_end, max(prev_end, next_start)

    text = " ".join(s["text"].strip() for s in segments).strip()
    payload = {"engine": "whisperx", "model": args.model, "device": device, "language": detected,
               "aligned": True, "source": str(source), "text": text, "segments": segments}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output.with_suffix(".txt").write_text(text + "\n", encoding="utf-8")
    output.with_suffix(".words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(segments)} segments, {len(words)} words, {words[-1]['end']:.1f}s -> {output}")


if __name__ == "__main__":
    main()
