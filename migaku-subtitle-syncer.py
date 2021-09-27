import os
import platform
import sys
from pathlib import Path
from shutil import which
from typing import Optional

import ffmpeg
from ffsubsync.ffsubsync import make_parser, run
from PyQt5.QtWidgets import QApplication, QMessageBox
from sortedcontainers import SortedList

app = QApplication([])

ffprobe_command: Optional[str] = ""
ffmpeg_command: Optional[str] = ""

if os.path.isfile("./ffprobe"):
    ffprobe_command = "./ffprobe"
if os.path.isfile("./ffmpeg"):
    ffmpeg_command = "./ffmpeg"
if platform.system() == "Windows":
    ffprobe_command = "ffprobe.exe"
    ffmpeg_command = "ffmpeg.exe"

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


def check_if_video_file(filename):
    try:
        probe = ffmpeg.probe(filename, ffprobe_command)
    except ffmpeg.Error:
        return False
    video_stream = next(
        (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
    )
    if video_stream is None:
        return False
    return True


current_dir_files = os.listdir(os.curdir)
if (
    platform.system() == "Darwin"
    and getattr(sys, "frozen", False)
    and "Contents" in str(os.path.abspath(getattr(sys, "executable", os.curdir)))
):
    bundle_dir = Path(
        os.path.dirname(os.path.abspath(getattr(sys, "executable", os.curdir)))
    )
    basepath = str(bundle_dir.parent.parent.parent.absolute())
    current_dir_files = os.listdir(basepath)
    current_dir_files = [os.path.join(basepath, file) for file in current_dir_files]

video_files = SortedList(list(filter(check_if_video_file, current_dir_files)))
subtitle_files = SortedList(
    [
        file
        for file in current_dir_files
        if any(ext in file for ext in ["srt", "ass", "ssa"])
    ]
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
    new_subtitle_name = subtitle_filename.with_suffix(
        ".synced" + subtitle_filename.suffix
    )

    ffmpeg_parent_folder = Path(ffmpeg_command).parent

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
Would you like to override the original subtitles, leave them as-is or discard all synced subtitles?
Note: this will overwrite all existing subtitles with the same name!

Save - Replaces each original subtitle with its synced counterpart
Close - Quit as-is without renaming subtitles further
Discard - Remove synced subtitles (in case of failure)
    """,
    buttons=QMessageBox.Save | QMessageBox.Close | QMessageBox.Discard,
)

for subtitle_file in subtitle_files:
    original_subtitle = Path(subtitle_file)
    synced_subtitle = original_subtitle.with_suffix(
        ".synced" + original_subtitle.suffix
    )

    if question == QMessageBox.Save:
        os.replace(synced_subtitle, original_subtitle)
    elif question == QMessageBox.Discard:
        os.remove(synced_subtitle)
