#!/usr/bin/env python3
"""
Interactively edit key=value pairs in every title.cfg found recursively under a root.

Formatting ENFORCED on save:
- No spaces around '=' (always "key=value")
- No trailing spaces at end of any line (including comments/blank lines)

Behavior:
- Displays the folder/file path.
- Shows each existing key and its current value.
- Prompts you to enter a new value (blank to keep, q to stop this file, qa to quit all).
- Overwrites existing values in-place, preserving file order, comments, blank lines, and newline style.
- Creates a .bak backup unless --no-backup is specified.
- Case-insensitive match on filename (title.cfg, TITLE.CFG, etc.).
- Encoding detection: utf-8-sig, utf-8, shift_jis, cp1252, latin-1 (writes back with the detected encoding).
- Newline style preserved (\r\n vs \n).

Usage:
    python edit_title_cfg_interactive.py .
    python edit_title_cfg_interactive.py "D:\\FinalwLE\\distribution-ready" --no-backup
"""

import argparse, sys
from pathlib import Path

CANDIDATE_ENCODINGS = ["utf-8-sig", "utf-8", "shift_jis", "cp1252", "latin-1"]

def detect_encoding(data: bytes) -> str:
    for enc in CANDIDATE_ENCODINGS:
        try:
            data.decode(enc)
            return enc
        except Exception:
            continue
    return "latin-1"

def detect_newline(text: str) -> str:
    # If Windows newlines present, keep \r\n; else default to \n
    return "\r\n" if "\r\n" in text and not text.endswith("\r") else "\n"

def load_text(path: Path):
    raw = path.read_bytes()
    enc = detect_encoding(raw)
    txt = raw.decode(enc, errors="strict")
    nl = detect_newline(txt)
    return txt, enc, nl

def save_text(path: Path, txt: str, enc: str, nl: str, do_backup: bool):
    # Normalize newlines to the chosen style
    normalized = txt.replace("\r\n", "\n").replace("\r", "\n")
    if nl == "\r\n":
        normalized = normalized.replace("\n", "\r\n")
    if do_backup:
        bak = Path(str(path) + ".bak")
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
    path.write_bytes(normalized.encode(enc))

def is_kv_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped or stripped[0] in "#;":
        return False
    return "=" in line

def split_kv(line: str):
    # Split at first '=', return raw parts and trimmed key/value
    idx = line.find("=")
    if idx == -1:
        # Not a kv line according to our use, but keep safe
        return line, "", "", "", ""
    left = line[:idx]
    right = line[idx+1:]
    key = left.strip()
    value = right.strip()
    return left, "=", right, key, value

def normalize_kv(key: str, value: str) -> str:
    # Enforce "key=value" with no spaces around '='
    return f"{key.strip()}={value.strip()}"

def process_file(p: Path, no_backup: bool) -> bool:
    try:
        txt, enc, nl = load_text(p)
    except Exception as e:
        print(f"  ERROR reading: {e}")
        return False

    # Split preserving lines; we'll rebuild after editing
    lines = txt.splitlines()
    changed = False

    print(f"Encoding: {enc}, Newline: {'CRLF' if nl=='\r\n' else 'LF'}")
    print("Editing existing keys. Blank = keep. 'q' = stop this file, 'qa' = quit all.")
    print("Formatting enforced: no spaces around '=', no trailing spaces.\n")

    new_lines = []
    quit_all = False

    # Count kv lines for progress display
    total = sum(1 for ln in lines if is_kv_line(ln))
    idx = 0

    for line in lines:
        # Trim trailing spaces on EVERY line (comments and blanks included)
        line = line.rstrip(" \t")

        if not is_kv_line(line):
            new_lines.append(line)
            continue

        idx += 1
        left, eq, right, key, value = split_kv(line)
        # Show current normalized view of this kv
        current_norm = normalize_kv(key, value)
        print(f"  [{idx}/{total}] {current_norm}")
        try:
            new_val = input("     New value (blank=keep, q=skip file, qa=quit all): ").rstrip("\n")
        except EOFError:
            new_val = ""

        if new_val.lower() == "qa":
            quit_all = True
            # Keep existing (but normalized) line
            new_lines.append(current_norm)
            continue
        if new_val.lower() == "q":
            # Keep this line normalized
            new_lines.append(current_norm)
            # Append remaining lines unchanged but enforce trailing-space removal
            rem = lines[len(new_lines):]
            for rem_line in rem:
                new_lines.append(rem_line.rstrip(" \t"))
            break

        if new_val == "":
            # Keep existing value but normalize formatting
            new_line = normalize_kv(key, value)
            if new_line != line:
                changed = True
            new_lines.append(new_line)
            continue

        # Use the provided new value, normalized
        new_line = normalize_kv(key, new_val)
        if new_line != line:
            changed = True
        new_lines.append(new_line)

    # If we didn't early-break, ensure remaining lines are accounted for
    if len(new_lines) < len(lines):
        # Done by break-copy above
        pass

    out_txt = "\n".join(new_lines)
    if changed:
        try:
            save_text(p, out_txt, enc, nl, do_backup=(not no_backup))
            print("  Saved.\n")
        except Exception as e:
            print(f"  ERROR writing: {e}")
            return False
    else:
        print("  No changes.\n")

    return quit_all

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--no-backup", action="store_true", help="do not create .bak files")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    print(f"Root: {root}")
    files = [p for p in root.rglob("*") if p.is_file() and p.name.lower() == "title.cfg"]
    print(f"Found {len(files)} title.cfg files.\n")

    if not files:
        print("Nothing to do.")
        return

    for n, p in enumerate(files, 1):
        print(f"[File {n}/{len(files)}] {p.relative_to(root)}")
        quit_all = process_file(p, args.no_backup)
        if quit_all:
            print("Quit all requested. Exiting.")
            break

    print("Done.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
