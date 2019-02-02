"""twitch_download.py

This module uses the twitch API to retrieve information about the Geek
and Sundry channel, present the user with videos that are likely to be
Critical Role uploads, and download a Critical Role VOD.

Once again this code is super brittle.

"""

from __future__ import print_function

import sys
import os
import re
import subprocess
import shlex

import requests
import streamlink
from streamlink_cli.main import setup_console, twitch
import progressbar

from . import media_utils
from . import configuration
from . import cli

TwitchException = Exception

CONFIG_FILENAME = ".streamlinkconfig"

TWITCH_CLIENT_ID = "ignduriqallck9hugiw15zfaqdvgwc"
GANDS_ID = "36619809"

HEADERS = {"Client-ID" : CLIENT_ID,
           "Accept"    : "application/vnd.twitchtv.v5+json"}

DEFAULT_STREAM_QUALITY = "360p"

def _get_oauth_token(retrieve_token=True):
    try:
        return configuration.data["twitch_token"]
    except KeyError:
        if retrieve_token:
            launch_browser = cli.confirm("""This application is not yet
            authorized to access your Twitch account. Launch a web browser
            now to obtain an authorization token?""")
            if launch_browser:
                #TODO: actually launch a browser here, hopefully
                #without relying on streamlink living in the user's
                #path
                return
        raise

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

def _download_progress_bar():
    widgets = [
        'Downloaded: ',
        progressbar.DataSize(),
        '(',
        progressbar.FileTransferSpeed(),
        ')'
    ]
    return progressbar.ProgressBar(widgets=widgets)

def download_video(video, filename, buffer_size=8192,
                       output_progress=True):

    oauth_token = _get_oauth_token(retrieve_token=False)
    session = streamlink.Streamlink()
    session.set_plugin_option("twitch", "oauth-token", oauth_token)

    streams = session.streams(video["url"])

    if streams and DEFAULT_STREAM_QUALITY in streams:
        stream = streams[DEFAULT_STREAM_QUALITY]
    else:
        raise TwitchException("Could not find stream {1} at url {2}".format(
            DEFAULT_STREAM_QUALITY, video["url"]))

    total_downloaded = 0
    with stream.open() as stream_file, open(filename, "wb") as output_file:
        if output_progress:
            bar = _download_progress_bar()

        chunk = stream_file.read(buffer_size)

        while chunk:
            total_downloaded += len(chunk)

            if output_progress:
                bar.update(total_downloaded)

            output_file.write(chunk)
            chunk = stream_file.read(buffer_size)
