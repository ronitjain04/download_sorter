# Download Sorter

A Python script that automatically monitors your **Downloads** folder and moves files into organized subfolders based on keywords or file types. For example, invoices and receipts can go into `Finance/`, images into `Images/`, and schoolwork into `School/`.

## Features
- Watches your Downloads folder in real time.
- Moves files into subfolders based on:
  - Keywords in the filename (`invoice`, `resume`, etc.)
  - File type patterns (`*.png`, `*.pdf`, etc.)
  - (Optional) Keywords found inside file contents (for `.txt`, `.pdf`, `.docx`).
- Skips partial downloads (like `.crdownload`).
- Creates folders automatically if they don’t exist.
- Works on macOS, Windows, and Linux.

## Requirements
- Python 3.8 or later
- Install dependencies:
  ```bash
  pip install watchdog
