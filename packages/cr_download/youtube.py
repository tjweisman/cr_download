"""youtube.py

This module uses the YouTube Data API to find recent uploads to the
Critical Role YouTube channel which are likely to be new Critical Role
episodes.

"""

from __future__ import print_function

import re

import requests
import streamlink

from cr_download.configuration import data as config

YOUTUBE_API_KEY = "AIzaSyBBKd5es2ZjnxYrlZlqZSoTPCGmt6E7sJU"

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/"

CHANNEL_QUERY = "channels"
PLAYLIST_QUERY = "playlistItems"

#actual value is 50, set to 5 for testing
MAX_RESULTS_PER_PAGE = 5

CRITROLE_YOUTUBE_ID = "UCpXBGqwsBkpvcYjsJBQ7LEQ"

def get_playlist_videos(playlist_id, limit=10):
    params = {"part":"contentDetails,snippet",
              "playlistId":playlist_id,
              "key":YOUTUBE_API_KEY
              }

    videos = []

    while len(videos) < limit:
        max_results = min(limit - len(videos), MAX_RESULTS_PER_PAGE)
        params["maxResults"] = max_results

        response = requests.get(YOUTUBE_API_URL + PLAYLIST_QUERY,
                                params=params)
        response.raise_for_status()

        [{"id":video["contentDetails"]["videoId"],
          "title":video["snippet"]["title"],
          }
         for video in response.json()["items"]]




    return response

def get_recent_channel_uploads(limit=10):
    params={"part":"contentDetails",
            "id":CRITROLE_YOUTUBE_ID,
            "key":YOUTUBE_API_KEY}

    response = requests.get(YOUTUBE_API_URL + CHANNEL_QUERY, params=params)
    response.raise_for_status()

    videos = []
    #channel ids are supposed to be unique, but we'll loop anyway
    #because we're paranoid
    for item in response.json()["items"]:
        playlist_id = item["contentDetails"]["relatedPlaylists"]["uploads"]
        return get_playlist_videos(playlist_id)
