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

    ep_data = {}

    campaign_regex = "(?:Campaign (?P<campaign>\d+))?"
    episode_regex = "Ep(?:isode)? ?(?P<episode>\d+)"

    cr_regex = re.compile("(?P<title>[^|]*)[ |,:]*Critical Role[ |,:]*" +
                          campaign_regex + "[ |,:]*" + episode_regex,
                          flags=re.I)

    match = cr_regex.match(title)

    if match:
        ep_data["campaign"] = match.group("campaign")
        ep_data["episode"] = int(match.group("episode"))
        ep_data["title"] = match.group("title").strip()

    return ep_data


def format_critrole_title(ep_data, short=True):
    """format a critical role episode title into either a short or long
    format

    """
    campaign_str = ""
    ep_str = ""
    if "campaign" in ep_data:
        if short:
            campaign_str += "c{0}".format(ep_data["campaign"])
        else:
            campaign_str += "Campaign {}".format(ep_data["campaign"])
    if "episode" in ep_data:
        if short:
            ep_str = "ep{:03d}".format(ep_data["episode"])
        else:
            ep_str = "Episode {}".format(ep_data["episode"])

    if short:
        return campaign_str + ep_str

    ep_title = " ".join([campaign_str, ep_str])
    if "title" in ep_data:
        ep_title += ": " + ep_data["title"]

    return ep_title


def write_metadata_file(output_file, audio_files, streams):
    """write a YAML file to output_file with an entry for each audio file
    provided.

    audio_files: dict of arrays of files downloaded (indexed by
    filename, possibly with wildcard)

    streams: dict of arrays of stream_data dicts, also indexed by
    filename (with wildcard if present)

    """
    episodes = {}
    for title, files in audio_files.items():
        part = 1
        for audio_file in files:
            stream  = streams[title][0]
            episode_name_data = parse_critrole_title(stream["title"])
            ep_title = format_critrole_title(episode_name_data, short=False)
            ep_id = format_critrole_title(episode_name_data)
            if len(files) > 1:
                ep_title += " part {}".format(part)
                ep_id += "p{:02d}".format(part)

            ep = {}
            ep["title"] = ep_title
            ep["id"] = ep_id
            ep["airdate"] = stream["creation_date"]
            ep["file"] = os.path.abspath(audio_file)

            if hasattr(stream, "description"):
                ep["description"] = stream.description

            episodes[ep_id] = ep

            part += 1

    yaml.dump(episodes, Path(output_file))
