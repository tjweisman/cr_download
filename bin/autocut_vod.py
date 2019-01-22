#!/usr/bin/env python

"""autocut_vod.py

This file provides a CLI for automatically recutting a downloaded
Critical Role VOD in mp4 form.

"""

import sys
from argparse import ArgumentParser
import tempfile
import shutil

from download_script import videos_to_episode_audio, prompt_title

def _init_args():
    parser = ArgumentParser(
        description="""Automatically recut the .mp4 video file for a
        Critical Role episode"""
    )

    parser.add_argument("filenames", nargs="+",
                        help="""filename(s) of .mp4 files to autocut""")

    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        help="debug mode (keep temporary files)")

    parser.add_argument("-m", "--merge", action="store_true",
                        dest="autocut_merge", help="""merge autocut
                        audio into a single file""")

    parser.add_argument("-n", "--no-autocut", action="store_false",
                        dest="autocut", help="""Don't autocut, just
                        convert to a single unedited audio file""")

    parser.add_argument("--cutting-sequence", default="default",
                        help="""which cutting sequence to use when autocutting
                        files (default behavior specified in config file)""")

    parser.add_argument("-k", "--keep-intro", action="store_const",
                        dest="cutting_sequence", const="keep",
                        help="""when autocutting, keep the pre-show
                        announcements/intro section""")

    parser.add_argument("--cut-intro", action="store_const",
                        dest="cutting_sequence", const="cut",
                        help="""when autocutting, cut the pre-show
                        announcements/intro section""")

    return parser.parse_args(sys.argv[1:])


def _main(arguments):
    vod = {"title":""}
    title = prompt_title(vod, arguments.autocut)
    tmpdir = tempfile.mkdtemp()
    try:

        audio_files = videos_to_episode_audio(arguments.filenames, title,
                                              arguments, tmpdir)

        print("Output audio files to:\n" + "\n".join(sorted(list(audio_files))))
    finally:
        if not arguments.debug:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    _main(_init_args())
