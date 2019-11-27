"""stream_data.py

Contains a wrapper class which contains data describing details of a
stream for streamlink to download.

Twitch and YouTube (and conceivably other streaming services) use
different json schemas to describe stream metadata. The point of this
class is to expose stream metadata in a unified way, providing a
single interface for the downloader.

Derived classes should override the load_data method and convert the
data dict into the fields which are set in the __init__ method here.

It might also be necessary to override the download method to
configure the appropriate streamlink plugin used to download the video
(e.g. to set up Twitch authentication if downloading a Twitch stream)

"""

import progressbar

StreamException = Exception

class StreamData:
    def __init__(self, data):
        #these should all be in human-readable format
        self.title = ""
        self.creation_date = ""
        self.length = ""
        self.url = ""
        self.stream = ""

        self.load_data(data)

    def load_data(self, data):
        self.json_data = data

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key):
        setattr(self, key)

    def download(self, output_filename):
        pass
