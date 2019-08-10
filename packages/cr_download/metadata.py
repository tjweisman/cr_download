"""metadata.py: produce YAML files containing metadata about
downloaded CR episodes """

from __future__ import print_function
from __future__ import unicode_literals
from builtins import input

import re
import os
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML(typ="safe")

def parse_critrole_title(title):
    """parse a critical role episode title to extract campaign and episode #"""

    match = re.match(r".*Critical Role:? (Campaign (\d+):?)?,? Ep(isode)? ?(\d+).*",
                     title, flags=re.I)

    campaign, episode = None, None

    if match:
        campaign = "1"
        if match.group(2):
            campaign = match.group(2)
        episode = int(match.group(4))

    return (campaign, episode)


def format_critrole_title(campaign, episode, short=True):
    """format a critical role episode title into either a short or long
    format

    """
    campaign_str = ""
    ep_str = ""
    if campaign:
        if short:
            campaign_str = "c{0}".format(campaign)
        else:
            campaign_str = "Campaign {}".format(campaign)
    if episode:
        if short:
            ep_str = "ep{:03d}".format(episode)
        else:
            ep_str = "Episode {}".format(episode)

    if short:
        return campaign_str + ep_str

    return " ".join([campaign_str, ep_str])


def write_metadata_file(output_file, audio_files, vods):
    """write a YAML file to output_file with an entry for each audio file
    provided.

    audio_files: dict of arrays of files downloaded (indexed by
    filename, possibly with wildcard)

    vods: dict of arrays of twitch vod dicts, also indexed by filename
    (with wildcard if present)

    """
    episodes = {}
    for title, files in audio_files.items():
        part = 1
        for audio_file in files:
            vod  = vods[title][0]
            campaign, episode = parse_critrole_title(vod["title"])
            ep_title = format_critrole_title(campaign, episode, short=False)
            ep_id = format_critrole_title(campaign, episode)
            if len(files) > 1:
                ep_title += " part {}".format(part)
                ep_id += "p{:02d}".format(part)

            ep = {}
            ep["title"] = ep_title
            ep["id"] = ep_id
            ep["airdate"] = vod["recorded_at"]
            ep["file"] = os.path.abspath(audio_file)

            episodes[ep_id] = ep

            part += 1

    yaml.dump(episodes, Path(output_file))
