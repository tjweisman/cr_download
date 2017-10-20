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

import twitch_download, drive_upload, sys
from datetime import timedelta
from argparse import ArgumentParser

DEFAULT_CR_REGEX = ".*Critical Role Ep(isode)? ?.*"

WIDE_CR_REGEX = ".*Critical Role.*"

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

    parser.add_argument("-w", action="store_const", dest="regex",
                        const=WIDE_CR_REGEX, help = "use a less "
                        "restrictive regex to match possible CR vods")
                        
    return parser.parse_args(sys.argv[1:])
                        
def main(arguments):
    vods = twitch_download.get_vod_list(cr_filter=arguments.regex,
                                        limit=arguments.limit)
                        
    to_download = []
    
    print "%d vod(s) found."%len(vods)
    for i, vod in enumerate(vods):
        print "%d. (%s) %s"%(i+1,
                             timedelta(seconds=int(vod["length"])),
                             vod["title"])
                        
    for vod in vods:
        print "Possible CR Episode found: {}".format(vod["title"])
        print "Length: {}".format(timedelta(seconds=int(vod["length"])))
                            
        ep_title = "ep{}.mp3".format(
            twitch_download.guess_ep_num(vod["title"]))

        if confirm("Download vod?"):
            title = raw_input(
                "Enter title to save vod under (default: %s): "%ep_title)
            if len(title.strip()) == 0:
                title = ep_title
                
            to_download.append((vod, ep_title))

    if arguments.upload:
        print "Downloading/uploading {} vod(s)."%len(to_download)
    else:
        print "Downloading %d vod(s)"%len(to_download)
        
    for vod, ep_title in to_download:
        success = twitch_download.dload_ep_audio(vod, ep_title)
        if success and arguments.upload:
            print "Uploading {} to 'xfer' folder in Google Drive...".format(
                ep_title)
            drive_upload.single_xfer_upload(ep_title)
                            
if __name__ == "__main__":
    arguments = init_args()
    main(arguments)
