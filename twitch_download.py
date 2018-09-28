"""twitch_download.py

This module uses the twitch API to retrieve information about the Geek
and Sundry channel, present the user with videos that are likely to be
Critical Role uploads, and download a Critical Role VOD.

Once again this code is super brittle.

"""

import requests, json, re, subprocess, shlex
import tempfile
import shutil
import os

from autocutter import autocutter
from autocutter.autocutter_utils import file_list

CLIENT_ID="ignduriqallck9hugiw15zfaqdvgwc"
GANDS_ID="36619809"

headers = {"Client-ID" : CLIENT_ID,
           "Accept"    : "application/vnd.twitchtv.v5+json"}

def get_gands_id():
    #currently not needed, since the G&S ID has already been retrieved
    #and hard-coded into the application
    params = {"login":"geekandsundry"}
    r = requests.get("https://api.twitch.tv/kraken/users",
                     headers=headers, params=params)
    return r.json()["users"][0]["_id"]

def get_vod_list(cr_filter=None, limit=10):
    #get JSON array of past broadcast VODs on the G&S channel, most
    #recent first
    limit = max(min(limit, 100), 1)
    params = {"broadcast_type":"archive", "limit":str(limit)}
    url = "https://api.twitch.tv/kraken/channels/{}/videos".format(GANDS_ID)
    r = requests.get(url, headers=headers,params=params)
    vods = r.json()["videos"]

    if cr_filter is not None:
        vods = [vod for vod in vods if re.match(cr_filter, vod["title"],
                                                flags=re.I)]

    return vods

def get_titles(video_list):
    return [video["title"] for video in video_list]

def dload_ep_video(video, name):
    video_url = "twitch.tv/videos/" + video["_id"][1:]

    cmd = "streamlink --config .streamlinkconfig {} 360p -f -o {}".format(
        video_url, name)
    subprocess.call(shlex.split(cmd))
