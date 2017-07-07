"""twitch_download.py

This module uses the twitch API to retrieve information about the Geek
and Sundry channel, present the user with videos that are likely to be
Critical Role uploads, and download a Critical Role VOD.

Once again this code is super brittle.

"""

import requests, json, re, subprocess, shlex

CLIENT_ID="ignduriqallck9hugiw15zfaqdvgwc"
GANDS_ID="36619809"

headers = {"Client-ID" : CLIENT_ID,
           "Accept"    : "application/vnd.twitchtv.v5+json"}

def critrole_video(video):
    #true if the video object title looks like a Critical Role episode title
    return re.match(".*Critical Role Ep(isode)? ?.*", video["title"],
                    flags=re.I)

def guess_ep_num(video_title):
    #guess the episode number from the title via regex
    m = re.match(".*Critical Role Ep(isode)? ?(\d+).*",
                 video_title, flags=re.I)
    if m:
        return m.groups()[1]
    return "??"

def get_gands_id():
    #currently not needed, since the G&S ID has already been retrieved
    #and hard-coded into the application
    params = {"login":"geekandsundry"}
    r = requests.get("https://api.twitch.tv/kraken/users",
                     headers=headers, params=params)
    return r.json()["users"][0]["_id"]

def get_vod_list():
    #get JSON array of past broadcast VODs on the G&S channel, most
    #recent first
    params = {"broadcast_type":"archive"}
    url = "https://api.twitch.tv/kraken/channels/{}/videos".format(GANDS_ID)
    r = requests.get(url, headers=headers,params=params)
    return r.json()["videos"]

def get_titles(video_list):
    return [video["title"] for video in video_list]

def scan_vods(video_json):
    #iterate through a JSON array of VODs, prompting the user to
    #download each one if its title looks like it's a CR episode.

    #return an array of filenames of episodes converted to mp3
    cr_videos = [video for video in video_json if critrole_video(video)]
    num = len(cr_videos)
    files = []
    print "{} video{} found.".format(num, ("" if num == 1 else "s"))
    for video in cr_videos:
        conf_str = ("Download possible CR episode with title:\n\"{}\"\n"
                    "as \"ep{}.mp3\"? [Y]/N\n")

        confirm = "X"
        while confirm.strip().upper() not in ["Y", "N", ""]:
            confirm = raw_input(conf_str.format(video["title"],
                                                guess_ep_num(video["title"])))
        if confirm.strip().upper() in ["Y", ""]:
            mp3 = dload_ep_audio(video, guess_ep_num(video["title"]))
            files.append(mp3)
    return files

def dload_ep_audio(video, ep_num):
    #use streamlink app to download VOD as "tmp.mp4," and convert it
    #to an mp3 file with the appropriate episode number

    #return filename of converted file
    video_url = "twitch.tv/videos/" + video["_id"][1:]
    cmd = "streamlink --config .streamlinkconfig {} 360p30 -o tmp.mp4".format(
        video_url)
    subprocess.call(shlex.split(cmd))
    mp3_file = "ep{}.mp3".format(ep_num)
    subprocess.call(["ffmpeg", "-i", "tmp.mp4", mp3_file])
    return mp3_file
