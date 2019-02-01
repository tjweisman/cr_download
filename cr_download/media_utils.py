"""This module provides utility functions for audio/video conversion.

Many of these functions are simple wrappers for ffmpeg functionality.

"""

import os
import re
import tempfile
import subprocess

from . import configuration

DEFAULT_FFMPEG_PATH = "ffmpeg"

FFMPEG_PATH = configuration.DATA.get("ffmpeg_path",
                                     DEFAULT_FFMPEG_PATH)

#max length (in seconds) of an audio file cut by mp4_to_audio_segments
AUDIO_SEGMENT_LENGTH = 1800

def file_list(directory, pattern):
    """return a sorted array of files in the given directory matching a
    specified regex.

    files in the returned array are specified relative to the location
    of the specified directory.

    """
    files = os.listdir(directory)
    matched_files = sorted([os.path.join(directory, fname)
                            for fname in files
                            if re.match(pattern, fname)])
    return matched_files

def merge_audio_files(files, output):
    """merge a sequence of audio files into a single one, using ffmpeg.

    """
    with tempfile.NamedTemporaryFile(mode="w+") as filelist:
        for name in files:
            filelist.write("file '{}'\n".format(name))
        filelist.flush()
        subprocess.call([FFMPEG_PATH, "-hide_banner", "-f", "concat",
                         "-safe", "0", "-i", filelist.name, output])

def change_ext(filename, new_ext):
    """return a new filename, with the extension changed.
    """
    return re.sub(r"\.\w+$", new_ext, filename)

def mp4_to_audio_segments(video_file, output_dir, segment_fmt):
    """cut an audio file into segments of length at most
    AUDIO_SEGMENT_LENGTH seconds, using ffmpeg

    file format of the output segments is specificed by segment_fmt.

    return the filenames of the output files, relative to location of
    output_dir.

    """
    basename = os.path.basename(video_file)
    pattern = os.path.join(
        output_dir,
        change_ext(basename, "%03d{}".format(segment_fmt))
    )
    with tempfile.NamedTemporaryFile(mode='w+') as filelist:
        subprocess.call([FFMPEG_PATH, "-hide_banner", "-i", video_file,
                         "-f", "segment", "-segment_time",
                         str(AUDIO_SEGMENT_LENGTH), "-segment_list",
                         filelist.name, pattern])
        split_files = [filename.strip() for filename in filelist]

    split_files = [os.path.join(output_dir, filename)
                   for filename in split_files]

    return split_files

def ffmpeg_convert(input_file, output_file):
    """wrapper function for ffmpeg video to audio conversion.
    """
    subprocess.call([FFMPEG_PATH, "-hide_banner", "-i",
                     input_file, output_file])
    return output_file
