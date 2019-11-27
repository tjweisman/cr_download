"""stream_data.py

Contains a wrapper class which contains data describing details of a
stream for streamlink to download.

Twitch and YouTube (and conceivably other streaming services) use
different json schemas to describe stream metadata. The point of this
class is to expose stream metadata in a unified way, providing a
single interface for the downloader.

Derived classes should override the load_data method and convert the
data dict into the fields which are set in the __init__ method here.

"""

import streamlink

class StreamData:
    def __init__(self, data):
        self.json_data = data

        #these should all be in human-readable format
        self.title = ""
        self.creation_date = ""
        self.length = ""
        self.url = ""
        self.stream = ""

        load_data(self, data)

    def load_data(self, data):
        pass

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key):
        setattr(self, key)

    def download(self, output_filename, buffer_size=8192,
                 session=None, output_progress=True):
        """download a video object to the given output file.
        """
        if not streamlink_session:
            session = streamlink.Streamlink()

        streams = session.streams(video["url"])

        if streams and self.stream in streams:
            stream = streams[self.stream]
        else:
            raise TwitchException("Could not find stream {1} at url {2}".format(
                self.stream, video["url"]))

        total_downloaded = 0
        with stream.open() as stream_file, open(filename, "wb") as output_file:
            if output_progress:
                progress_bar = _download_progress_bar()

            chunk = stream_file.read(buffer_size)

            while chunk:
                total_downloaded += len(chunk)

                if output_progress:
                    progress_bar.update(total_downloaded)

                output_file.write(chunk)
                chunk = stream_file.read(buffer_size)
