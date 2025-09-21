#!/usr/bin/env python3
"""
Interactive icon.sys title editor (2-line aware, Shift-JIS full-width)

Features
- Recursively finds icon.sys (case-insensitive) under a root.
- For each file:
  * Shows relative path.
  * Reads current split offset @0x06 and current titles @0xC0..(0xC0+68).
  * Prompts for Line 1 and Line 2 (blank keeps existing), supports 's' to skip file, 'q' to quit all.
  * Converts ASCII to full-width, sanitizes to Shift-JIS compatible.
  * Enforces "Line 1 <= 16 chars" (after ASCII input but before FW/SJIS conversion we validate length against 16 chars).
  * Writes title bytes at 0xC0, pads/truncates to 68 bytes.
  * Writes split offset byte at 0x06 = len(Title1 SJIS bytes).
  * Creates .bak once per file unless --no-backup is set.
- Safe binary handling; no encoding assumptions for file itself.

Defaults
- title block offset: 0xC0
- title block length: 68
- split offset byte location: 0x06 (single byte)

Usage
    python name_icons_interactive_v2.py .
    python name_icons_interactive_v2.py "D:\\FinalwLE\\distribution-ready"
Options
    --no-backup      Do not create .bak backups

Controls during prompt
    Enter text for Line 1 / Line 2 -> write
    Blank -> keep current line (no change)
    's'   -> skip this file
    'q'   -> quit all
"""

from pathlib import Path
import sys
import unicodedata
import argparse

TITLE_OFFSET_DEFAULT = 0xC0
TITLE_BLOCK_LEN_DEFAULT = 68
SPLIT_OFFSET_POS = 0x06  # single byte

# Mapping for unsupported/problematic characters -> safer full-width equivalents
REPLACEMENTS = {
    "'": "’",
    "-": "ー",
    # Subscript digits to full-width
    "₀": "０", "₁": "１", "₂": "２", "₃": "３", "₄": "４",
    "₅": "５", "₆": "６", "₇": "７", "₈": "８", "₉": "９",
}

def ascii_to_fullwidth(text: str) -> str:
    """Convert ASCII text to full-width (Zenkaku) style similar to PS2 expectations.
       - Replace mapped characters
       - Decompose accents (é -> e) then fullwidth-map ASCII range and space
    """
    result = []
    for c in text:
        if c in REPLACEMENTS:
            c = REPLACEMENTS[c]
        # Decompose accents (best-effort)
        decomp = unicodedata.normalize('NFD', c)
        c = decomp[0]
        code = ord(c)
        if 0x21 <= code <= 0x7E:
            # Basic ASCII -> full-width by adding 0xFEE0
            result.append(chr(code + 0xFEE0))
        elif c == ' ':
            result.append('\u3000')  # ideographic space
        else:
            result.append(c)
    return ''.join(result)

def can_encode_shift_jis(char: str) -> bool:
    try:
        char.encode('shift_jis')
        return True
    except UnicodeEncodeError:
        return False

def sanitize_for_shift_jis(text: str) -> str:
    return ''.join(c for c in text if can_encode_shift_jis(c))

def encode_line(text_ascii: str) -> bytes:
    """Convert an ASCII line to full-width, sanitize, encode to Shift-JIS bytes."""
    fw = ascii_to_fullwidth(text_ascii)
    fw_sane = sanitize_for_shift_jis(fw)
    return fw_sane.encode('shift_jis')

def decode_fw_sjis_to_ascii(b: bytes) -> str:
    """Decode bytes as Shift-JIS and try to map full-width ASCII back to ASCII for preview."""
    try:
        s = b.decode('shift_jis', errors='ignore')
    except Exception:
        s = ''
    # Map common full-width ranges to ASCII for display
    out = []
    for ch in s:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:  # full-width ASCII
            out.append(chr(code - 0xFEE0))
        elif ch == '\u3000':  # ideographic space
            out.append(' ')
        else:
            out.append(ch)
    return ''.join(out)

def read_current_titles(data: bytes, title_offset: int, block_len: int):
    block = data[title_offset:title_offset+block_len]
    # Read split offset (line1 sjis length) from @0x06; clamp to block_len
    split = data[SPLIT_OFFSET_POS] if len(data) > SPLIT_OFFSET_POS else 0
    if split > block_len:
        split = min(split, block_len)
    line1_bytes = block[:split]
    # Remaining non-zero until terminator for nice preview
    line2_bytes = block[split:]
    # Trim at first 0x00
    if 0x00 in line1_bytes:
        line1_bytes = line1_bytes.split(b'\x00', 1)[0]
    if 0x00 in line2_bytes:
        line2_bytes = line2_bytes.split(b'\x00', 1)[0]
    return decode_fw_sjis_to_ascii(line1_bytes), decode_fw_sjis_to_ascii(line2_bytes)

def write_titles(p: Path, line1_txt: str, line2_txt: str, title_offset: int, block_len: int, do_backup: bool):
    data = bytearray(p.read_bytes())
    # Encode both lines
    l1 = encode_line(line1_txt)
    l2 = encode_line(line2_txt)
    # Enforce line1 <= 16 characters as per friend script; also ensure SJIS len fits.
    if len(line1_txt) > 16:
        raise ValueError(f"Line 1 ASCII length {len(line1_txt)} exceeds 16 characters.")
    if len(line2_txt) > 16:
        raise ValueError(f"Line 2 ASCII length {len(line2_txt)} exceeds 16 characters.")
    split_offset = len(l1)
    if split_offset > block_len:
        raise ValueError("Line 1 is too long after encoding (exceeds title block length).")
    combined = l1 + l2
    title_block = combined[:block_len].ljust(block_len, b'\x00')

    # Ensure file can hold offsets
    end_needed = title_offset + block_len
    if len(data) < end_needed:
        data.extend(b'\x00' * (end_needed - len(data)))

    # Write split offset
    if len(data) <= SPLIT_OFFSET_POS:
        data.extend(b'\x00' * (SPLIT_OFFSET_POS + 1 - len(data)))
    data[SPLIT_OFFSET_POS] = split_offset & 0xFF

    # Write block
    data[title_offset:title_offset+block_len] = title_block

    if do_backup:
        bak = p.with_suffix(p.suffix + ".bak")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
    p.write_bytes(data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--no-backup", action="store_true", help="do not create .bak files")
    ap.add_argument("--offset", type=lambda x: int(x, 0), default=TITLE_OFFSET_DEFAULT, help="title block start (default 0xC0)")
    ap.add_argument("--block-len", type=int, default=TITLE_BLOCK_LEN_DEFAULT, help="title block length (default 68)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    print(f"Root: {root}")
    icons = [p for p in root.rglob("*") if p.is_file() and p.name.lower() == "icon.sys"]
    print(f"Found {len(icons)} icon.sys files.\n")

    if not icons:
        print("Nothing to do.")
        return

    for i, p in enumerate(icons, 1):
        print(f"[{i}/{len(icons)}] {p.relative_to(root)}")
        try:
            data = p.read_bytes()
        except Exception as e:
            print(f"  ERROR reading: {e}\n")
            continue

        # Current preview
        cur1, cur2 = read_current_titles(data, args.offset, args.block_len)
        print(f"  Current split @0x06: {data[SPLIT_OFFSET_POS] if len(data) > SPLIT_OFFSET_POS else 0}")
        print(f"  Current Line1: '{cur1}'")
        print(f"  Current Line2: '{cur2}'")

        # Prompts
        l1 = input("  New Line 1 (blank=keep, 's'=skip file, 'q'=quit all): ").rstrip("\n")
        if l1.lower() == 'q':
            print("Quit requested.")
            break
        if l1.lower() == 's':
            print("  Skipped.\n")
            continue
        l2 = input("  New Line 2 (blank=keep): ").rstrip("\n")

        if l1 == "":
            l1 = cur1
        if l2 == "":
            l2 = cur2

        # Enforce <=16 chars each (ASCII length check as per provided reference)
        if len(l1) > 16:
            print(f"  ERROR: Line 1 exceeds 16 characters (got {len(l1)}). Skipping.\n")
            continue
        if len(l2) > 16:
            print(f"  ERROR: Line 2 exceeds 16 characters (got {len(l2)}). Skipping.\n")
            continue

        try:
            write_titles(p, l1, l2, args.offset, args.block_len, do_backup=(not args.no_backup))
        except Exception as e:
            print(f"  ERROR writing: {e}\n")
            continue

        print("  Written.\n")

    print("Done.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
