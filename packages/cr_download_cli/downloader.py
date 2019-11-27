from __future__ import print_function
from __future__ import unicode_literals
from builtins import input

from datetime import timedelta
from argparse import ArgumentParser
import tempfile
import os
import re
import shutil

from cr_download.configuration import data as config
from cr_download import twitch_download
from cr_download import youtube
from cr_download import media_utils
from cr_download import metadata

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

    download_args.add_argument("-s", "--source", default="youtube",
                               help="""where to look for recent
                               Critical Role streams (twitch or
                               youtube). Default: youtube""")

    # regex arguments
    download_args.add_argument("-r", "--regex", default=DEFAULT_CR_REGEX,
                               help="""what regex to use when filtering for
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

    download_args.add_argument("--metadata-file", help="""name of a YAML file that
                               will be output with a description of each episode
                               downloaded""")


    return parser

def _upload_file(title):
    from cr_download import drive_upload

    ostr = "Uploading {} to 'xfer' folder in Google Drive..."
    print((ostr.format(title)))
    drive_upload.single_xfer_upload(title)

def download_streams(base_name, to_download, dst_dir):
    """Download video files for the streams specified in to_download.

    """
    video_files = []
    video_base = media_utils.change_ext(base_name, "")
    for i, stream in enumerate(to_download):
        filename = os.path.join(dst_dir, "{}{:02}".format(video_base, i))
        output_filename = stream.download(filename)
        video_files.append(output_filename)

    return video_files


def stream_index_select(streams, split_episodes):
    to_download = {}
    index = input("Select a stream to download (hit enter to not"
                  " download any streams): ")
    try:
        if int(index) > 0 and int(index) <= len(streams):
            title = cli.prompt_title(streams[int(index) - 1]["title"],
                                     multiple_parts=split_episodes)
            to_download[title] = [streams[int(index) - 1]]
    except ValueError:
        pass

    return to_download


def stream_confirm_select(streams, merge_files, split_episodes):
    """Prompt the user to confirm downloading each stream from a given list.

    The user is then given a prompt for a filename to save each one under.

    """
    to_download = {}

    episode_streams = []
    for stream in streams:
        print("Possible CR Episode found: {}".format(stream["title"]))
        print("Length: {}".format(stream["length"]))

        if cli.confirm("Download stream?"):
            if not merge_files:
                title = cli.prompt_title(stream["title"], split_episodes)
                to_download[title] = [stream]
            else:
                episode_streams.append(stream)

    if merge_files and episode_streams:
        title = cli.prompt_title(episode_streams[0]["title"], split_episodes)
        to_download[title] = episode_streams

    return to_download

def filter_stream_list(streams, title_regex):
    return [stream for stream in streams
            if re.match(title_regex, stream["title"], flags=re.I)]

def main(args):
    parser = _downloader_argparser()
    cli.parse_args(parser, args)

    cr_filter = config.regex
    if config.index_select:
        cr_filter = None

    if config.source == "youtube":
        streams = youtube.get_recent_channel_uploads(limit=config.limit)
    elif config.source == "twitch":
        streams = twitch_download.get_vod_list(limit=config.limit)
    else:
        raise Exception(
            "Invalid stream source specified: {}".format(config.source))

    if cr_filter:
        streams = filter_stream_list(streams, cr_filter)

    streams.sort(key=lambda stream: stream["creation_date"], reverse=True)

    print("{} stream(s) found.".format(len(streams)))
    for i, stream in enumerate(streams):
        print("{}. ({}) {}".format(i+1, stream["length"],
                                   stream["title"]))

    split_episodes = (config.autocut and not config.autocut_merge)

    if config.index_select:
        to_download = stream_index_select(streams, split_episodes)
    else:
        to_download = stream_confirm_select(streams, config.merge,
                                         split_episodes)

    num_streams = sum([len(ep_streams) for ep_streams in to_download.values()])

    tmpdir = tempfile.mkdtemp()

    if config.cleanup:
        stream_dir = tmpdir
    else:
        stream_dir = "."

    try:
        print(("Downloading {} stream(s)...".format(num_streams)))
        episode_files = {title: download_streams(title, streams, stream_dir)
                         for title, streams in to_download.items()}

        print("Converting stream(s) to audio...")

        audio_files = {
            title: cli.videos_to_episode_audio(
                video_files, title, tmpdir)
            for title, video_files in episode_files.items()
        }
        for title, files in audio_files.items():
            print("Output audio files for {}:\n{}".format(
                title, "\n".join(files))
            )

        if config.metadata_file:
            metadata.write_metadata_file(config.metadata_file,
                                         audio_files,
                                         to_download)



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
