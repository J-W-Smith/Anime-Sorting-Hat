#!/usr/bin/env python3
"""Repair episode folders left behind by earlier Anime Sorting Hat runs.

This is for folders like:

    Hitori no Shita - S03-01
    Hitori no Shita - S03-02

If they contain files, this tool moves those files into:

    Hitori no Shita/Season 03/

It is dry-run by default. Use --apply to actually move files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

INVALID_WINDOWS_CHARS = r'[<>:"/\\|?*]'
DEFAULT_SKIP_FOLDERS = {"Movies", "OVAs", "Misc", "@eaDir", ".git", "__pycache__"}
EPISODE_FOLDER_PATTERN = re.compile(
    r"^(?P<title>.+?)\s*[-–—]\s*S(?P<season>\d{1,2})\s*[- ]\s*(?P<episode>\d{1,3})(?:v\d+)?\s*$",
    re.IGNORECASE,
)


def clean_windows_name(name: str) -> str:
    name = re.sub(INVALID_WINDOWS_CHARS, "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip(" .")


def normalize_key(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[._]+", " ", value)
    value = re.sub(r"[-–—]+", " - ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        print(f"[WARN] Config file not found: {path}")
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def apply_aliases(title: str, aliases: dict[str, str]) -> str:
    title_key = normalize_key(title)
    for alias, canonical in sorted(aliases.items(), key=lambda x: len(x[0]), reverse=True):
        alias_key = normalize_key(alias)
        if alias_key and alias_key in title_key:
            return canonical
    return title


def canonicalize_dash_title(title: str, dash_whitelist: list[str]) -> str:
    title_key = normalize_key(title)
    for item in dash_whitelist:
        item_key = normalize_key(item)
        if item_key and title_key.startswith(item_key + " - "):
            return title.split(" - ", 1)[0].strip()
    return title


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def is_skipped(path: Path, root: Path, skip_folders: set[str]) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return any(part in skip_folders for part in relative.parts)


def clean_empty_dirs(root: Path, dry_run: bool, skip_folders: set[str]) -> int:
    removed = 0
    for current_root, dirs, files in os.walk(root, topdown=False):
        folder = Path(current_root)
        if folder == root or is_skipped(folder, root, skip_folders):
            continue
        if not dirs and not files:
            print(f"[CLEAN] Remove empty folder: {folder}")
            removed += 1
            if not dry_run:
                try:
                    folder.rmdir()
                except OSError:
                    pass
    return removed


def repair_episode_folders(root: Path, aliases: dict[str, str], dash_whitelist: list[str], dry_run: bool) -> int:
    planned = 0

    # Walk bottom-up so nested episode folders are handled before parent cleanup.
    for current_root, dirs, files in os.walk(root, topdown=False):
        folder = Path(current_root)
        match = EPISODE_FOLDER_PATTERN.match(folder.name)
        if not match:
            continue

        if is_skipped(folder, root, DEFAULT_SKIP_FOLDERS):
            continue

        raw_title = match.group("title").strip()
        season = int(match.group("season"))
        canonical_title = apply_aliases(raw_title, aliases)
        canonical_title = canonicalize_dash_title(canonical_title, dash_whitelist)
        canonical_title = clean_windows_name(canonical_title)

        destination_folder = root / canonical_title / f"Season {season:02d}"

        # Move all files directly inside the episode folder.
        file_children = [p for p in folder.iterdir() if p.is_file()]
        if not file_children:
            continue

        for source_file in file_children:
            destination = unique_destination(destination_folder / source_file.name)
            print(f"[MOVE] {source_file}")
            print(f"       -> {destination}")
            planned += 1

            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_file), str(destination))

    return planned


def main() -> int:
    parser = argparse.ArgumentParser(description="Move files out of leftover episode folders like 'Show - S03-01'.")
    parser.add_argument("source", help="Anime library folder to repair.")
    parser.add_argument("--apply", action="store_true", help="Actually move files. Without this, only preview changes.")
    parser.add_argument("--config", type=Path, default=None, help="Optional Anime Sorting Hat JSON config file.")
    parser.add_argument("--clean-empty", action="store_true", help="Remove empty folders after repair.")
    args = parser.parse_args()

    root = Path(args.source).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] Source folder does not exist or is not a directory: {root}")
        return 1

    config = load_config(args.config)
    aliases = config.get("aliases", {}) if isinstance(config.get("aliases", {}), dict) else {}
    dash_whitelist = config.get("dash_normalize_whitelist", []) if isinstance(config.get("dash_normalize_whitelist", []), list) else []

    dry_run = not args.apply

    print("Anime Sorting Hat - Episode Folder Repair")
    print("=========================================")
    print(f"Library: {root}")
    print(f"Mode:    {'DRY RUN' if dry_run else 'APPLY'}\n")

    count = repair_episode_folders(root, aliases, dash_whitelist, dry_run=dry_run)

    if args.clean_empty:
        clean_empty_dirs(root, dry_run=dry_run, skip_folders=DEFAULT_SKIP_FOLDERS)

    print(f"\nDone. {'Previewed' if dry_run else 'Moved'} {count} file(s) from episode folders.")
    if dry_run:
        print("Run again with --apply to actually move files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
