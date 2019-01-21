"""twitch_download.py

This module uses the twitch API to retrieve information about the Geek
and Sundry channel, present the user with videos that are likely to be
Critical Role uploads, and download a Critical Role VOD.

Once again this code is super brittle.

"""

import os
import re
import subprocess
import shlex

import requests

from . import cr_settings

CONFIG_FILENAME = ".streamlinkconfig"

CLIENT_ID = "ignduriqallck9hugiw15zfaqdvgwc"
GANDS_ID = "36619809"

HEADERS = {"Client-ID" : CLIENT_ID,
           "Accept"    : "application/vnd.twitchtv.v5+json"}

def get_gands_id():
    """Retrieve the ID of the Geek & Sundry Twitch channel

    currently not needed, since the G&S ID has already been retrieved
    and hard-coded into the application

    """
    params = {"login":"geekandsundry"}
    response = requests.get("https://api.twitch.tv/kraken/users",
                            headers=HEADERS, params=params)
    return response.json()["users"][0]["_id"]

def get_vod_list(cr_filter=None, limit=10):
    """get JSON array of past broadcast VODs on the G&S channel, most
    recent first

    """
    limit = max(min(limit, 100), 1)
    params = {"broadcast_type":"archive", "limit":str(limit)}
    url = "https://api.twitch.tv/kraken/channels/{}/videos".format(GANDS_ID)
    response = requests.get(url, headers=HEADERS, params=params)
    vods = response.json()["videos"]

    if cr_filter is not None:
        vods = [vod for vod in vods if re.match(cr_filter, vod["title"],
                                                flags=re.I)]

    return vods

def download_video(video, name):
    """download a twitch video using streamlink.

    video: a dictionary object, matching the format of that
    returned by get_vod_list.

    name: the filename to save the video under

    """
    video_url = "twitch.tv/videos/" + video["_id"][1:]

    config_file = os.path.join(cr_settings.CONFIG_DIR, CONFIG_FILENAME)
    cmd = "streamlink --config {} {} 360p -f -o {}".format(
        config_file, video_url, name)
    subprocess.call(shlex.split(cmd))
