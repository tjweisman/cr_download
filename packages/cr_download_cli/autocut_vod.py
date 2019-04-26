"""autocut_vod.py

This file provides a CLI for automatically recutting a downloaded
Critical Role VOD in mp4 form.

"""

from argparse import ArgumentParser
import tempfile
import shutil

from cr_download.configuration import data as config
from . import cli

def _autocut_argparser():
    parser = ArgumentParser(parents=[cli.base_argparser(),
                                     cli.autocutter_argparser()],
                            description="""Automatically recut the .mp4
                            video file for a Critical Role episode""")

    parser.add_argument("filenames", nargs="+",
                        help="""filename(s) of .mp4 files to autocut""")

    parser.add_argument("-n", "--no-autocut", action="store_false",
                        dest="autocut", help="""Don't autocut, just
                        convert to a single unedited audio file""")

    parser.add_argument("-m", "--merge", action="store_true",
                        help="merge all given VODs into a single episode")

    return parser

def main(args):
    parser = _autocut_argparser()
    cli.parse_args(parser, args)

    split_episodes = (config.autocut and not config.autocut_merge)

    vods = {}
    if config.merge:
        title = cli.prompt_title(multiple_parts=split_episodes)
        vods[title] = config.filenames
    else:
        for filename in config.filenames:
            title = cli.prompt_title(multiple_parts=split_episodes)
            vods[title] = [filename]

    tmpdir = tempfile.mkdtemp()
    try:
        audio_files = {
            title: cli.videos_to_episode_audio(video_files, title, tmpdir)
            for title, video_files in vods.items()
        }
        for title, files in audio_files.items():
            print("Output audio files for {}:\n{}".format(
                title, "\n".join(files))
            )
    finally:
        if not config.debug:
            shutil.rmtree(tmpdir)
