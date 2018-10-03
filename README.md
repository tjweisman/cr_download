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
episode to Google drive (mostly because my USB ports suck and I can't
reliably transfer the audio to my phone over a wired connection, and
Google Drive/WiFi is faster than Bluetooth).

For usage help, run `cr_download -h`.

Dependencies:
==========================

- streamlink[https://streamlink.github.io/]

- ffmpeg[https://www.ffmpeg.org/]

- requests[http://docs.python-requests.org/en/master/]

- tqdm[https://pypi.org/project/tqdm/]

- acoustid[https://acoustid.org/chromaprint] and its
  python bindings[https://pypi.org/project/pyacoustid/] (optional)
  
- Google API python client
  [https://developers.google.com/api-client-library/python/] (optional)