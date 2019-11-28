"""youtube.py

This module uses the YouTube Data API to find recent uploads to the
Critical Role YouTube channel which are likely to be new Critical Role
episodes.

"""

from __future__ import print_function

from datetime import timedelta
import re

import requests
import youtube_dl

from cr_download.configuration import data as config
from cr_download import stream_data

YOUTUBE_API_KEY = "AIzaSyBBKd5es2ZjnxYrlZlqZSoTPCGmt6E7sJU"

ISO_REGEX = re.compile(r"PT((?P<h>\d*)H)?((?P<m>\d*)M)?((?P<s>\d*)S)?")

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/"

VIDEO_QUERY = "videos"
CHANNEL_QUERY = "channels"
PLAYLIST_ITEM_QUERY = "playlistItems"
PLAYLIST_QUERY = "playlists"

YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v="

MAX_RESULTS_PER_PAGE = 50

CRITROLE_YOUTUBE_ID = "UCpXBGqwsBkpvcYjsJBQ7LEQ"
CRITROLE_CAMPAIGN_PLAYLIST = "Campaign 2: The Mighty Nein"

DEFAULT_STREAM_QUALITY = "bestaudio/worst"

def _parse_iso_duration(duration):
    match = ISO_REGEX.match(duration)
    if match:
        hrs = match.group('h') or "0"
        mins = match.group('m') or "0"
        secs = match.group('s') or "0"
        return timedelta(hours=int(hrs), minutes=int(mins), seconds=int(secs))

class YoutubeStreamData(stream_data.StreamData):
    def __init__(self, *args, **kwargs):
        super(YoutubeStreamData, self).__init__(*args, **kwargs)
        output_filename = ""

    #it's actually absurd that the youtube_dl API doesn't have an
    #obvious way to access the final filename except through a
    #progress hook, even though the download method blocks. something
    #is stupid here.

    #I hope this isn't threaded or else this is even more dumb.
    def download_hook(self, d):
        if d['status'] == 'finished' or d['status'] == 'downloading':
            self.output_filename = d['filename']

    def load_data(self, data):
        self.json_data = data
        self.title = data["snippet"]["title"]

        #convert these please
        self.creation_date = data["snippet"]["publishedAt"]
        self.length = str(_parse_iso_duration(
            data["contentDetails"]["duration"]))

        self.url = YOUTUBE_VIDEO_URL + data["id"]
        self.stream = DEFAULT_STREAM_QUALITY

    def download(self, output):
        ydl_options = {"format":DEFAULT_STREAM_QUALITY,
                       "outtmpl":"{}.%(ext)s".format(output),
                       "progress_hooks":[lambda d: self.download_hook(d)]
        }

        with youtube_dl.YoutubeDL(ydl_options) as ydl:
            ydl.download([self.url])

        return self.output_filename


def get_video_data(ids):
    params = {"part":"contentDetails,snippet",
              "id":",".join(ids),
              "key":YOUTUBE_API_KEY
    }

    response = requests.get(YOUTUBE_API_URL + VIDEO_QUERY,
                            params=params)
    response.raise_for_status()

    return [YoutubeStreamData(video)
            for video in response.json()["items"]]

def get_playlist_video_ids(playlist_id, limit=10, reverse=True):
    """get video ids for items in the given playlist.

    if limit is negative, get everything in the list.

    """
    params = {"part":"contentDetails",
              "playlistId":playlist_id,
              "key":YOUTUBE_API_KEY
    }

    video_ids = []

    initial_query = True

    if reverse:
        return get_playlist_video_ids(
            playlist_id, limit=-1, reverse=False
        )[-1 * limit:]

    while (initial_query or
           ("nextPageToken" in response.json() and
            (len(video_ids) < limit or limit < 0))):

        if not initial_query:
            params["pageToken"] = response.json()["nextPageToken"]

        initial_query = False

        if limit > 0:
            max_results = min(limit - len(video_ids), MAX_RESULTS_PER_PAGE)
        else:
            max_results = MAX_RESULTS_PER_PAGE

        params["maxResults"] = max_results

        response = requests.get(YOUTUBE_API_URL + PLAYLIST_ITEM_QUERY,
                                params=params)
        response.raise_for_status()

        video_ids += [video["contentDetails"]["videoId"]
                      for video in response.json()["items"]]

    return video_ids

def get_critrole_main_playlist_id():
    """find the playlist id for the main Critical Role campaign playlist"""
    params = {"part":"snippet",
              "channelId":CRITROLE_YOUTUBE_ID,
              "key":YOUTUBE_API_KEY}

    initial_query = True
    while initial_query or "nextPageToken" in response.json():
        initial_query = False
        response = requests.get(YOUTUBE_API_URL + PLAYLIST_QUERY, params=params)
        response.raise_for_status()

        for playlist in response.json()["items"]:
            if re.match(CRITROLE_CAMPAIGN_PLAYLIST,
                        playlist["snippet"]["title"]):
                return playlist["id"]

        params["pageToken"] = response.json()["nextPageToken"]

def get_critrole_upload_playlist_id():
    """find the playlist id for the playlist of all uploads to the
    Critical Role channel.

    """


    params={"part":"contentDetails",
            "id":CRITROLE_YOUTUBE_ID,
            "key":YOUTUBE_API_KEY}

    response = requests.get(YOUTUBE_API_URL + CHANNEL_QUERY, params=params)
    response.raise_for_status()

    for item in response.json()["items"]:
        return item["contentDetails"]["relatedPlaylists"]["uploads"]

def get_recent_critrole_videos(limit=10):
    """retrieve an array of json objects representing recent uploads to the
    Critical Role Mighty Nein playlist.

    If for some reason the Mighty Nein playlist isn't available, get
    an array of json objects representing recent uploads to the
    Critical Role channel.
    """

    cr_playlist_id = get_critrole_main_playlist_id()

    if cr_playlist_id:
        video_ids = get_playlist_video_ids(cr_playlist_id, limit=limit, reverse=True)
    else:
        cr_playlist_id = get_critrole_upload_playlist_id()
        video_ids = get_playlist_video_ids(cr_playlist_id, limit=limit)

    return get_video_data(video_ids)
