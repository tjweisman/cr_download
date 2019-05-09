Overview
=======================

cr_download checks recent Critical Role Twitch VODs for videos with
titles looking like Critical Role episode titles, and prompts the user
to download each one. The file is downloaded as video using the
[streamlink](https://streamlink.github.io/) API, and converted to
audio using [ffmpeg](https://www.ffmpeg.org/).

Optionally, cr_download can use the
[Chromaprint](https://acoustid.org/chromaprint) music fingerprinting
algorithm to attempt to detect the soundtracks Critical Role plays
before/after the show, in the opening credits, and during the
break. If a good enough set of transition points is found in the
episode audio, cr_download will recut the audio to leave out
pre/post-show segments, intermission, and (optionally) the
announcement section of the episode.

In addition, cr_download can also upload the audio files for the
episode to a fixed Google drive folder.

Setup
==========================

1. Install [ffmpeg](https://www.ffmpeg.org/) if you haven't already.

2.  If installing via pip (recommended, if I've actually uploaded the
    package to PyPI by the time you read this), run `pip install
    cr-download`.

    Otherwise, download and extract the repository, and run `python
    setup.py install` from the directory you extracted it to.

3. Run `streamlink --twitch-oauth-authenticate` to authorize
streamlink to access your Twitch account. Copy the provided oauth
token into your config file, located at
`~/.config/cr_download/config.yaml` (it will be automatically created
the first time you run the program).

Usage
==================================

Run `critrole_download` (it should be added to your path after
installation) to display a list of recent Critical Role VODs. You may
choose one (or more) to download and convert to audio.

To run the automatic audio editor on the downloaded files, run
`critrole_download -a`.

You can also run `autocut_vod FILENAME [FILENAME ...]` to run the
autocutting tool on a local audio/video file.

To see a full list of options for each command, run `critrole_download
-h` or `autocut_vod -h`. You can also change the behavior of the
program by editing options in the configuration file located at
`~/.config/cr_download/config.yaml`.
