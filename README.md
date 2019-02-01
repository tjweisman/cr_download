Overview
=======================

cr_download checks recent Geek and Sundry Twitch VODs for videos with
titles looking like Critical Role episode titles, and prompts the user
to download each one. The file is downloaded as video using the
"streamlink" program, and converted to audio using ffmpeg.

Optionally, cr_download can use the Chromaprint music fingerprinting
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

2. If installing via pip (recommended, if I've actually uploaded the
package to PyPI by the time you read this), run `pip install
cr-download`.

 Otherwise, download and extract the repository, and run `python
 setup.py install` from the directory you extracted it to.

3. Run `streamlink --twitch-oauth-authenticate` and copy the contents
of the displayed page into the file
`~/.config/cr_download/.streamlinkconfig` (you will need to create
this file).

Usage
==================================

Run `critrole_download` (it should be added to your path after
installation) to display a list of recent Geek & Sundry VODs. You may
choose one (or more) to download and convert to audio.

You can also run `autocut_vod FILENAME [FILENAME ...]` to run the
autocutting tool on a local video file.

For more usage help, run `critrole_download -h` or `autocut_vod -h`