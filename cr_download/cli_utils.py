import re

from cr_download.autocutter_utils import valid_pattern


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
    elif not multiple_parts:
        suggestion = "tmp_part*.mp3"
    else:
        suggestion = "tmp.mp3"

    return suggestion

def confirm(prompt):
    """Provide a Y/N prompt for the user, and continue prompting until Y/N
    is input.

    """
    response = "X"
    while response.strip().upper() not in ["Y", "N", ""]:
        response = input(prompt + " [Y]/N ")
        if response.strip().upper() in ["Y", ""]:
            return True
    return False


def prompt_title(vod, multiple_parts=False):
    """Ask the user to provide a title (or title pattern) for a vod.

    title_format should contain exactly one '*' (later substituted for).
    """
    ep_title = suggest_filename(vod["title"], multiple_parts)
    if multiple_parts:
        prompt_str = (
            "Enter titles to save vod segments under (default: {})".format(
                ep_title))
    else:
        prompt_str = (
            "Enter title to save vod under (default: {}): ".format(
                ep_title))

    invalid_title = True
    while invalid_title:
        title = input(prompt_str)
        if not title.strip():
            title = ep_title
        invalid_title = multiple_parts and not valid_pattern(title)
        if invalid_title:
            print("Enter a title pattern containing exactly one '*'.")


    return title
