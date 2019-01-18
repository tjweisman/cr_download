#!/usr/bin/env python

"""cr_helper.py

This file provides the CLI for the Critical Role download helper.

"""

from __future__ import print_function
from __future__ import unicode_literals
from builtins import input

import re
import sys
from datetime import timedelta
from argparse import ArgumentParser
import tempfile
import os
import shutil

from cr_download import autocutter
from cr_download import twitch_download
from cr_download.autocutter_utils import valid_pattern
from cr_download import media_utils

DEBUG = False

STRICT_CR_REGEX = ".*Critical Role Ep(isode)? ?.*"

DEFAULT_CR_REGEX = ".*Critical Role.*"

def init_args():
    """initialize script arguments

    """
    parser = ArgumentParser(description="Download .mp3 files for Critical "
                            "Role episodes from Twitch")

    parser.add_argument("-a", dest="autocut", action="store_true",
                        help="""automatically cut transitions/
                        breaks from episode""")

    parser.add_argument("-c", dest="cleanup", action="store_true",
                        help="""keep downloaded video files in a temporary
                        directory to be deleted after running""")

    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        help="debug mode (keep temporary files)")

    parser.add_argument("-i", "--index-select", action="store_true",
                        help="""list all most recent VODs and select
                        which one to download""")

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

    parser.add_argument("-l", dest="limit", type=int, default=10,
                        help="""Set max number of VODs to retrieve
                        when searching for CR episodes (default: 10)""")

    parser.add_argument("-m", "--merge", action="store_true",
                        help="merge all downloaded VODs into a single episode")

    parser.add_argument("-M", "--autocut-merge", action="store_true",
                        help="""when autocutting, merge the cut segments into
                        a single file instead of cutting along breaks""")

    parser.add_argument("-n", action="store_const", dest="regex",
                        const=None, help="""don't filter vods at all
                        when searching for CR videos""")

    parser.add_argument("-r", "--regex", default=DEFAULT_CR_REGEX,
                        help=""""what regex to use when filtering for
                        CR vods""")

    parser.add_argument("-u", "--upload", action="store_true",
                        help="Also upload .mp3s to Google Drive")

    parser.add_argument("-v", dest="verbose", action="store_true",
                        default=False, help="Show more details about vods")


    parser.add_argument("--strict", action="store_const", dest="regex",
                        const=DEFAULT_CR_REGEX, help="""use a stricter
                        regex to match possible CR vods""")

    return parser.parse_args(sys.argv[1:])

def suggest_filename(title, multiple_parts=False):
    """suggest a filename to save a Critical Role episode under, given the
    title of its VOD.

    If MULTIPLE_PARTS is specified, suggest a globbed format for
    the filenames for multiple parts of the episode.

    """
    match = re.match(r".*Critical Role:? (Campaign (\d+):?)?,? Ep(isode)? ?(\d+).*",
                     title, flags=re.I)
    wildcard = ""
    if multiple_parts:
        wildcard = "_part*"
    if match:
        campaign = "1"
        if match.group(2):
            campaign = match.group(2)
        episode = int(match.group(4))
        suggestion = "c{0}ep{1:03d}{2}.mp3".format(campaign, episode, wildcard)
    elif not multiple_parts:
        suggestion = "tmp_part*.mp3"
    else:
        suggestion = "tmp.mp3"

    return suggestion

def confirm(prompt):
    """Provide a Y/N prompt for the user, and continue prompting until Y/N
    is input.

    """
    response = "X"
    while response.strip().upper() not in ["Y", "N", ""]:
        response = input(prompt + " [Y]/N ")
        if response.strip().upper() in ["Y", ""]:
            return True
    return False


def prompt_title(vod, multiple_parts=False):
    """Ask the user to provide a title (or title pattern) for a vod.

    title_format should contain exactly one '*' (later substituted for).
    """
    ep_title = suggest_filename(vod["title"], multiple_parts)
    if multiple_parts:
        prompt_str = (
            "Enter titles to save vod segments under (default: {})".format(
                ep_title))
    else:
        prompt_str = (
            "Enter title to save vod under (default: {}): ".format(
                ep_title))

    invalid_title = True
    while invalid_title:
        title = input(prompt_str)
        if not title.strip():
            title = ep_title
        invalid_title = multiple_parts and not valid_pattern(title)
        if invalid_title:
            print("Enter a title pattern containing exactly one '*'.")


    return title

def try_autocut(filepaths, output,
                cutting_sequence="default",
                merge_segments=False,
                debug=False):
    """automatically edit a list of audio files

    OUTPUT is either an audio file name or a substitutable pattern if
    multiple audio files are to be created (i.e. when MERGE_SEGMENTS
    is not specified).

    """
    try:
        print("Attempting to autocut files...")
        outfiles = autocutter.autocut(filepaths, output,
                                      cutting_sequence=cutting_sequence,
                                      debug=debug,
                                      merge_segments=merge_segments)
    except autocutter.AutocutterException:
        #TODO prompt user to see if they still want output if autocut fails
        print("Autocutter failed. Merging uncut audio...")
        outfiles = [media_utils.merge_audio_files(filepaths, output)]

    return outfiles

def _upload_file(title):
    from cr_download import drive_upload

    ostr = "Uploading {} to 'xfer' folder in Google Drive..."
    print((ostr.format(title)))
    drive_upload.single_xfer_upload(title)

def download_vods(ep_title, to_download, dst_dir):
    """Download video files for the vods specified in TO_DOWNLOAD.

    """
    video_files = []
    video_base = media_utils.change_ext(ep_title, "")
    for i, vod in enumerate(to_download):
        filename = os.path.join(dst_dir, "{}{:02}.mp4".format(video_base, i))
        twitch_download.dload_ep_video(vod, filename)
        video_files.append(filename)

    return video_files

def videos_to_episode_audio(video_files, title, arguments, tmpdir):
    """convert all of the files in VIDEO_FILES to one or more audio files.

    if arguments.merge is specified, treat each file in VIDEO_FILES as
    a piece of a larger episode. Otherwise treat each file as an individual episode.

    if arguments.autocut is specified, run the autocutting algorithm
    on each episode before outputting. if, in addition, autocut_merge
    is specified, the different parts of the (autocut) episode are
    merged into a single audio file.

    return the name(s) of the audio file(s) created.

    """

    episodes = []
    for filename in video_files:
        episodes.append(
            media_utils.mp4_to_audio_segments(
                filename, tmpdir,
                segment_fmt=".wav"))

    output_files = []
    for episode_segments in episodes:
        if arguments.autocut:
            output_files += try_autocut(episode_segments, title,
                                        arguments.cutting_sequence,
                                        arguments.autocut_merge,
                                        debug=arguments.debug)
        else:
            output_files.append(media_utils.merge_audio_files(episode_segments, title))

    return output_files

def vod_index_select(vods, split_episodes):
    to_download = {}
    index = input("Select a vod to download (hit enter to not"
                  " download any vods): ")
    try:
        if int(index) > 0 and int(index) <= len(vods):
            title = prompt_title(vods[int(index) - 1],
                                 multiple_parts=split_episodes)
            to_download[title] = [vods[int(index) - 1]]
    except ValueError:
        pass

    return to_download


def vod_confirm_select(vods, merge_files, split_episodes):
    """Prompt the user to confirm downloading each vod from a given list.

    The user is then given a prompt for a filename to save each one under.

    """
    to_download = {}

    episode_vods = []
    for vod in vods:
        print("Possible CR Episode found: {}".format(vod["title"]))
        print("Length: {}".format(timedelta(seconds=int(vod["length"]))))

        if confirm("Download vod?"):
            if not merge_files:
                title = prompt_title(vod, split_episodes)
                to_download[title] = [vod]
            else:
                episode_vods.append(vod)

    if merge_files and episode_vods:
        title = prompt_title(episode_vods[0], split_episodes)
        to_download[title] = episode_vods

    return to_download


def _main(arguments):
    debug = (DEBUG or arguments.debug)

    cr_filter = arguments.regex
    if arguments.index_select:
        cr_filter = None

    vods = twitch_download.get_vod_list(cr_filter=cr_filter,
                                        limit=arguments.limit)

    vods.sort(key=lambda vod: vod["recorded_at"])

    print("{} vod(s) found.".format(len(vods)))
    for i, vod in enumerate(vods):
        print("{}. ({}) {}".format(i+1,
                                   timedelta(seconds=int(vod["length"])),
                                   vod["title"]))

    split_episodes = (arguments.autocut and not arguments.autocut_merge)

    if arguments.index_select:
        to_download = vod_index_select(vods, split_episodes)
    else:
        to_download = vod_confirm_select(vods, arguments.merge,
                                         split_episodes)

    num_vods = sum([len(ep_vods) for ep_vods in to_download.values()])

    tmpdir = tempfile.mkdtemp()

    if arguments.cleanup:
        vod_dir = tmpdir
    else:
        vod_dir = "."

    try:
        print(("Downloading {} vod(s)...".format(num_vods)))
        episode_files = {title: download_vods(title, vods, vod_dir)
                         for title, vods in to_download.items()}

        print("Converting vod(s) to audio...")

        audio_files = {
            title: videos_to_episode_audio(video_files, title, arguments, tmpdir)
            for title, video_files in episode_files.items()
        }

        print("Output audio files to:\n" + "\n".join(sorted(list(audio_files))))

    finally:
        if not debug:
            shutil.rmtree(tmpdir)
        else:
            print(("Debug mode: downloader script preserving temporary "
                   "directory {}".format(tmpdir)))

    if arguments.upload:
        print(("Uploading {} audio file(s)...".format(len(audio_files))))
        for audio_file in audio_files:
            _upload_file(audio_file)

    print("Done.")

if __name__ == "__main__":
    _main(init_args())
