#!/usr/bin/env python
"""Transcript-guided cut (v0). The text decides, never the volume.

Reads the WhisperX transcript (scripts/transcribe_whisperx.py output), keeps the segments you
name, drops leading words of a segment when it starts with an aborted restart, closes pauses
longer than --max-pause by splitting the span, pads each span by the real voice (-pad-in / +pad-out)
and writes the result into projects/<slug>/edit-plan.json "cuts" (what `studio.py assemble` reads)
plus work/cut/cuts.json with the reasoning.

  python scripts/transcript_cut.py projects/harvey \
      --transcript work/transcripts/harvey-pesquisa.transcript.json \
      --source raw/harvey-pesquisa.MOV \
      --keep 0,1,2,4,7,8,9,10,11,12,13,14 --skip-words 8:1,11:2

Alignment smears: a word longer than --smear seconds is treated as mis-aligned. If it is the
last word of its segment the real end is start+0.6; otherwise the real start is end-0.4.
"""
import argparse
import json
from pathlib import Path


def real_bounds(words, smear):
    out = []
    for index, w in enumerate(words):
        start, end = w["start"], w["end"]
        if end - start > smear:
            if index == len(words) - 1:
                end = start + 0.6
            else:
                start = end - 0.4
        out.append({"text": w["word"].strip(), "start": start, "end": end})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--transcript", type=Path, required=True, help="relative to project")
    parser.add_argument("--source", type=Path, required=True, help="relative to project, inside raw/")
    parser.add_argument("--keep", required=True, help="segment indexes to keep, in order, e.g. 0,1,2,4")
    parser.add_argument("--skip-words", default="", help="segment:count pairs, e.g. 8:1,11:2")
    parser.add_argument("--max-pause", type=float, default=0.6)
    parser.add_argument("--pad-in", type=float, default=0.15)
    parser.add_argument("--pad-out", type=float, default=0.25)
    parser.add_argument("--smear", type=float, default=1.0)
    args = parser.parse_args()

    project = args.project.resolve()
    data = json.loads((project / args.transcript).read_text(encoding="utf-8"))
    segments = data["segments"]
    skips = {int(k): int(v) for k, v in (pair.split(":") for pair in args.skip_words.split(",") if pair)}
    keep = [int(i) for i in args.keep.split(",")]

    cuts, log = [], []
    for order, index in enumerate(keep):
        segment = segments[index]
        words = real_bounds(segment["words"], args.smear)
        skipped = skips.get(index, 0)
        if skipped:
            log.append({"segment": index, "dropped_words": [w["text"] for w in words[:skipped]], "reason": "aborted restart"})
            words = words[skipped:]
        # split the segment wherever the gap between words is longer than max_pause
        spans, current = [], [words[0]]
        for prev, word in zip(words, words[1:]):
            if word["start"] - prev["end"] > args.max_pause:
                spans.append(current)
                current = [word]
            else:
                current.append(word)
        spans.append(current)
        for part, span in enumerate(spans):
            cuts.append({
                "beat_id": f"s{index:02d}" + (f"-{part + 1}" if len(spans) > 1 else ""),
                "source": str(args.source).replace("\\", "/"),
                "source_in": round(max(0.0, span[0]["start"] - args.pad_in), 3),
                "source_out": round(span[-1]["end"] + args.pad_out, 3),
                "text": " ".join(w["text"] for w in span),
                "reason": "kept take" + (f", pause of {span[0]['start'] - spans[part - 1][-1]['end']:.1f}s closed" if part else ""),
            })

    dropped = [i for i in range(len(segments)) if i not in keep]
    for i in dropped:
        log.append({"segment": i, "text": segments[i]["text"].strip(), "reason": "earlier take or aborted line"})

    plan_path = project / "edit-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["cuts"] = cuts
    plan["status"] = "spoken-cut-proposed"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    cut_dir = project / "work" / "cut"
    cut_dir.mkdir(parents=True, exist_ok=True)
    total = sum(c["source_out"] - c["source_in"] for c in cuts)
    (cut_dir / "cuts.json").write_text(json.dumps({
        "transcript": str(args.transcript), "engine": data.get("engine"), "language": data.get("language"),
        "settings": {"max_pause": args.max_pause, "pad_in": args.pad_in, "pad_out": args.pad_out, "smear": args.smear},
        "cuts": cuts, "decisions": log, "duration": round(total, 2)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(cuts)} cuts, {total:.1f}s -> {plan_path}")
    for c in cuts:
        print(f"  {c['beat_id']:7} {c['source_in']:7.2f}-{c['source_out']:7.2f}  {c['text']}")


if __name__ == "__main__":
    main()
