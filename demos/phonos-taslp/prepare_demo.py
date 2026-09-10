#!/usr/bin/env python3
"""Build the PHONOS paper demo from the manually reviewed study pool."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import soundfile as sf


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = Path(
    "/data/waris/code/anonymousis23.github.io/UserStudy/PHONOS-TASLP26/accent_new"
)
SOURCE_MANIFEST = SOURCE_ROOT / "selection_manifest.csv"
SAMPLES_PER_DIRECTION = 5

DIRECTIONS = [
    ("ame2bri", "General American English", "British English", "GAE", "BRE"),
    ("ame2ind", "General American English", "Indian English", "GAE", "INE"),
    ("ame2spn", "General American English", "Spanish-accented English", "GAE", "SPE"),
    ("bri2ame", "British English", "General American English", "BRE", "GAE"),
    ("ind2ame", "Indian English", "General American English", "INE", "GAE"),
    ("spn2ame", "Spanish-accented English", "General American English", "SPE", "GAE"),
]


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wav_duration(path: Path) -> float:
    return float(sf.info(path).duration)


def copy_as_pcm16(source: Path, destination: Path) -> None:
    audio, sample_rate = sf.read(source, always_2d=True)
    sf.write(destination, audio, sample_rate, subtype="PCM_16")


def normalize_transcript(value: str) -> str:
    text = " ".join(value.strip().lower().split())
    if text and text[-1] not in ".?!":
        text += "."
    return text


def main() -> None:
    if not SOURCE_MANIFEST.exists():
        raise FileNotFoundError(f"Source manifest not found: {SOURCE_MANIFEST}")

    with SOURCE_MANIFEST.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))

    output = {
        "selection": {
            "source": str(SOURCE_MANIFEST),
            "policy": (
                "Five highest-NISQA PHONOS outputs per direction from the manually "
                "reviewed accent-study pool."
            ),
            "samples_per_direction": SAMPLES_PER_DIRECTION,
        },
        "directions": [],
    }
    audit_rows = []

    for direction, source_name, target_name, source_code, target_code in DIRECTIONS:
        candidates = [row for row in source_rows if row["direction"] == direction]
        candidates.sort(key=lambda row: as_float(row["phonos_nisqa_mos"]), reverse=True)
        if len(candidates) < SAMPLES_PER_DIRECTION:
            raise RuntimeError(
                f"{direction} has only {len(candidates)} candidates; "
                f"{SAMPLES_PER_DIRECTION} are required"
            )

        direction_dir = HERE / "audio" / direction
        direction_dir.mkdir(parents=True, exist_ok=True)
        samples = []

        for demo_index, row in enumerate(candidates[:SAMPLES_PER_DIRECTION], start=1):
            original_source = SOURCE_ROOT / row["original_audio"]
            converted_source = SOURCE_ROOT / row["phonos_audio"]
            if not original_source.exists() or not converted_source.exists():
                raise FileNotFoundError(
                    f"Missing pair for {direction}/{row['sample_group_id']}: "
                    f"{original_source}, {converted_source}"
                )

            original_name = f"sample_{demo_index:02d}_original.wav"
            converted_name = f"sample_{demo_index:02d}_phonos.wav"
            original_dest = direction_dir / original_name
            converted_dest = direction_dir / converted_name
            copy_as_pcm16(original_source, original_dest)
            copy_as_pcm16(converted_source, converted_dest)

            original_duration = wav_duration(original_dest)
            converted_duration = wav_duration(converted_dest)
            sample = {
                "id": f"{direction}_{demo_index:02d}",
                "label": f"Sample {demo_index:02d}",
                "transcript": normalize_transcript(row["transcript"]),
                "original_audio": f"audio/{direction}/{original_name}",
                "converted_audio": f"audio/{direction}/{converted_name}",
                "original_duration_sec": round(original_duration, 3),
                "converted_duration_sec": round(converted_duration, 3),
            }
            samples.append(sample)

            audit_rows.append(
                {
                    "direction": direction,
                    "demo_sample": demo_index,
                    "source_accent": source_name,
                    "target_accent": target_name,
                    "sample_group_id": row["sample_group_id"],
                    "source_id": row["source_id"],
                    "source_speaker_id": row["source_speaker_id"],
                    "utterance_id": row["utterance_id"],
                    "transcript": row["transcript"],
                    "phonos_item_id": row["phonos_item_id"],
                    "phonos_checkpoint": row["phonos_checkpoint"],
                    "phonos_target_ref_id": row["phonos_target_ref_id"],
                    "phonos_nisqa_mos": row["phonos_nisqa_mos"],
                    "phonos_accent_prediction": row["phonos_accent_prediction"],
                    "phonos_target_probability_pct": row[
                        "phonos_target_probability_pct"
                    ],
                    "demo_original_audio": sample["original_audio"],
                    "demo_converted_audio": sample["converted_audio"],
                    "original_duration_sec": f"{original_duration:.3f}",
                    "converted_duration_sec": f"{converted_duration:.3f}",
                    "original_sha256": sha256(original_dest),
                    "converted_sha256": sha256(converted_dest),
                }
            )

        output["directions"].append(
            {
                "id": direction,
                "source": source_name,
                "target": target_name,
                "source_code": source_code,
                "target_code": target_code,
                "label": f"{source_name} to {target_name}",
                "short_label": f"{source_code} to {target_code}",
                "samples": samples,
            }
        )

    with (HERE / "samples.json").open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=True)
        handle.write("\n")

    with (HERE / "selection_manifest.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    print(
        f"Prepared {len(audit_rows)} demo pairs across "
        f"{len(DIRECTIONS)} directions in {HERE}"
    )


if __name__ == "__main__":
    main()
