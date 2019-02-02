"""twitch_download.py

This module uses the twitch API to retrieve information about the Geek
and Sundry channel, present the user with videos that are likely to be
Critical Role uploads, and download a Critical Role VOD.

Once again this code is super brittle.

"""

from __future__ import print_function

import sys
import re

import requests
import streamlink
import progressbar

from cr_download.configuration import data as config

TwitchException = Exception

TWITCH_CLIENT_ID = "ignduriqallck9hugiw15zfaqdvgwc"
GANDS_ID = "36619809"

HEADERS = {"Client-ID" : TWITCH_CLIENT_ID,
           "Accept"    : "application/vnd.twitchtv.v5+json"}

DEFAULT_STREAM_QUALITY = "360p"

def _get_oauth_token():
    try:
        return config.twitch_token
    except AttributeError:
        print("This application is not yet authorized to access "
              "your Twitch account! Run "
              "'streamlink --twitch-oauth-authenticate "
              "and set 'twitch_token' in your config file to the resulting "
              "value.")
        sys.exit()
        return None


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
    """download a video object to the given output file.
    """
    oauth_token = _get_oauth_token()
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
            progress_bar = _download_progress_bar()

        chunk = stream_file.read(buffer_size)

        while chunk:
            total_downloaded += len(chunk)

            if output_progress:
                progress_bar.update(total_downloaded)

            output_file.write(chunk)
            chunk = stream_file.read(buffer_size)
