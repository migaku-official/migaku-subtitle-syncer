import os
import sys
from pathlib import Path

import ffmpeg
from ffsubsync.ffsubsync import make_parser, run
from PyQt5.QtWidgets import QApplication, QMessageBox
from sortedcontainers import SortedList

app = QApplication([])


def check_if_video_file(filename):
    try:
        probe = ffmpeg.probe(filename)
    except ffmpeg.Error:
        return False
    video_stream = next(
        (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
    )
    if video_stream is None:
        return False
    return True


current_dir_files = os.listdir(os.curdir)
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
Please make sure there are as many subtitles as there are video files.""",
        buttons=QMessageBox.Ok,
    )
    sys.exit(0)

for subtitle, video in zip(subtitle_files, video_files):
    subtitle_filename = Path(subtitle)
    new_subtitle_name = subtitle_filename.with_suffix(
        ".synced" + subtitle_filename.suffix
    )

    unparsed_args = [
        video,
        "-i",
        subtitle,
        "-o",
        str(new_subtitle_name),
    ]

    print(unparsed_args)
    parser = make_parser()
    args = parser.parse_args(args=unparsed_args)
    result = run(args)

question = QMessageBox.question(
    None,
    "Save without \".synced\"",
    """
Would you like to save these subs without \".synced\", leave them as ".synced" or discard the resynced subtitles?
Note that this may overwritte any existing subs with the same name
    """,
    buttons=QMessageBox.Save | QMessageBox.Close | QMessageBox.Discard
)

for subtitle_file in subtitle_files:
    subtitle_filename = Path(subtitle_file)
    old_subtitle_path = subtitle_filename.with_suffix(".synced" + subtitle_filename.suffix)

    if question == QMessageBox.Save:
        os.replace(subtitle_filename, old_subtitle_path)
    elif question == QMessageBox.Discard:
        os.remove(old_subtitle_path)
