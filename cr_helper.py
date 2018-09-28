#!/usr/bin/python

"""cr_helper.py

Main file for the Critical Role download helper

This program checks recent Geek and Sundry Twitch VODs for videos with
titles looking like Critical Role episode titles, and prompts the user
to download each one. The file is downloaded as video using the
"streamlink" program, and converted to .mp3 using ffmpeg. Then the
script uploads each .mp3 file to the "xfer" folder in Google Drive.

This is super brittle and not amazingly customizable, but at least I
spent some time commenting my code.

"""

import re
import sys
from datetime import timedelta
from argparse import ArgumentParser
import tempfile
import os

import twitch_download, drive_upload
from autocutter.autocutter_utils import change_ext


STRICT_CR_REGEX = ".*Critical Role Ep(isode)? ?.*"

DEFAULT_CR_REGEX = ".*Critical Role.*"

def confirm(prompt):
    confirm = "X"
    while confirm.strip().upper() not in ["Y", "N", ""]:
        confirm = raw_input(prompt + " [Y]/N ")
        if confirm.strip().upper() in ["Y", ""]:
            return True
    return False

def init_args():
    parser = ArgumentParser(description="Download .mp3 files for Critical "
                            "Role episodes from Twitch")

    parser.add_argument("-a", dest="autocut", action="store_true",
                        help=("automatically cut transitions/breaks "
                              "from episode"))

    parser.add_argument("-l", dest="limit", type=int, default=10,
                        help=("Set max number of VODs to retrieve "
                              "when searching for CR episodes (default: 10)"))
    
    parser.add_argument("-u", "--upload", action="store_true",
                        help="Also upload .mp3s to Google Drive")

    parser.add_argument("-v", dest="verbose", action="store_true",
                        default=False, help="Show more details about vods")

    parser.add_argument("-r", "--regex", default=DEFAULT_CR_REGEX,
                        help = "what regex to use when filtering for "
                        "CR vods")

    parser.add_argument("-n", action="store_const", dest="regex",
                        const=None, help="don't filter vods at all "
                        "when searching for CR videos")

    parser.add_argument("-s", action="store_const", dest="regex",
                        const=DEFAULT_CR_REGEX, help = "use a stricter "
                        "regex to match possible CR vods")

    parser.add_argument("-e", "--select", action="store_true",
                        help="list all most recent VODs and select "
                        "which one to download")

    parser.add_argument("-m", "--merge", action="store_true",
                        help="merge all downloaded VODs into a single file")
                        
    return parser.parse_args(sys.argv[1:])

def guess_title(title):
    #guess the episode number from the title via regex
    m = re.match(".*Critical Role:? (Campaign (\d+):?)? Ep(isode)? ?(\d+).*",
                 title, flags=re.I)
    if m:
        campaign = "1"
        if m.group(2):
            campaign = m.group(2)
            ep = m.group(4)
        return "c{0}ep{1}.mp3".format(campaign, ep)
    
    return "tmp.mp3"


def prompt_title(vod):
    ep_title = guess_title(vod["title"])
    title = raw_input(
                "Enter title to save vod under (default: %s): "%ep_title)
    if len(title.strip()) == 0:
        title = ep_title
        
    return title

    
def ask_each_vod(vods):
    to_download = []
    for vod in vods:
        print u"Possible CR Episode found: {}".format(vod["title"])
        print "Length: {}".format(timedelta(seconds=int(vod["length"])))

        if confirm("Download vod?"):
            title = prompt_title(vod)
            to_download.append((vod, title))

    return to_download

def main(arguments):
    cr_filter = arguments.regex
    
    if arguments.select:
        cr_filter = None
        
    vods = twitch_download.get_vod_list(cr_filter=cr_filter,
                                        limit=arguments.limit)

    vods.sort(key = lambda vod: vod["recorded_at"])
    
    print "%d vod(s) found."%len(vods)
    for i, vod in enumerate(vods):
        print "%d. (%s) %s"%(i+1,
                             timedelta(seconds=int(vod["length"])),
                             vod["title"])

    to_download = []
    
    if arguments.select:
        index = raw_input("Select a vod to download (hit enter to not"
                          " download any vods): ")
        try:
            if int(index) > 0 and int(index) <= len(vods):
                title = prompt_title(vods[int(index)])
                to_download = [(vods[int(index)], title)]
        except ValueError:
            pass
    else:
        to_download = ask_each_vod(vods)

    if arguments.upload:
        print "Downloading/uploading %d vod(s)."%len(to_download)
    else:
        print "Downloading %d vod(s)"%len(to_download)

    for i, (vod, ep_title) in enumerate(to_download):
        tmpdir = tempfile.mkdtemp()
        filename = os.path.join(tmpdir, "crvid{:02}.mp4".format(i))
        twitch_download.dload_ep_video(vod, filename)
        if arguments.merge:
            twitch_download.mp4_to_audio(filename,
                                         change_ext(filename, ".wav"),
                                         segment = arguments.autocut,
                                         segment_fmt = ".wav")
        else:
            twitch_download.mp4_to_audio(filename, ep_title,
                                         segment = arguments.autocut,
                                         segment_fmt = ".wav")
            if arguments.autocut:
                pass
        
        if success and arguments.upload:
            print u"Uploading {} to 'xfer' folder in Google Drive...".format(
                ep_title)
            drive_upload.single_xfer_upload(ep_title)
                            
if __name__ == "__main__":
    arguments = init_args()
    main(arguments)
