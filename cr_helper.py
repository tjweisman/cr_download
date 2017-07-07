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

import twitch_download, drive_upload

if __name__ == "__main__":
    vods = twitch_download.get_vod_list()
    vod_files = twitch_download.scan_vods(vods)

    for vod in vod_files:
        print "Uploading {} to 'xfer' folder in Google Drive...".format(vod)
        drive_upload.single_xfer_upload(vod)
