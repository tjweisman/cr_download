"""youtube.py

This module uses the YouTube Data API to find recent uploads to the
Critical Role YouTube channel which are likely to be new Critical Role
episodes.

"""

from __future__ import print_function

from datetime import timedelta
import re

import requests
import streamlink

from cr_download.configuration import data as config
from cr_download import stream_data

YOUTUBE_API_KEY = "AIzaSyBBKd5es2ZjnxYrlZlqZSoTPCGmt6E7sJU"

ISO_REGEX = re.compile(r"PT((?P<h>\d*)H)?((?P<m>\d*)M)?((?P<s>\d*)S)?")

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/"

VIDEO_QUERY = "videos"
CHANNEL_QUERY = "channels"
PLAYLIST_QUERY = "playlistItems"

YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v="

MAX_RESULTS_PER_PAGE = 50

CRITROLE_YOUTUBE_ID = "UCpXBGqwsBkpvcYjsJBQ7LEQ"

DEFAULT_STREAM_QUALITY = "audio_mp4"


def _parse_iso_duration(duration):
    match = ISO_REGEX.match(duration)
    if match:
        hrs = match.group('h') or "0"
        mins = match.group('m') or "0"
        secs = match.group('s') or "0"
        return timedelta(hours=int(hrs), minutes=int(mins), seconds=int(secs))

class YoutubeStreamData(stream_data.StreamData):
    def load_data(self, data):
        self.json_data = data
        self.title = data["snippet"]["title"]

        #convert these please
        self.creation_date = data["snippet"]["publishedAt"]
        self.length = str(_parse_iso_duration(
            data["contentDetails"]["duration"]))

        self.url = YOUTUBE_VIDEO_URL + data["id"]
        self.stream = DEFAULT_STREAM_QUALITY

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


def get_playlist_video_ids(playlist_id, limit=10):
    params = {"part":"contentDetails",
              "playlistId":playlist_id,
              "key":YOUTUBE_API_KEY
    }

    video_ids = []

    while len(video_ids) < limit:
        max_results = min(limit - len(video_ids), MAX_RESULTS_PER_PAGE)
        params["maxResults"] = max_results

        response = requests.get(YOUTUBE_API_URL + PLAYLIST_QUERY,
                                params=params)
        response.raise_for_status()

        video_ids += [video["contentDetails"]["videoId"]
                      for video in response.json()["items"]]

    return video_ids

def get_recent_channel_uploads(limit=10):
    params={"part":"contentDetails",
            "id":CRITROLE_YOUTUBE_ID,
            "key":YOUTUBE_API_KEY}

    response = requests.get(YOUTUBE_API_URL + CHANNEL_QUERY, params=params)
    response.raise_for_status()

    videos = []
    #channel ids are supposed to be unique, but we'll loop anyway
    for item in response.json()["items"]:
        playlist_id = item["contentDetails"]["relatedPlaylists"]["uploads"]
        video_ids = get_playlist_video_ids(playlist_id, limit=limit)
        return get_video_data(video_ids)
