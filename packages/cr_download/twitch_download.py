"""twitch_download.py

This module uses the twitch API to retrieve information about the
Critical Role Twitch channel, present the user with videos that are
likely to be Critical Role uploads, and download a Critical Role VOD.

Once again this code is super brittle.

NOTE: ever since Twitch broke API access to restricted streams from
3rd-party apps, this code DOES NOT WORK, and will need to be retested
if Twitch ever chooses to fix it.

"""

from __future__ import print_function

import sys
import re

import requests
import streamlink
import progressbar

from cr_download.configuration import data as config
from cr_download import stream_data

TwitchException = Exception

TWITCH_CLIENT_ID = "ignduriqallck9hugiw15zfaqdvgwc"
CRITROLE_TWITCH_CHANNEL = "criticalrole"

HEADERS = {"Client-ID" : TWITCH_CLIENT_ID,
           "Accept"    : "application/vnd.twitchtv.v5+json"}

DEFAULT_STREAM_QUALITY = "audio"

UNCONFIGURED_TOKEN = "YOUR_TOKEN_HERE"

class TwitchStreamData(stream_data.StreamData):
    def load_data(self, data):
        super(TwitchStreamData, self).load_data(data)

        self.title = data["title"]
        self.creation_date = data["recorded_at"]
        self.length = data["length"]
        self.url = data["url"]
        self.stream = DEFAULT_STREAM_QUALITY

    def download(self, output_filename, output_progress=True):
        oauth_token = _get_oauth_token()
        session = streamlink.Streamlink()
        session.set_plugin_option("twitch", "oauth-token", oauth_token)
        super(TwitchStreamData, self).download(output_filename,
                                               session=session,
                                               output_progress=output_progress)

def _get_oauth_token():
    try:
        if config.twitch_token != UNCONFIGURED_TOKEN:
            return config.twitch_token
    except AttributeError:
        pass

    print("This application is not yet authorized to access "
          "your Twitch account! Run "
          "'streamlink --twitch-oauth-authenticate' "
          "and set 'twitch_token' in your config file to the resulting "
          "value.")
    sys.exit()


def get_channel_id(channel_name):
    """Retrieve the Twitch ID of the channel with the given name

    """
    params = {"login":channel_name}
    response = requests.get("https://api.twitch.tv/kraken/users",
                            headers=HEADERS, params=params)
    return response.json()["users"][0]["_id"]

def get_vod_list(cr_filter=None, limit=10):
    """get JSON array of past broadcast VODs on the G&S channel, most
    recent first

    """
    limit = max(min(limit, 100), 1)
    params = {"broadcast_type":"archive", "limit":str(limit)}
    channel_id = get_channel_id(CRITROLE_TWITCH_CHANNEL)
    url = "https://api.twitch.tv/kraken/channels/{}/videos".format(channel_id)
    response = requests.get(url, headers=HEADERS, params=params)
    vods = response.json()["videos"]

    if cr_filter is not None:
        vods = [vod for vod in vods if re.match(cr_filter, vod["title"],
                                                flags=re.I)]

    return [TwitchStreamData(vod) for vod in vods]

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



# try and set token as soon as the module is loaded so that the user
# knows to configure it if necessary. NOTE: this should be changed if
# we want to let the user set the token on the command line.
_TWITCH_TOKEN = _get_oauth_token()
