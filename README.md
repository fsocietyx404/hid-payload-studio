# hid-payload-studio

![Version](https://img.shields.io/badge/version-1.0.0-0f172a)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Build](https://img.shields.io/badge/build-stable-success)
![Status](https://img.shields.io/badge/status-experimental-8b5cf6)

> Compile DuckyScript into raw USB HID payloads ⚡

A lightweight desktop GUI for generating `payload.dd` files compatible with Pico-based HID injection firmware.

Built with Python, PyQt6 and OpenCV.

---

## ⚙ Overview

hid-payload-studio converts DuckyScript into structured 8-byte USB HID reports.

The encoder:

- Parses DuckyScript instructions
- Encodes modifier + key combinations
- Converts delays into timing packets
- Generates raw binary payload output
- Provides syntax highlighting
- Supports animated MP4 backgrounds

This project focuses on low-level USB HID encoding inside a clean GUI environment.

---

## 🧠 Technical Details

Each keypress is translated into an 8-byte HID report:

- 1 byte modifier
- 1 reserved byte
- 6 keycode slots

Delays are implemented as repeated empty HID frames to simulate timing between events.

The resulting binary file can be deployed directly on compatible firmware-based USB devices.

---

## 🎬 Background System

The animated background runs via a local `background.mp4` file rendered with OpenCV.

Why is the background flexible?

This project was developed as a short-cycle experimental build.  
The video system was intentionally kept dynamic so users can replace it easily.

To customize:

1. Place a file named `background.mp4` next to the executable.
2. Restart the application.

Any MP4 file will work.

If you need to extract a video from YouTube as MP4:

https://wwv-y2mate.com

Rename it to `background.mp4` and place it in the application directory.

---

## 🚀 Installation

### Run from Source

Requirements:

- Python 3.10+
- pip

Install dependencies:

```
pip install PyQt6 opencv-python
```

Run:

```
python sysfract.py
```

---

### Build Standalone Executable

```
pip install pyinstaller
pyinstaller --onefile --windowed sysfract.py
```

Place `background.mp4` next to the generated executable.

---

## 💻 Usage

1. Write or load DuckyScript.
2. Click "Save as payload.dd".
3. Deploy the generated file to your HID device.

Example:

```
DELAY 2000
GUI r
DELAY 400
STRING notepad
ENTER
```

---

## ⚠ Disclaimer

This tool is intended for:

- Educational research
- Hardware experimentation
- Authorized security testing

The author is not responsible for misuse.

Always ensure you have explicit permission before interacting with any system.

---

## 🧩 Project Context

hid-payload-studio was built as a focused experimental project exploring:

- USB HID packet construction
- Binary payload encoding
- GUI design with PyQt6
- Custom syntax highlighting

It is intentionally minimal and extensible.

---

## 📜 License

MIT License
