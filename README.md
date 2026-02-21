# WinShiC

**Win+Shift+C** screenshot tool for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Capture any area of your screen and instantly pass it to Claude Code via clipboard path.

![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Win+Shift+C** — Region select capture
- **Win+Shift+V** — Active window capture
- **Multi-screenshot stacking** — Capture multiple screenshots, paste all paths at once
- **Multi-monitor support**
- **System tray icon** — Double-click or right-click menu
- **Auto cleanup** — Prompts to clean up when files exceed 250
- **Sleep recovery** — Auto-restarts hotkey listener after wake

## How it works

1. Press `Win+Shift+C`
2. Select a region on screen
3. Screenshot is saved & path is copied to clipboard
4. Paste the path into Claude Code — Claude can read the image

You can take multiple screenshots before pasting. All paths are stacked in the clipboard.

## Install

### Option 1: Run from source

```bash
pip install Pillow pynput pystray
python winshic.pyw
```

### Option 2: Use the exe

Download `winshic.exe` from [Releases](../../releases) and add it to your startup folder.

**Startup folder location:**
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

## Requirements

- Windows 10/11
- Python 3.8+ (if running from source)
- `Pillow`, `pynput`, `pystray`

## Screenshots saved to

```
~/Documents/Claude_Screenshot/
```

## License

MIT
