#!/usr/bin/env python3
"""Generate review-only alias suggestions for Anime Sorting Hat.

This script does not move or rename anything. It scans video filenames, strips
common release noise, and groups similar-looking titles so you can decide which
aliases belong in anime_sorting_hat_config.json.
"""

from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from pathlib import Path

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".wmv"}
SKIP_FOLDERS = {"Movies", "OVAs", "Misc", ".git", "__pycache__", "@eaDir"}

NOISE_WORDS = {
    "ova",
    "oad",
    "ona",
    "special",
    "pre broadcast",
    "pre-broadcast",
    "batch",
    "uncensored",
    "web dl",
    "web-dl",
    "webrip",
    "bluray",
    "blu ray",
    "blu-ray",
    "bdrip",
    "x264",
    "x265",
    "h264",
    "h265",
    "hevc",
    "aac",
    "flac",
    "720p",
    "1080p",
    "2160p",
    "4k",
}


def strip_release_group(name: str) -> str:
    return re.sub(r"^\[[^\]]+\]\s*", "", name).strip()


def normalize_title(name: str) -> str:
    name = strip_release_group(name)
    name = re.sub(r"\[[^\]]+\]", " ", name)
    name = re.sub(r"\([^)]*\)", " ", name)
    name = re.sub(r"\bS\d{1,2}[- ]?E?\d{1,3}\b", " ", name, flags=re.I)
    name = re.sub(r"\b\d{1,3}v?\d?\b", " ", name, flags=re.I)
    name = re.sub(r"[._]+", " ", name)
    name = re.sub(r"[-–—]+", " - ", name)
    name = re.sub(r"\s+", " ", name).strip().lower()

    for word in sorted(NOISE_WORDS, key=len, reverse=True):
        name = name.replace(word, " ")

    name = re.sub(r"\s+", " ", name)
    return name.strip(" -_")


def franchise_key(title: str, words: int = 3) -> str:
    normalized = normalize_title(title)
    parts = normalized.split()
    if len(parts) <= words:
        return normalized
    return " ".join(parts[:words])


def iter_video_files(root: Path):
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS]
        for file in files:
            path = Path(current_root) / file
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate alias suggestions for Anime Sorting Hat.")
    parser.add_argument("source", nargs="?", default=os.getcwd(), help="Anime library folder to scan. Defaults to current directory.")
    parser.add_argument("--output", default="alias_suggestions.txt", help="Output text file. Defaults to alias_suggestions.txt")
    parser.add_argument("--words", type=int, default=3, help="Number of leading words to use for franchise grouping. Defaults to 3.")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        print(f"[ERROR] Source folder does not exist or is not a directory: {source}")
        return 1

    groups: dict[str, list[Path]] = defaultdict(list)

    for path in iter_video_files(source):
        key = franchise_key(path.stem, words=args.words)
        if key:
            groups[key].append(path)

    output = Path(args.output)
    with output.open("w", encoding="utf-8") as f:
        f.write("Anime Sorting Hat Alias Suggestions\n")
        f.write("===================================\n\n")
        f.write("Review these manually. Do not blindly copy every suggestion.\n\n")

        for key, files in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
            if len(files) < 2:
                continue

            clean_variants = sorted({normalize_title(p.stem) for p in files})
            f.write("========================\n")
            f.write(f"CANONICAL CANDIDATE: {key.title()}\n")
            f.write(f"FILES: {len(files)}\n\n")

            f.write("VARIANTS:\n")
            for variant in clean_variants:
                f.write(f"  - {variant}\n")

            f.write("\nSAMPLE FILES:\n")
            for sample in files[:15]:
                f.write(f"  - {sample.name}\n")
            if len(files) > 15:
                f.write(f"  ... and {len(files) - 15} more\n")

            f.write("\nCONFIG STARTER:\n")
            f.write('  "aliases": {\n')
            for variant in clean_variants:
                if variant != key:
                    f.write(f'    "{variant}": "{key.title()}",\n')
            f.write('  }\n\n')

    print(f"Done. Review generated file: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
