import logging
import multiprocessing
import os
import platform
import sys
from pathlib import Path
from shutil import which
from typing import Optional

from ffsubsync.ffsubsync import make_parser, run
from PyQt5.QtWidgets import QApplication, QMessageBox
from sortedcontainers import SortedList

LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
logging.basicConfig(level=LOGLEVEL)

multiprocessing.freeze_support()


app = QApplication([])

ffprobe_command: Optional[str] = ""
ffmpeg_command: Optional[str] = ""


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    logging.debug(f"base path: {base_path}")
    return os.path.join(base_path, relative_path)


if os.path.isfile(resource_path("./ffprobe")):
    ffprobe_command = resource_path("./ffprobe")
if os.path.isfile(resource_path("./ffmpeg")):
    ffmpeg_command = resource_path("./ffmpeg")
if platform.system() == "Windows":
    ffprobe_command = resource_path("ffprobe.exe")
    ffmpeg_command = resource_path("ffmpeg.exe")


if not ffprobe_command:
    ffprobe_command = which("ffprobe")
if not ffmpeg_command:
    ffmpeg_command = which("ffmpeg")

missing_program = ""
if not ffprobe_command:
    missing_program = "ffprobe"
if not ffmpeg_command:
    missing_program = "ffmpeg"
if missing_program:
    QMessageBox.critical(
        None,
        "Migaku Error Dialog",
        f"It seems {missing_program} is not installed. Please retry after installing",
        buttons=QMessageBox.Ok,
    )
    sys.exit(1)

logging.info(f"ffprobe path: {ffprobe_command}")
logging.info(f"ffmpeg path: {ffmpeg_command}")

video_file_endings = [
    ".webm",
    ".mkv",
    ".flv",
    ".flv",
    ".vob",
    ".ogv",
    ".ogg",
    ".drc",
    ".gif",
    ".gifv",
    ".mng",
    ".avi",
    ".MTS",
    ".M2TS",
    ".TS",
    ".mov",
    ".qt",
    ".wmv",
    ".yuv",
    ".rm",
    ".rmvb",
    ".viv",
    ".asf",
    ".amv",
    ".mp4",
    ".m4p",
    ".m4v",
    ".mpg",
    ".mp2",
    ".mpeg",
    ".mpe",
    ".mpv",
    ".mpg",
    ".mpeg",
    ".m2v",
    ".m4v",
    ".svi",
    ".3gp",
    ".3g2",
    ".mxf",
    ".roq",
    ".nsv",
    ".flv",
    ".f4v",
    ".f4p",
    ".f4a",
    ".f4b",
]


def check_if_video_file(filename):
    file_extension = Path(filename).suffix
    return bool(any(ext == file_extension for ext in video_file_endings))


current_dir_files = os.listdir(os.curdir)
if (
    platform.system() == "Darwin"
    and getattr(sys, "frozen", False)
    and "Contents" in str(os.path.abspath(getattr(sys, "executable", os.curdir)))
):
    bundle_dir = Path(os.path.dirname(os.path.abspath(getattr(sys, "executable", os.curdir))))
    basepath = str(bundle_dir.parent.parent.parent.absolute())
    current_dir_files = os.listdir(basepath)
    current_dir_files = [os.path.join(basepath, file) for file in current_dir_files]

video_files = SortedList(list(filter(check_if_video_file, current_dir_files)))
subtitle_files = SortedList(
    [file for file in current_dir_files if any(ext == Path(file).suffix for ext in ["srt", "ass", "ssa"])]
)

if len(video_files) != len(subtitle_files):
    button = QMessageBox.warning(
        None,
        "Migaku Warning Dialog",
        """
There is an uneven amount of video files and subtitles in this folder.
Please make sure there are as many subtitles as there are video files.
        """,
        buttons=QMessageBox.Ok,
    )
    sys.exit(0)

for subtitle, video in zip(subtitle_files, video_files):
    subtitle_filename = Path(subtitle)
    new_subtitle_name = subtitle_filename.with_suffix(".synced" + subtitle_filename.suffix)

    ffmpeg_parent_folder = Path(os.path.abspath(ffmpeg_command)).parent
    logging.debug(f"ffmpeg parent: {ffmpeg_parent_folder}")
    logging.debug(f"video: {video}")
    logging.debug(f"subtitle: {subtitle}")

    unparsed_args = [
        video,
        "-i",
        subtitle,
        "-o",
        str(new_subtitle_name),
        "--ffmpegpath",
        str(ffmpeg_parent_folder),
    ]

    print(unparsed_args)
    parser = make_parser()
    args = parser.parse_args(args=unparsed_args)
    result = run(args)

question = QMessageBox.question(
    None,
    'Save without ".synced"',
    """
Would you like to override the original subtitles?

Save - Replaces each original subtitle with its synced counterpart
Close - Quit as-is without renaming subtitles further
    """,
    buttons=QMessageBox.Save | QMessageBox.Close,
)

for subtitle_file in subtitle_files:
    original_subtitle = Path(subtitle_file)
    synced_subtitle = original_subtitle.with_suffix(".synced" + original_subtitle.suffix)

    if question == QMessageBox.Save:
        os.replace(synced_subtitle, original_subtitle)
    elif question == QMessageBox.Discard:
        os.remove(synced_subtitle)
