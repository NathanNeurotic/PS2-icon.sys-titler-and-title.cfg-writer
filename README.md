# 📝 PS2 Icon & Title Config Tools

This repository contains two interactive tools for managing PlayStation 2 save metadata:

- **Interactive Icon Title Editor** — Safely edits `icon.sys` title lines (supports line 1 & 2, sets proper split offset)
- **Interactive Title.cfg Editor** — Edits simple `key=value` pairs in `title.cfg` files, enforcing clean formatting

---

## 📌 1. Icon.sys Interactive Namer (Two-Line Aware)

**Files**  
- `name_icons_interactive_v2.py` — Main Python script  
- `Name_IconSys_Interactively_v2.bat` — Double-click wrapper  

### What It Does
- Recursively scans for **icon.sys** files under the folder where you run it.
- Displays:
  - Relative folder path
  - Current **split offset** (byte `0x06`)
  - Current **Line 1** and **Line 2** (decoded preview)
- Prompts you to enter new text for Line 1 and Line 2:
  - **Blank** → keep current line  
  - **s** → skip this file  
  - **q** → quit all files
- Converts to **full-width Shift-JIS**, writes both lines starting at offset `0xC0`, pads to 68 bytes, and updates split offset to match Line 1 length.
- Makes a `.bak` backup before first write (unless `--no-backup` is specified).

### Usage

**Simplest (double-click):**
1. Place `.bat` + `.py` in the top folder of your save collection.
2. Double-click `Name_IconSys_Interactively_v2.bat`.
3. Follow prompts for each `icon.sys`.

**Advanced (command line):**
```bash
python name_icons_interactive_v2.py . --offset 0xC0 --block-len 68
```
Optional flags:

| Flag | Description |
|------|-------------|
| `--no-backup` | Do not create `.bak` files |
| `--offset` | Override title block start offset (default `0xC0`) |
| `--block-len` | Override title block length (default `68`) |

---

## 📌 2. Title.cfg Interactive Editor

**Files**  
- `edit_title_cfg_interactive.py` — Main Python script  
- `Edit_TitleCFG_Interactively.bat` — Double-click wrapper  

### What It Does
- Recursively finds **title.cfg** (case-insensitive) under the folder you run it in.
- Reads file with detected encoding (UTF-8, Shift-JIS, etc.).
- Displays each `key=value` line in order.
- Prompts you to enter new value:
  - **Blank** → keep current value (but normalized)
  - **q** → skip rest of this file
  - **qa** → quit all
- **Automatically enforces formatting**:
  - No spaces around `=`
  - No trailing spaces at end of line
- Preserves comments, blank lines, key order, and newline style.
- Makes a `.bak` backup before first write (unless `--no-backup` is specified).

### Usage

**Simplest (double-click):**
1. Place `.bat` + `.py` in the top folder of your save collection.
2. Double-click `Edit_TitleCFG_Interactively.bat`.
3. Follow prompts for each `title.cfg`.

**Advanced (command line):**
```bash
python edit_title_cfg_interactive.py . --no-backup
```

---

## 🔒 Safety & Notes
- **Backups**: Both tools write `.bak` files once per file before modifying, so you can restore if needed.
- **Skip & Quit**: Always available while prompting (`s`, `q`, `qa`).
- **Line Limits**: The icon tool enforces ≤ 16 characters per line (PS2 spec).
- **Encoding**: Handles Shift-JIS properly, sanitizes unsupported characters, preserves full-width formatting.
