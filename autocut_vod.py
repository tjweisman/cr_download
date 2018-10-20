#!/usr/bin/python

"""autocut_vod.py

This file provides a CLI for automatically recutting a downloaded
Critical Role VOD in mp4 form.

"""

import sys
from argparse import ArgumentParser
import tempfile
import os
import shutil

from cr_download import autocutter
from cr_download.autocutter_utils import valid_pattern
from cr_download import media_utils

from download_script import videos_to_merged_audio, prompt_title

def init_args():
    parser = ArgumentParser(
        description= """Automatically recut the .mp4 video file for a 
        Critical Role episode"""
    )

    parser.add_argument("filenames", nargs="+",
                        help="""filename(s) of .mp4 files to autocut"""
    )

    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        help="debug mode (keep temporary files)")

    parser.add_argument("-m", "--merge", action="store_true",
                        dest="autocut_merge", help="""merge autocut
                        audio into a single file""")

    parser.add_argument("-n", "--no-autocut", action="store_false",
                        dest="autocut", help="""Don't autocut, just
                        convert to a single unedited audio file""")

    parser.add_argument("-k", "--keep_intro", dest="keep_intro",
                        action="store_true",
                        help=("when autocutting, keep the pre-show"
                              "announcements/intro section"))

    return parser.parse_args(sys.argv[1:])
    

def main(arguments):
    vod = {"title":""}
    title = prompt_title(vod, arguments.autocut)
    tmpdir = tempfile.mkdtemp()
    try:
        filenames = [(None, name) for name in arguments.filenames]
        audio_files = videos_to_merged_audio(filenames,
                                             arguments,
                                             tmpdir,
                                             title)
    finally:
        if not arguments.debug:
            shutil.rmtree(tmpdir)
    

if __name__ == "__main__":
    arguments = init_args()
    main(arguments)
