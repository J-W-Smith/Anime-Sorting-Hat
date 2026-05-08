# Anime Sorting Hat

Anime Sorting Hat is a safer Python organizer for anime libraries. It scans anime video files and organizes them into show/season folders, with support for messy real-world release names.

It was built for filenames like:

```text
[SubsPlease] Kekkon Yubiwa Monogatari - 01v2 (720p) [50A1AF4D].mkv
[GuodongSubs] Hitori no Shita - S03-01 [40921809].mkv
[SubsPlease] Dorohedoro - OVA (720p) [75F66B45].mkv
Demon.Slayer.Kimetsu.No.Yaiba.Infinity.Castle.2025.1080p.WEB-DL.mkv
```

## What it does

- Organizes series into show and season folders:

```text
Anime Name/
  Season 01/
  Season 02/
  Season 00/
```

- Uses `Season 00` for OVAs, specials, pre-broadcast specials, and episode `00`.
- Sends detected one-off movies to `Movies/`.
- Sends unclassified files to `Misc/`.
- Supports recursive cleanup of an already-sorted library.
- Moves matching sidecar files with videos, such as `.nfo`, `.srt`, `.ass`, and `.ssa`.
- Supports custom aliases so related titles can be merged under one canonical name.

## Safety first

The script is **dry-run by default**. It previews what it would move without changing files.

```powershell
python Anime-Sorting-Hat.py "E:\~Anime"
```

To actually move files:

```powershell
python Anime-Sorting-Hat.py "E:\~Anime" --apply
```

To remove empty folders afterward:

```powershell
python Anime-Sorting-Hat.py "E:\~Anime" --apply --clean-empty
```

To only scan the top-level folder:

```powershell
python Anime-Sorting-Hat.py "E:\~Anime" --no-recursive
```

## Install

`anitopy` is optional, but it improves anime filename parsing.

```powershell
pip install -r requirements.txt
```

or:

```powershell
pip install anitopy
```

## Configuration

Copy the example config:

```powershell
copy anime_sorting_hat_config.example.json anime_sorting_hat_config.json
```

Then run with:

```powershell
python Anime-Sorting-Hat.py "E:\~Anime" --config anime_sorting_hat_config.json
```

Example alias use:

```json
{
  "aliases": {
    "hitori no shita": "Hitori no Shita",
    "hitori no shita - the outcast": "Hitori no Shita",
    "the outcast": "Hitori no Shita",
    "rust iron returns": "Hitori no Shita"
  },
  "dash_normalize_whitelist": [
    "Hitori no Shita"
  ],
  "skip_folders": [
    "Movies",
    "OVAs",
    "Misc"
  ]
}
```

This helps collapse title variants like:

```text
Hitori no Shita - The Outcast
Hitori no Shita - Rust Iron Returns
Hitori no Shita S6
```

into:

```text
Hitori no Shita/
```

## Filename cleanup

By default, leading release group tags are removed from destination filenames:

```text
[SubsPlease] Show - 01.mkv
```

becomes:

```text
Show - 01.mkv
```

To keep release group tags:

```powershell
python Anime-Sorting-Hat.py "E:\~Anime" --apply --keep-release-group
```

## Helper: generate alias suggestions

Use the alias helper to scan a library and suggest likely title aliases:

```powershell
python tools/generate_alias_suggestions.py "E:\~Anime"
```

It writes `alias_suggestions.txt` by default. Review the suggestions manually before adding them to your config.

## Notes

Anime filenames are messy. No parser is perfect, especially when official titles change across seasons. For best results, use the JSON config aliases for known problem series.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
