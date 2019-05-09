from __future__ import print_function
from __future__ import unicode_literals
from builtins import input

from datetime import timedelta
from argparse import ArgumentParser
import tempfile
import os
import shutil

from cr_download.configuration import data as config
from cr_download import twitch_download
from cr_download import media_utils

from . import cli

STRICT_CR_REGEX = ".*Critical Role Ep(isode)? ?.*"

DEFAULT_CR_REGEX = ".*Critical Role.*"


def _downloader_argparser():
    base_parser = cli.base_argparser()
    autocut_parser = cli.autocutter_argparser()
    parser = ArgumentParser(parents=[base_parser, autocut_parser],
                            description="Download .mp3 files for Critical "
                            "Role episodes from Twitch")

    parser.add_argument("-a", dest="autocut", action="store_true",
                        help="""automatically cut transitions/
                        breaks from episode""")

    parser.add_argument("-m", "--merge", action="store_true",
                        help="merge all downloaded VODs into a single episode")

    parser.add_argument("-u", "--upload", action="store_true",
                        help="Also upload .mp3s to Google Drive")


    download_args = parser.add_argument_group("downloader")

    download_args.add_argument("-c", dest="cleanup", action="store_true",
                               help="""keep downloaded video files in a temporary
                               directory to be deleted after running""")

    download_args.add_argument("-i", "--index-select", action="store_true",
                               help="""list all most recent VODs and select
                               which one to download""")

    download_args.add_argument("-l", dest="limit", type=int, default=10,
                               help="""Set max number of VODs to retrieve
                               when searching for CR episodes (default: 10)""")


    # regex arguments
    download_args.add_argument("-r", "--regex", default=DEFAULT_CR_REGEX,
                               help=""""what regex to use when filtering for
                               CR vods""")

    download_args.add_argument("--strict", action="store_const",
                               dest="regex", const=STRICT_CR_REGEX,
                               help="""use a stricter regex to match
                               possible CR vods""")

    download_args.add_argument("-n", action="store_const", dest="regex",
                               const=None, help="""don't filter vods at all
                               when searching for CR videos""")


    download_args.add_argument("-v", dest="verbose", action="store_true",
                               default=False, help="Show more details about vods")


    return parser

def _upload_file(title):
    from cr_download import drive_upload

    ostr = "Uploading {} to 'xfer' folder in Google Drive..."
    print((ostr.format(title)))
    drive_upload.single_xfer_upload(title)

def download_vods(base_name, to_download, dst_dir):
    """Download video files for the vods specified in TO_DOWNLOAD.

    """
    video_files = []
    video_base = media_utils.change_ext(base_name, "")
    for i, vod in enumerate(to_download):
        filename = os.path.join(dst_dir, "{}{:02}.mp4".format(video_base, i))
        twitch_download.download_video(vod, filename)
        video_files.append(filename)

    return video_files


def vod_index_select(vods, split_episodes):
    to_download = {}
    index = input("Select a vod to download (hit enter to not"
                  " download any vods): ")
    try:
        if int(index) > 0 and int(index) <= len(vods):
            title = cli.prompt_title(vods[int(index) - 1]["title"],
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

        if cli.confirm("Download vod?"):
            if not merge_files:
                title = cli.prompt_title(vod["title"], split_episodes)
                to_download[title] = [vod]
            else:
                episode_vods.append(vod)

    if merge_files and episode_vods:
        title = cli.prompt_title(episode_vods[0]["title"], split_episodes)
        to_download[title] = episode_vods

    return to_download

def main(args):
    parser = _downloader_argparser()
    cli.parse_args(parser, args)

    cr_filter = config.regex
    if config.index_select:
        cr_filter = None

    vods = twitch_download.get_vod_list(cr_filter=cr_filter,
                                        limit=config.limit)

    vods.sort(key=lambda vod: vod["recorded_at"], reverse=True)

    print("{} vod(s) found.".format(len(vods)))
    for i, vod in enumerate(vods):
        print("{}. ({}) {}".format(i+1,
                                   timedelta(seconds=int(vod["length"])),
                                   vod["title"]))

    split_episodes = (config.autocut and not config.autocut_merge)

    if config.index_select:
        to_download = vod_index_select(vods, split_episodes)
    else:
        to_download = vod_confirm_select(vods, config.merge,
                                         split_episodes)

    num_vods = sum([len(ep_vods) for ep_vods in to_download.values()])

    tmpdir = tempfile.mkdtemp()

    if config.cleanup:
        vod_dir = tmpdir
    else:
        vod_dir = "."

    try:
        print(("Downloading {} vod(s)...".format(num_vods)))
        episode_files = {title: download_vods(title, vods, vod_dir)
                         for title, vods in to_download.items()}

        print("Converting vod(s) to audio...")

        audio_files = {
            title: cli.videos_to_episode_audio(
                video_files, title, tmpdir)
            for title, video_files in episode_files.items()
        }
        for title, files in audio_files.items():
            print("Output audio files for {}:\n{}".format(
                title, "\n".join(files))
            )

    finally:
        if not config.debug:
            shutil.rmtree(tmpdir)
        else:
            print(("Debug mode: downloader script preserving temporary "
                   "directory {}".format(tmpdir)))

    if config.upload:
        print("Auto-uploader currently disabled.")
        #print(("Uploading {} audio file(s)...".format(len(audio_files))))
        #for audio_file in audio_files:
        #    _upload_file(audio_file)

    print("Done.")
