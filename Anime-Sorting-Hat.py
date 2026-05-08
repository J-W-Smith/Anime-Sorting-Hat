#!/usr/bin/env python3
"""
Anime Sorting Hat

A safer anime media organizer for Windows/Emby/Plex style libraries.

Highlights:
- Dry-run by default; use --apply to actually move files.
- Recursively scans existing folders by default.
- Groups files into: Anime Name/Season 01/
- Handles common anime release formats:
    [SubsPlease] Title - 01 (720p) [HASH].mkv
    [Group] Title - S03-01 [HASH].mkv
    Title.Something.Movie.2025.1080p.WEB-DL.mkv
    Title - OVA (720p).mkv
- Supports title aliases through JSON config.
- Moves matching sidecar files like .nfo, .srt, .ass with the video.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import anitopy  # type: ignore
except ImportError:
    anitopy = None

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".wmv"}
SIDECAR_EXTENSIONS = {".nfo", ".srt", ".ass", ".ssa", ".sub", ".idx", ".txt"}
DEFAULT_SKIP_FOLDERS = {"Movies", "OVAs", "Misc", "@eaDir", ".git", "__pycache__"}
INVALID_WINDOWS_CHARS = r'[<>:"/\\|?*]'

MOVIE_KEYWORDS = {"movie", "gekijouban", "the movie", "film", "web-dl", "webrip", "bluray", "blu-ray", "bdrip"}
SPECIAL_KEYWORDS = {"ova", "oad", "ona", "special", "pre-broadcast", "pre broadcast", "pilot"}


@dataclass
class SortDecision:
    source: Path
    destination_folder: Path
    destination_name: str
    anime_name: str | None
    season: int | None
    category: str
    reason: str


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        print(f"[WARN] Config file not found: {path}")
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def clean_windows_name(name: str) -> str:
    name = re.sub(INVALID_WINDOWS_CHARS, "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip(" .")


def strip_release_group(name: str) -> str:
    return re.sub(r"^\[[^\]]+\]\s*", "", name).strip()


def strip_noise_for_title(name: str) -> str:
    name = strip_release_group(name)
    name = re.sub(r"\[[^\]]+\]", " ", name)
    name = re.sub(r"\([^)]*\)", " ", name)
    name = re.sub(r"\b(480p|720p|1080p|2160p|4k|x264|x265|h264|h265|hevc|aac|flac|web-dl|webrip|bluray|blu-ray|bdrip)\b", " ", name, flags=re.I)
    name = re.sub(r"\s+", " ", name)
    return name.strip(" -_.")


def normalize_key(value: str) -> str:
    value = strip_release_group(value).lower()
    value = re.sub(r"[._]+", " ", value)
    value = re.sub(r"[-–—]+", " - ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def apply_aliases(title: str, aliases: dict[str, str]) -> str:
    title_key = normalize_key(title)
    for alias, canonical in sorted(aliases.items(), key=lambda x: len(x[0]), reverse=True):
        alias_key = normalize_key(alias)
        if alias_key and alias_key in title_key:
            return canonical
    return title


def canonicalize_dash_title(title: str, dash_whitelist: Iterable[str]) -> str:
    """Collapse configured titles like 'Hitori no Shita - Subtitle' to 'Hitori no Shita'."""
    title_key = normalize_key(title)
    for item in dash_whitelist:
        item_key = normalize_key(item)
        if item_key and title_key.startswith(item_key + " - "):
            return title.split(" - ", 1)[0].strip()
    return title


def extract_sxx_exx(filename: str) -> tuple[int | None, int | None, str | None]:
    stem = strip_release_group(Path(filename).stem)
    patterns = [
        r"^(?P<title>.+?)\s*[-–—]?\s*S(?P<season>\d{1,2})\s*[- ]\s*(?P<episode>\d{1,3})(?:v\d+)?\b",
        r"^(?P<title>.+?)\s*[-–—]?\s*S(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?:v\d+)?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, stem, flags=re.I)
        if match:
            return int(match.group("season")), int(match.group("episode")), match.group("title").strip(" -_")
    return None, None, None


def extract_standard_episode(filename: str) -> tuple[str | None, int | None]:
    stem = strip_release_group(Path(filename).stem)
    match = re.search(r"^(?P<title>.+?)\s*[-–—]\s*(?P<episode>\d{1,3})(?:v\d+)?(?:\s|\(|\[|$)", stem, flags=re.I)
    if match:
        return match.group("title").strip(" -_"), int(match.group("episode"))
    return None, None


def extract_season_from_title(title: str) -> tuple[str, int | None]:
    match = re.search(r"\b(?:S|Season)\s*(\d{1,2})\b", title, flags=re.I)
    if not match:
        return title, None
    season = int(match.group(1))
    title = re.sub(r"\b(?:S|Season)\s*\d{1,2}\b", "", title, flags=re.I)
    return title.strip(" -_"), season


def has_year(filename: str) -> bool:
    return re.search(r"\b(?:19|20)\d{2}\b", filename) is not None


def contains_any(value: str, keywords: Iterable[str]) -> bool:
    value = normalize_key(value)
    return any(keyword.lower() in value for keyword in keywords)


def parse_with_anitopy(filename: str) -> dict[str, Any]:
    if anitopy is None:
        return {}
    try:
        parsed = anitopy.parse(filename)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def build_clean_filename(path: Path, remove_release_group: bool) -> str:
    name = path.name
    if remove_release_group:
        name = strip_release_group(name)
    return clean_windows_name(name)


def decide_destination(source_file: Path, library_root: Path, aliases: dict[str, str], dash_whitelist: Iterable[str], remove_release_group: bool) -> SortDecision | None:
    if source_file.suffix.lower() not in VIDEO_EXTENSIONS:
        return None

    lower_name = source_file.name.lower()
    clean_filename = build_clean_filename(source_file, remove_release_group)

    season, episode, title = extract_sxx_exx(source_file.name)
    if title is None:
        title, episode = extract_standard_episode(source_file.name)

    parsed = parse_with_anitopy(source_file.name)
    if title is None and isinstance(parsed.get("anime_title"), str):
        title = parsed.get("anime_title")

    if season is None and parsed.get("anime_season") is not None:
        try:
            season = int(parsed.get("anime_season"))
        except (TypeError, ValueError):
            season = None

    if episode is None and parsed.get("episode_number") is not None:
        try:
            episode = int(float(str(parsed.get("episode_number"))))
        except (TypeError, ValueError):
            episode = None

    is_special = contains_any(lower_name, SPECIAL_KEYWORDS)
    is_movie = episode is None and (has_year(lower_name) or contains_any(lower_name, MOVIE_KEYWORDS))

    if is_movie and not is_special:
        return SortDecision(source_file, library_root / "Movies", clean_filename, None, None, "movie", "movie/no episode detected")

    if title is None:
        title = strip_noise_for_title(source_file.stem)
        title = re.sub(r"\b(ova|oad|ona|special|pre[- ]broadcast).*$", "", title, flags=re.I).strip(" -_")

    if not title:
        return SortDecision(source_file, library_root / "Misc", clean_filename, None, None, "misc", "could not identify title")

    title, title_season = extract_season_from_title(title)
    if season is None and title_season is not None:
        season = title_season

    title = apply_aliases(title, aliases)
    title = canonicalize_dash_title(title, dash_whitelist)
    title = clean_windows_name(title)

    if is_special or episode == 0:
        season = 0
        reason = "special/OVA/episode 00"
    else:
        season = season or 1
        reason = "series episode"

    return SortDecision(source_file, library_root / title / f"Season {season:02d}", clean_filename, title, season, "series", reason)


def matching_sidecars(video_file: Path) -> list[Path]:
    matches: list[Path] = []
    for ext in SIDECAR_EXTENSIONS:
        candidate = video_file.with_suffix(ext)
        if candidate.exists():
            matches.append(candidate)
    return matches


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def should_skip_path(path: Path, library_root: Path, skip_folders: set[str]) -> bool:
    try:
        relative = path.relative_to(library_root)
    except ValueError:
        return False
    return any(part in skip_folders for part in relative.parts)


def iter_video_files(library_root: Path, recursive: bool, skip_folders: set[str]) -> Iterable[Path]:
    if recursive:
        for root, dirs, files in os.walk(library_root):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if d not in skip_folders]
            if should_skip_path(root_path, library_root, skip_folders):
                continue
            for filename in files:
                path = root_path / filename
                if path.suffix.lower() in VIDEO_EXTENSIONS:
                    yield path
    else:
        for path in library_root.iterdir():
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
                yield path


def move_file(source: Path, destination: Path, dry_run: bool) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def clean_empty_dirs(library_root: Path, dry_run: bool, skip_folders: set[str]) -> int:
    removed = 0
    for root, dirs, files in os.walk(library_root, topdown=False):
        root_path = Path(root)
        if root_path == library_root or should_skip_path(root_path, library_root, skip_folders):
            continue
        if not dirs and not files:
            print(f"[CLEAN] Remove empty folder: {root_path}")
            removed += 1
            if not dry_run:
                try:
                    root_path.rmdir()
                except OSError:
                    pass
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely organize anime files into show/season folders.")
    parser.add_argument("source", nargs="?", default=os.getcwd(), help="Anime library folder to scan. Defaults to current directory.")
    parser.add_argument("--apply", action="store_true", help="Actually move files. Without this, the script only previews changes.")
    parser.add_argument("--no-recursive", action="store_true", help="Only scan the top-level source folder.")
    parser.add_argument("--config", type=Path, default=None, help="Optional JSON config file with aliases and settings.")
    parser.add_argument("--keep-release-group", action="store_true", help="Keep leading release group tags like [SubsPlease] in destination filenames.")
    parser.add_argument("--clean-empty", action="store_true", help="Remove empty folders after moving files.")
    args = parser.parse_args()

    library_root = Path(args.source).expanduser().resolve()
    if not library_root.exists() or not library_root.is_dir():
        print(f"[ERROR] Source folder does not exist or is not a directory: {library_root}")
        return 1

    config = load_config(args.config)
    aliases = config.get("aliases", {}) if isinstance(config.get("aliases", {}), dict) else {}
    dash_whitelist = config.get("dash_normalize_whitelist", []) if isinstance(config.get("dash_normalize_whitelist", []), list) else []

    skip_folders = set(DEFAULT_SKIP_FOLDERS)
    extra_skip = config.get("skip_folders", [])
    if isinstance(extra_skip, list):
        skip_folders.update(str(x) for x in extra_skip)

    dry_run = not args.apply

    print("Anime Sorting Hat")
    print("=================")
    print(f"Library:   {library_root}")
    print(f"Mode:      {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"Recursive: {not args.no_recursive}\n")

    decisions: list[SortDecision] = []
    for video_file in iter_video_files(library_root, recursive=not args.no_recursive, skip_folders=skip_folders):
        decision = decide_destination(video_file, library_root, aliases, dash_whitelist, remove_release_group=not args.keep_release_group)
        if decision is None:
            continue

        destination = decision.destination_folder / decision.destination_name
        if video_file.resolve() == destination.resolve():
            continue

        decisions.append(decision)
        print(f"[MOVE] {video_file}")
        print(f"       -> {destination}")
        print(f"       reason: {decision.reason}")

        sidecars = matching_sidecars(video_file)
        if sidecars:
            print(f"       sidecars: {', '.join(p.name for p in sidecars)}")

        if not dry_run:
            final_destination = unique_destination(destination)
            move_file(video_file, final_destination, dry_run=False)
            for sidecar in sidecars:
                sidecar_name = build_clean_filename(sidecar, remove_release_group=not args.keep_release_group)
                sidecar_destination = unique_destination(decision.destination_folder / sidecar_name)
                move_file(sidecar, sidecar_destination, dry_run=False)

    if args.clean_empty:
        clean_empty_dirs(library_root, dry_run=dry_run, skip_folders=skip_folders)

    print(f"\nDone. {'Previewed' if dry_run else 'Moved'} {len(decisions)} video file(s).")
    if dry_run:
        print("Run again with --apply to actually move files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
