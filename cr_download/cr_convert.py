from cr_download import media_utils
from cr_download.autocut import autocutter

def videos_to_episode_audio(video_files, title, arguments, tmpdir):
    """convert all of the files in VIDEO_FILES to one or more audio files.

    if arguments.autocut is specified, run the autocutting algorithm
    on each episode before outputting. if, in addition, autocut_merge
    is specified, the different parts of the (autocut) episode are
    merged into a single audio file.

    return the name(s) of the audio file(s) created.

    """

    episodes = []
    for filename in video_files:
        episodes.append(
            media_utils.mp4_to_audio_segments(
                filename, tmpdir,
                segment_fmt=".wav"))

    output_files = []
    for episode_segments in episodes:
        if arguments.autocut:
            try:
                output_files += autocutter.autocut(
                    episode_segments, title,
                    arguments.cutting_sequence,
                    debug=arguments.debug,
                    merge_segments=arguments.autocut_merge)
            except autocutter.AutocutterException:
                if arguments.autocut_ignore_errors:
                    print("Autocutter failed, exporting episode audio uncut as {}"
                          .format(title))
                    output_files.append(
                        media_utils.merge_audio_files(episode_segments, title))
                else:
                    raise
        else:
            output_files.append(media_utils.merge_audio_files(episode_segments, title))

    return output_files
