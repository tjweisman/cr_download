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
                              "when searching for CR episodes"))
    
    parser.add_argument("-n", "--no-upload", dest="upload",
                        action="store_false", default=True,
                        help="Don't upload .mp3s to Google Drive")

    parser.add_argument("-v", dest="verbose", action="store_true",
                        default=False, help="Show more details about vods")


    return parser.parse_args(sys.argv[1:])

def main(arguments):
    vods = twitch_download.get_vod_list(limit=arguments.limit)
    to_download = []
    
    print "{} vod(s) found.".format(len(vods))

    for vod in vods:
        print "Possible CR Episode found: {}".format(vod["title"])
        print "Length: {}".format(timedelta(seconds=int(vod["length"])))

        ep_title = "ep{}.mp3".format(
            twitch_download.guess_ep_num(vod["title"]))
                                  
        if confirm("Download vod as {}?".format(ep_title)):
            to_download.append((vod, ep_title))

    print "Downloading/uploading {} vod(s).".format(len(to_download))

    for vod, ep_title in to_download:
        success = twitch_download.dload_ep_audio(vod, ep_title)
        if success and arguments.upload:
            print "Uploading {} to 'xfer' folder in Google Drive...".format(
                ep_title)
            drive_upload.single_xfer_upload(ep_title)

if __name__ == "__main__":
    arguments = init_args()
    main(arguments)
