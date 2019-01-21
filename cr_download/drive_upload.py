"""drive_upload.py

Module responsible for uploading a single file to a folder named
"xfer" in the user's Google Drive root directory.

This is super brittle and does basically no error checking.

"""

from __future__ import print_function

import os
import httplib2

from apiclient import discovery, errors
from apiclient.http import MediaFileUpload
from oauth2client.file import Storage
from progressbar import ProgressBar

from . import cr_settings

XFER_FOLDER_NAME = "xfer"
CREDENTIALS_FILE = os.path.join(cr_settings.CONFIG_DIR, "drive_credentials.json")

def _get_service():
    """get Google Drive API service object (assume credentials are stored
    locally)

    """
    store = Storage(CREDENTIALS_FILE)
    credentials = store.get()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v2', http=http)
    return service

def _get_xfer_id(service):
    """get id of XFER_FOLDER_NAME folder in user's Google Drive root
    directory

    """
    try:
        children = service.children().list(
            folderId="root",
            q='title="{}"'.format(XFER_FOLDER_NAME)).execute()

        all_children = children.get('items', [])
        if len(all_children) == 1:
            return all_children[0]['id']
        return None
    except errors.HttpError as error:
        print("Error: {}".format(error))

def _upload_file(service, filename, parent_id):
    """use service to upload file filename to Drive folder with id
    parent_id

    """
    media_body = MediaFileUpload(filename, resumable=True)
    body = {
        'title':os.path.basename(filename),
        'parents':[{'id':parent_id}]
    }
    request = service.files().insert(body=body, media_body=media_body)
    response = None
    with ProgressBar(max_value=100) as progress_bar:
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress_bar.update(int(status.progress() * 100))

def single_xfer_upload(filename):
    """upload a local file to the XFER_FOLDER_NAME folder in the user's
    Google Drive.

    """
    service = _get_service()
    xfer_id = _get_xfer_id(service)
    _upload_file(service, filename, xfer_id)
