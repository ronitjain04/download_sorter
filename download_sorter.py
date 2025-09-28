from pathlib import Path
import time
import shutil
import fnmatch
import threading

from file_extensions import PLAIN_TEXT_EXTS, CODE_EXTS, CONTENT_SCAN_EXTS

def extract_text(path: Path) -> str:
    """
    Returns text content for text, code, and select Office files when possible.
    Tries optional PDF/DOCX readers if installed.
    """
    try:
        suffix = path.suffix.lower()

        if suffix in PLAIN_TEXT_EXTS or suffix in CODE_EXTS:
            return path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".pdf":
            try:
                from PyPDF2 import PdfReader
                text = []
                with path.open("rb") as f:
                    reader = PdfReader(f)
                    for page in reader.pages:
                        text.append(page.extract_text() or "")
                return "\n".join(text)
            except Exception:
                return ""

        if suffix in {".docx", ".docm", ".dotx", ".dotm"}:
            try:
                import docx
                doc = docx.Document(str(path))
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                return ""
            
    except Exception:
        return ""
    return ""


def is_temporary_download(p: Path) -> bool:
    tmp_suffixes = {".crdownload", ".part", ".tmp", ".download"}
    return p.suffix.lower() in tmp_suffixes or p.name.startswith("~$")


# === Customize this mapping ===
# Keys can be keywords or simple glob patterns. Values are destination folder names.
ROUTES = {
    # keyword or glob      -> subfolder under DEST_ROOT
    "invoice": "Finance",
    "receipt": "Finance",
    "tax": "Finance",
    "resume": "Resumes",
    "cover letter": "Resumes",
    "*.png": "Images",
    "*.jpg": "Images",
    "*.jpeg": "Images",
    "*.gif": "Images",
    "report": "Reports",
    "homework": "School",
    "assignment": "School",
}

# Where to watch and where to file things
DOWNLOADS = Path.home() / "Downloads"          # change if needed
DEST_ROOT = Path.home() / "SortedDownloads"    # change if needed

SETTLE_SECONDS = 2.0


def match_route(filename: str, content: str) -> str | None:
    """
    Return the destination subfolder name if any route matches
    based on filename or content. Filename checks support glob patterns.
    Content checks are substring contains.
    """
    lower_filename = filename.lower()
    lower_content = content.lower() if content else ""

    # First try glob matches on filename
    for pattern, folder in ROUTES.items():
        if any(ch in pattern for ch in "*?[]"):  # treat as glob
            if fnmatch.fnmatch(lower_filename, pattern.lower()):
                return folder

    # Then keyword matches on filename
    for key, folder in ROUTES.items():
        if not any(ch in key for ch in "*?[]"):  # simple keyword
            if key.lower() in lower_filename:
                return folder

    # Finally keyword matches on content (for selected types)
    if lower_content:
        for key, folder in ROUTES.items():
            if not any(ch in key for ch in "*?[]"):
                if key.lower() in lower_content:
                    return folder

    return None


def move_file(src: Path, subfolder: str):
    dest_dir = DEST_ROOT / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    # Handle name collisions
    if dest.exists():
        stem, suf = dest.stem, dest.suffix
        i = 1
        while True:
            candidate = dest_dir / f"{stem} ({i}){suf}"
            if not candidate.exists():
                dest = candidate
                break
            i += 1

    shutil.move(str(src), str(dest))
    print(f"Moved: {src.name} -> {dest}")


def process_file(path: Path):
    if not path.exists() or not path.is_file():
        return
    if is_temporary_download(path):
        return

    # Let the file settle (avoid moving while browser is still writing)
    time.sleep(SETTLE_SECONDS)

    # Check again after settling
    if not path.exists() or not path.is_file():
        return
    if is_temporary_download(path):
        return

    content = ""
    if path.suffix.lower() in CONTENT_SCAN_EXTS:
        content = extract_text(path)

    subfolder = match_route(path.name, content)
    if subfolder:
        move_file(path, subfolder)


def scan_existing_files():
    for p in DOWNLOADS.iterdir():
        if p.is_file():
            process_file(p)


def main_polling():
    """
    Polling-based watcher (no extra dependencies).
    Scans Downloads every few seconds for new files.
    """
    print(f"Watching: {DOWNLOADS}")
    seen = {p.name for p in DOWNLOADS.iterdir() if p.is_file()}
    try:
        while True:
            current = {p.name for p in DOWNLOADS.iterdir() if p.is_file()}
            new_files = current - seen
            for name in new_files:
                p = DOWNLOADS / name
                threading.Thread(target=process_file, args=(p,), daemon=True).start()
            seen = current
            time.sleep(2)
    except KeyboardInterrupt:
        print("Exiting.")


def main():
    # Try to use watchdog if available for real-time events
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                if not event.is_directory:
                    threading.Thread(target=process_file, args=(Path(event.src_path),), daemon=True).start()

            # Some apps rewrite files; catch modifications too
            def on_modified(self, event):
                if not event.is_directory:
                    threading.Thread(target=process_file, args=(Path(event.src_path),), daemon=True).start()

        print(f"Watching (watchdog): {DOWNLOADS}")
        observer = Observer()
        observer.schedule(Handler(), str(DOWNLOADS), recursive=False)
        observer.start()
        scan_existing_files()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    except ImportError:
        print("watchdog not installed. Falling back to polling.")
        scan_existing_files()
        main_polling()


if __name__ == "__main__":
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    main()
