import re
import os


_CONFIRM_YN_OPTION = {"Y":True, "N":False}
_CONFIRM_YN_ORDER = "YN"
_DEFAULT_CONFIRM_OPTION = "Y"

def _singleline_fmt(long_string):
    return re.sub(r"\s+", " ", long_string)

def suggest_filename(title, multiple_parts=False):
    """suggest a filename to save a Critical Role episode under, given the
    title of its VOD.

    If MULTIPLE_PARTS is specified, suggest a globbed format for
    the filenames for multiple parts of the episode.

    """
    match = re.match(r".*Critical Role:? (Campaign (\d+):?)?,? Ep(isode)? ?(\d+).*",
                     title, flags=re.I)
    wildcard = ""
    if multiple_parts:
        wildcard = "_part*"
    if match:
        campaign = "1"
        if match.group(2):
            campaign = match.group(2)
        episode = int(match.group(4))
        suggestion = "c{0}ep{1:03d}{2}.mp3".format(campaign, episode, wildcard)
    else:
        suggestion = "tmp{}.mp3".format(wildcard)

    return suggestion

def confirm(prompt, options=None,
            default=_DEFAULT_CONFIRM_OPTION,
            option_order=_CONFIRM_YN_ORDER):
    """Provide a Y/N prompt for the user, and continue prompting until Y/N
    is input.

    """

    if not options:
        options = {key:val for key, val in _CONFIRM_YN_OPTION.items()}
    default = default.upper()
    option_order = option_order.upper()

    if default not in options:
        raise Exception("invalid confirm default specified.")

    confirm_text = " (" + ("/".join(option_order)).replace(
        default, "[{}]".format(default)
    ) + ") "

    prompt_text = _singleline_fmt(prompt) + confirm_text

    options[""] = options[default]

    response = input(prompt_text)
    while response.strip().upper() not in options:
        response = input(prompt_text)

    return options[response.strip().upper()]

def _multipart_title(title):
    prefix, ext = os.path.splitext(title)
    return prefix + "_*" + ext

def prompt_title(vod_title="", multiple_parts=False):
    """Ask the user to provide a title (or title pattern) for a vod.

    if multiple_parts is True, vod_title should contain at least
    one '*' (later substituted for).

    """
    ep_title = suggest_filename(vod_title, multiple_parts)
    if multiple_parts:
        prompt_str = (
            """Enter titles to save episode segments under
            (default: {}): """.format(ep_title))
    else:
        prompt_str = (
            "Enter title to save episode under (default: {}): ".format(
                ep_title))

    accepted_title = False
    while not accepted_title:
        title = input(_singleline_fmt(prompt_str))

        if not title.strip():
            title = ep_title
            accepted_title = True
        elif multiple_parts and "*" not in title:
            title = _multipart_title(title)
            accepted_title = confirm("""Since autocutter is specified,
            episodes will be saved in the format {}.
            Is this ok?""".format(title))
        else:
            accepted_title = True

    return title

def autocutter_argparser():
    """get an argument parser containing a subgroup with autocutter config
    args"""

    parser = ArgumentParser(add_help=False)

    autocut_args = parser.add_argument_group("autocutter")

    autocut_args.add_argument("--ignore-errors", action="store_true",
                              help="""On autocut errors, just merge output into a
                              single audio file""")

    autocut_args.add_argument("--cutting-sequence", default="default",
                              help="""which cutting sequence to use when autocutting
                              files (default behavior specified in config file)""")

    autocut_args.add_argument("-k", "--keep-intro", action="store_const",
                              dest="cutting_sequence", const="keep",
                              help="""when autocutting, keep the pre-show
                              announcements/intro section""")

    autocut_args.add_argument("--cut-intro", action="store_const",
                              dest="cutting_sequence", const="cut",
                              help="""when autocutting, cut the pre-show
                              announcements/intro section""")

    autocut_args.add_argument("-M", "--autocut-merge", action="store_true",
                              help="""when autocutting, merge the cut segments into
                              a single file instead of cutting along breaks""")

    return parser

def video_argparser():
    """get an argument parser containing video options"""

    parser = ArgumentParser(add_help=False)
    parser.add_argument("--ffmpeg-path", default="ffmpeg",
                        help="""Path to ffmpeg""")
    return parser

def downloader_argparser():
    vid_parser = video_argparser()
    autocut_parser = autocutter_argparser()
    parser = ArgumentParser(parents=[vid_parser, autocut_parser],
                            description="Download .mp3 files for Critical "
                            "Role episodes from Twitch")
    return parser
