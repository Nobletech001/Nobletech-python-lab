#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# NOBLETECH DOWNLOADER v1.0
# ============================================================

APP_NAME = "NOBLETECH DOWNLOADER"
VERSION = "1.0"

HOME = Path.home()

# Android shared storage provided by:
# termux-setup-storage
SHARED_STORAGE = HOME / "storage" / "shared"

BASE_DIR = SHARED_STORAGE / "Movies" / "Nobletech"

VIDEO_DIR = BASE_DIR / "Videos"
AUDIO_DIR = BASE_DIR / "Audio"
PLAYLIST_DIR = BASE_DIR / "Playlists"

HISTORY_FILE = BASE_DIR / "history.json"


# ============================================================
# DIRECTORY SETUP
# ============================================================

def setup_directories():
    """Create the required storage directories."""

    directories = [
        BASE_DIR,
        VIDEO_DIR,
        AUDIO_DIR,
        PLAYLIST_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# STORAGE CHECK
# ============================================================

def check_storage():
    """Check whether Termux can access Android shared storage."""

    if not SHARED_STORAGE.exists():
        print()
        print("❌ Android shared storage is not available.")
        print()
        print("Run this command once:")
        print()
        print("    termux-setup-storage")
        print()
        print("Then allow Termux storage permission.")
        return False

    return True


# ============================================================
# DEPENDENCY CHECK
# ============================================================

def check_dependencies():
    """Check required external programs."""

    missing = []

    if shutil.which("yt-dlp") is None:
        missing.append("yt-dlp")

    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")

    if missing:
        print()
        print("❌ Missing required dependencies:")
        print("   " + ", ".join(missing))
        print()
        print("Install them with:")
        print()
        print("    pip install -U yt-dlp")
        print("    pkg install ffmpeg -y")
        print()

        return False

    return True


# ============================================================
# HISTORY
# ============================================================

def load_history():
    """Load download history."""

    if not HISTORY_FILE.exists():
        return []

    try:
        return json.loads(
            HISTORY_FILE.read_text(encoding="utf-8")
        )

    except (json.JSONDecodeError, OSError):
        return []


def save_history(url, mode, status):
    """Save a download event to history."""

    history = load_history()

    history.append({
        "date": datetime.now().isoformat(timespec="seconds"),
        "url": url,
        "mode": mode,
        "status": status,
    })

    try:
        HISTORY_FILE.write_text(
            json.dumps(history, indent=2),
            encoding="utf-8",
        )

    except OSError:
        print("⚠️ Could not save download history.")


def show_history():
    """Display recent downloads."""

    history = load_history()

    if not history:
        print()
        print("📭 No download history yet.")
        return

    print()
    print("=" * 70)
    print("                 DOWNLOAD HISTORY")
    print("=" * 70)

    for item in history[-20:]:
        date = item.get("date", "Unknown")
        mode = item.get("mode", "Unknown")
        status = item.get("status", "Unknown")
        url = item.get("url", "")

        print(f"{date} | {mode:<9} | {status:<8}")
        print(f"  {url}")
        print("-" * 70)


# ============================================================
# COMMON YT-DLP OPTIONS
# ============================================================

def common_options():
    """Options shared by downloads."""

    return [
        "--continue",
        "--no-overwrites",

        # Retry handling
        "--retries", "10",
        "--fragment-retries", "10",

        # Network timeout
        "--socket-timeout", "30",

        # Cleaner terminal output
        "--newline",

        # Preserve original timestamps where possible
        "--no-mtime",

        # Better metadata
        "--embed-metadata",

        # Thumbnail
        "--write-thumbnail",

        # Safer filenames
        "--restrict-filenames",

        # Do not download playlists accidentally
        "--no-playlist",
    ]


# ============================================================
# VIDEO DOWNLOAD
# ============================================================

def download_video(url, subtitles=False):
    """Download the best available non-DRM video/audio combination."""

    command = [
        "yt-dlp",
        *common_options(),

        "-f",
        "bv*+ba/b",

        "--merge-output-format",
        "mp4",

        "-o",
        str(
            VIDEO_DIR /
            "%(title)s.%(ext)s"
        ),
    ]

    if subtitles:
        command += [
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", "all",
            "--embed-subs",
        ]

    return execute_download(
        command,
        url,
        "video",
    )


# ============================================================
# AUDIO DOWNLOAD
# ============================================================

def download_audio(url):
    """Extract the best available audio as MP3."""

    command = [
        "yt-dlp",
        *common_options(),

        "-x",

        "--audio-format",
        "mp3",

        "--audio-quality",
        "0",

        "-o",
        str(
            AUDIO_DIR /
            "%(title)s.%(ext)s"
        ),
    ]

    return execute_download(
        command,
        url,
        "audio",
    )


# ============================================================
# PLAYLIST DOWNLOAD
# ============================================================

def download_playlist(url, audio=False):
    """Download a playlist into its own folder."""

    if audio:
        output_template = (
            str(PLAYLIST_DIR)
            + "/%(playlist_title)s/"
            + "%(playlist_index)03d - %(title)s.%(ext)s"
        )

        command = [
            "yt-dlp",
            "--yes-playlist",
            "--continue",
            "--no-overwrites",
            "--retries", "10",
            "--fragment-retries", "10",
            "--socket-timeout", "30",
            "--newline",
            "--no-mtime",
            "--embed-metadata",
            "--write-thumbnail",
            "--restrict-filenames",

            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",

            "-o",
            output_template,
        ]

        mode = "playlist-audio"

    else:
        output_template = (
            str(PLAYLIST_DIR)
            + "/%(playlist_title)s/"
            + "%(playlist_index)03d - %(title)s.%(ext)s"
        )

        command = [
            "yt-dlp",
            "--yes-playlist",
            "--continue",
            "--no-overwrites",
            "--retries", "10",
            "--fragment-retries", "10",
            "--socket-timeout", "30",
            "--newline",
            "--no-mtime",
            "--embed-metadata",
            "--write-thumbnail",
            "--restrict-filenames",

            "-f",
            "bv*+ba/b",

            "--merge-output-format",
            "mp4",

            "-o",
            output_template,
        ]

        mode = "playlist-video"

    return execute_download(
        command,
        url,
        mode,
    )


# ============================================================
# EXECUTE DOWNLOAD
# ============================================================

def execute_download(command, url, mode):
    """Execute yt-dlp and record the result."""

    print()
    print("=" * 70)
    print(f"        {APP_NAME} v{VERSION}")
    print("=" * 70)
    print(f"Mode: {mode}")
    print()

    if mode == "video":
        print(f"📁 {VIDEO_DIR}")

    elif mode == "audio":
        print(f"📁 {AUDIO_DIR}")

    else:
        print(f"📁 {PLAYLIST_DIR}")

    print("=" * 70)
    print()

    try:
        result = subprocess.run(command + [url])

    except KeyboardInterrupt:
        print()
        print("⚠️ Download cancelled.")
        save_history(url, mode, "cancelled")
        return False

    except FileNotFoundError:
        print()
        print("❌ yt-dlp could not be started.")
        save_history(url, mode, "failed")
        return False

    success = result.returncode == 0

    if success:
        print()
        print("=" * 70)
        print("✅ DOWNLOAD COMPLETED")
        print("=" * 70)
        print()
        print(f"📱 Location: {BASE_DIR}")

        save_history(url, mode, "success")

    else:
        print()
        print("=" * 70)
        print("❌ DOWNLOAD FAILED")
        print("=" * 70)
        print()
        print(
            "The content may be unavailable, unsupported, "
            "restricted, or DRM-protected."
        )

        save_history(url, mode, "failed")

    return success


# ============================================================
# FORMAT INSPECTION
# ============================================================

def show_formats(url):
    """Display formats legitimately available to yt-dlp."""

    print()
    print("=" * 70)
    print("                 AVAILABLE FORMATS")
    print("=" * 70)
    print()

    subprocess.run([
        "yt-dlp",
        "--list-formats",
        url,
    ])


# ============================================================
# INTERACTIVE MENU
# ============================================================

def interactive_menu():
    """Launch interactive downloader menu."""

    while True:

        print()
        print("=" * 70)
        print(f"        {APP_NAME} v{VERSION}")
        print("=" * 70)

        print("""
1. 🎬 Download video
2. 🎵 Download MP3
3. 📋 Download video playlist
4. 🎧 Download playlist as MP3
5. 💬 Video + subtitles
6. 🔎 Show available formats
7. 📜 Download history
8. 🚪 Exit
""")

        choice = input("Choose an option [1-8]: ").strip()

        if choice == "8":
            print()
            print("Nobletech Downloader closed. 👋")
            return

        if choice == "7":
            show_history()
            continue

        if choice not in {"1", "2", "3", "4", "5", "6"}:
            print()
            print("❌ Invalid option.")
            continue

        url = input("\nPaste URL: ").strip()

        if not url:
            print("❌ No URL provided.")
            continue

        if choice == "1":
            download_video(url)

        elif choice == "2":
            download_audio(url)

        elif choice == "3":
            download_playlist(url)

        elif choice == "4":
            download_playlist(url, audio=True)

        elif choice == "5":
            download_video(url, subtitles=True)

        elif choice == "6":
            show_formats(url)


# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Nobletech Downloader"
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="URL to download",
    )

    parser.add_argument(
        "-a",
        "--audio",
        action="store_true",
        help="Extract MP3 audio",
    )

    parser.add_argument(
        "-p",
        "--playlist",
        action="store_true",
        help="Download playlist",
    )

    parser.add_argument(
        "--playlist-audio",
        action="store_true",
        help="Download playlist as MP3",
    )

    parser.add_argument(
        "-s",
        "--subtitles",
        action="store_true",
        help="Download and embed subtitles",
    )

    parser.add_argument(
        "-f",
        "--formats",
        action="store_true",
        help="Show available formats",
    )

    parser.add_argument(
        "-H",
        "--history",
        action="store_true",
        help="Show download history",
    )

    args = parser.parse_args()

    # Prepare directories.
    if not check_storage():
        return 1

    setup_directories()

    # Check required software.
    if not check_dependencies():
        return 1

    # History.
    if args.history:
        show_history()
        return 0

    # Interactive mode.
    if not args.url:
        interactive_menu()
        return 0

    # Format inspection.
    if args.formats:
        show_formats(args.url)
        return 0

    # Playlist audio.
    if args.playlist_audio:
        download_playlist(
            args.url,
            audio=True,
        )
        return 0

    # Playlist video.
    if args.playlist:
        download_playlist(
            args.url,
            audio=False,
        )
        return 0

    # Audio.
    if args.audio:
        download_audio(args.url)
        return 0

    # Default = video.
    download_video(
        args.url,
        subtitles=args.subtitles,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
