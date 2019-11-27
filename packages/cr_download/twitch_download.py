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

from datetime import timedelta
import sys
import re

import requests
import streamlink

from cr_download.configuration import data as config
from cr_download import stream_data

TWITCH_CLIENT_ID = "ignduriqallck9hugiw15zfaqdvgwc"
CRITROLE_TWITCH_CHANNEL = "criticalrole"

HEADERS = {"Client-ID" : TWITCH_CLIENT_ID,
           "Accept"    : "application/vnd.twitchtv.v5+json"}

DEFAULT_STREAM_QUALITY = "audio"

UNCONFIGURED_TOKEN = "YOUR_TOKEN_HERE"

class TwitchStreamData(stream_data.StreamData):
    def load_data(self, data):
        #hold onto all of the data in the Twitch json object, just in
        #case we want to use it later
        self.json_data = data

        self.title = data["title"]
        self.creation_date = data["recorded_at"]

        self.length = str(timedelta(seconds=int(data["length"])))
        self.url = data["url"]
        self.stream = DEFAULT_STREAM_QUALITY

    def download(self, filename, output_progress=True):
        output_filename = filename + ".mp4"
        download_twitch_vod(self.url, DEFAULT_STREAM_QUALITY,
                            output_filename, output_progress=output_progress)
        return output_filename

def _get_oauth_token():
    try:
        if config.twitch_token != UNCONFIGURED_TOKEN:
            return config.twitch_token
    except AttributeError:
        pass

    #if we're not using twitch as a video source, we can ignore an
    #unconfigured token
    if config.stream != "twitch":
        return None

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

def get_vod_list(limit=10):
    """get JSON array of past broadcast VODs on the G&S channel, most
    recent first

    """
    limit = max(min(limit, 100), 1)
    params = {"broadcast_type":"archive", "limit":str(limit)}
    channel_id = get_channel_id(CRITROLE_TWITCH_CHANNEL)
    url = "https://api.twitch.tv/kraken/channels/{}/videos".format(channel_id)
    response = requests.get(url, headers=HEADERS, params=params)
    vods = response.json()["videos"]

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

def download_twitch_vod(url, stream_name, output_filename,
                        buffer_size=8192, output_progress=True):
    """download a video object to the given output file.
    """
    oauth_token = _get_oauth_token()
    session = streamlink.Streamlink()
    session.set_plugin_option("twitch", "oauth-token", oauth_token)

    streams = session.streams(url)

    if streams and stream_name in streams:
        stream = streams[stream_name]
    else:
        raise StreamException("Could not find stream {1} at url {2}".format(
            stream_name, url))

    total_downloaded = 0
    with stream.open() as stream_file, open(output_filename, "wb") as output_file:
        if output_progress:
            progress_bar = _download_progress_bar()

        chunk = stream_file.read(buffer_size)

        while chunk:
            total_downloaded += len(chunk)

            if output_progress:
                progress_bar.update(total_downloaded)

            output_file.write(chunk)
            chunk = stream_file.read(buffer_size)

# try and set token as soon as the module is loaded so that the user
# knows to configure it if necessary. NOTE: this should be changed if
# we want to let the user set the token on the command line.
_TWITCH_TOKEN = _get_oauth_token()
