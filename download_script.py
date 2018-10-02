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
import shutil

from cr_download import twitch_download, drive_upload
from cr_download.autocutter_utils import valid_pattern
from cr_download import media_utils

DEBUG = False

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
                        help="""automatically cut transitions/
                        breaks from episode""")

    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        help="debug mode (keep temporary files)")

    parser.add_argument("-l", dest="limit", type=int, default=10,
                        help=("Set max number of VODs to retrieve "
                              "when searching for CR episodes (default: 10)"))

    parser.add_argument("-k", "--keep_intro", dest="keep_intro",
                        action="store_true",
                        help=("when autocutting, keep the pre-show"
                              "announcements/intro section"))
    
    parser.add_argument("-M", "--autocut-merge", action="store_true",
                        help=("when autocutting, merge the cut segments " 
                              "into a single file instead of cutting along "
                              "breaks"))
    
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

    parser.add_argument("--strict", action="store_const", dest="regex",
                        const=DEFAULT_CR_REGEX, help = "use a stricter "
                        "regex to match possible CR vods")

    parser.add_argument("-e", "--select", action="store_true",
                        help="list all most recent VODs and select "
                        "which one to download")

    parser.add_argument("-m", "--merge", action="store_true",
                        help="merge all downloaded VODs into a single episode")
                        
    return parser.parse_args(sys.argv[1:])

def guess_title(title, title_format=False):
    #guess the episode number from the title via regex
    m = re.match(".*Critical Role:? (Campaign (\d+):?)? Ep(isode)? ?(\d+).*",
                 title, flags=re.I)
    wildcard = ""
    if title_format:
        wildcard = "_part*"
    if m:
        campaign = "1"
        if m.group(2):
            campaign = m.group(2)
            ep = m.group(4)
        return "c{0}ep{1:03d}{2}.mp3".format(campaign, ep, wildcard)
    
    return "tmp.mp3"

def prompt_title(vod, title_format=False):
    """Ask the user to provide a title (or title pattern) for a vod.

    title_format should contain exactly one '*' (later substituted for).
    """
    ep_title = guess_title(vod["title"], title_format)
    if title_format:
        valid_title = False
        while not valid_title:
            prompt_str = (
                "Enter titles to save vod segments under (default: {})".format(
                    ep_title))
            valid_title = valid_pattern(ep_title)
            if not valid_title:
                print("Enter a title pattern containing exactly one '*'.")
    else:
        prompt_str = (
            "Enter title to save vod under (default: {}): ".format(
                ep_title))
        
    title = raw_input(prompt_str)
    if len(title.strip()) == 0:
        title = ep_title
        
    return title

    
def ask_each_vod(vods, ask_title=True, title_format=False):
    """Ask the user if they want to download each vod in VODs.

    By default, ask the user to provide a title for the saved audio
    file (or a template if multiple audio files will be generated).

    """
    to_download = []
    for vod in vods:
        print u"Possible CR Episode found: {}".format(vod["title"])
        print "Length: {}".format(timedelta(seconds=int(vod["length"])))

        if confirm("Download vod?"):
            if ask_title:
                title = prompt_title(vod, title_format)
                to_download.append((vod, title))
            else:
                to_download.append((vod, None))

    return to_download

def autocut_files(directory, filelist, output_file,
                  keep_intro = True,
                  merge_segments = False,
                  debug = False):
    from cr_download import autocutter
    
    filepaths = [os.path.join(directory, filename) for filename in filelist]
    try:
        print("Attempting to autocut files...")
        autocutter.autocut(filepaths, output_file, keep_intro = keep_intro,
                           debug = debug, merge_segments=merge_segments)
    except autocutter.AutocutterException:
        print("Autocut failed. Merging uncut audio...")
        media_utils.merge_audio_files(filepaths, output_file)

def upload_file(title):
        ostr = u"Uploading {} to 'xfer' folder in Google Drive..."
        print(ostr.format(title))
        drive_upload.single_xfer_upload(title)

def download_vods(to_download, arguments, tmpdir,
                  merge_title=None):
    filelist = []
    for i, (vod, ep_title) in enumerate(to_download):
        filename = os.path.join(tmpdir, "crvid{:02}.mp4".format(i))
        twitch_download.dload_ep_video(vod, filename)
        if arguments.merge:
            if arguments.autocut:
                filelist += media_utils.mp4_to_audio_segments(
                    filename, tmpdir,
                    segment_fmt = ".wav")
            else:
                mfile = os.path.join(
                    tmpdir, media_utils.change_ext(filename, ".wav"))
                filelist.append(media_utils.mp4_to_audio_file(filename, mfile))
                
        else:
            if arguments.autocut:
                filelist = media_utils.mp4_to_audio_segments(
                    filename, ep_title,
                    segment_fmt = ".wav")
                autocut_files(tmpdir, filelist, ep_title,
                              arguments.keep_intro,
                              debug = debug
                )
            else:
                media_utils.mp4_to_audio_file(filename, ep_title)
                    
            if arguments.upload:
                upload_file(ep_title)
                
    if arguments.merge:
        if arguments.autocut:
            autocut_files(tmpdir, filelist, merge_title, arguments.keep_intro,
                          debug = debug)
        else:
            files = [os.path.join(tmpdir, filename) for filename in filelist]
            media_utils.merge_audio_files(files, merge_title)
        if arguments.upload:
            upload_file(merge_title)

        
def main(arguments):
    debug = (DEBUG or arguments.debug)
    cr_filter = arguments.regex
    
    if arguments.select:
        cr_filter = None

    autocut_split = (arguments.autocut and not arguments.autocut_merge)

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
                title = prompt_title(vods[int(index)],
                                     title_format = autocut_split)
                to_download = [(vods[int(index)], title)]
        except ValueError:
            pass
    else:
        to_download = ask_each_vod(vods,
                                   ask_title=not arguments.merge,
                                   title_format = autocut_split)
    merge_title = None
    if arguments.merge and len(vods) > 0:
        merge_title = prompt_title(vods[0], title_format = autocut_split)

    if arguments.upload:
        print "Downloading/uploading %d vod(s)."%len(to_download)
    else:
        print "Downloading %d vod(s)"%len(to_download)
    
    tmpdir = tempfile.mkdtemp()
    try:
        download_vods(to_download, arguments, tmpdir, merge_title)
    finally:
        if not debug:
            shutil.rmtree(tmpdir)
        else:
            print ("Debug mode: downloader script preserving temporary "
                   "directory {}".format(tmpdir))
            
if __name__ == "__main__":
    arguments = init_args()
    main(arguments)
