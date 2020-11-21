## WARNING: THIS PROJECT IS NO LONGER MAINTAINED.

This tool hasn't been tested since November 2019, which means it probably
doesn't work anymore. If you want to try using it, you'll need to get your own
YouTube API key and configure the program to use it. I'm not bothering to
document how to do that since it's unlikely anyone has any need for it
(especially not me, since I don't listen to Critical Role any more). Email me
if you have questions.

Overview
=======================

cr_download checks the Critical Role YouTube channel for recent episodes, and
prompts the user to download each one. The audio is downloaded using the
[youtube_dl](https://youtube-dl.org/) API.

Optionally, cr_download can use the
[Chromaprint](https://acoustid.org/chromaprint) music fingerprinting algorithm
to attempt to detect the soundtracks Critical Role plays before/after the
show, in the opening credits, and during the break. If a good enough set of
transition points is found in the episode audio, cr_download will recut the
audio to leave out pre/post-show segments, intermission, and (optionally) the
announcement section of the episode.

In addition, the cr_download can dump episode metadata into an RSS feed file,
which I (previously) used to host an alternative version of the Critical Role
podcast (virtually identical to the regular podcast, except uploading a week
early).

Setup
==========================

1. Install [ffmpeg](https://www.ffmpeg.org/) if you haven't already.

2.  If installing via pip (recommended, if I've actually uploaded the
    package to PyPI by the time you read this), run `pip install
    cr-download`.

    Otherwise, download and extract the repository, and run `python
    setup.py install` from the directory you extracted it to.

3. (DEPRECATED. Configure a YouTube API key instead.) Run `streamlink --twitch-oauth-authenticate` to authorize
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
