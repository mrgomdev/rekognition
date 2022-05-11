from typing import Optional, TypedDict, List, Type

import os
import posixpath
from icecream import ic

import requests
import requests.adapters

from flask import request, render_template
from flask import Flask

import rekognition.utils_alert
import rekognition


app = Flask(__name__)


class Response(TypedDict):
    error_code: int
    body: dict


@rekognition.utils_alert.alert_slack_when_exception
def respond(_: Optional[str], error_code: int, **kwargs) -> Response:
    assert 'error_code' not in kwargs
    return dict(error_code=error_code, body=kwargs)


CURRENT_USAGE = 0
MAX_USAGE = int(os.environ.get('MAX_USAGE', 50))


class TooHotError(OSError):
    pass


@app.route('/resetgomdev')
def resetgomdev():
    global CURRENT_USAGE
    CURRENT_USAGE = 0

    return respond('', error_code=0, message=f"Reset done. CURRENT_USAGE={CURRENT_USAGE}, MAX_USAGE={MAX_USAGE}")


class SearchedEach(TypedDict):
    matches: List[rekognition.utils_boto3.FaceMatch]
    searched_face_bounding_box: rekognition.utils_boto3.BoundingBox
class UploadPostPayload(TypedDict):
    searcheds: List[SearchedEach]
@app.route('/upload', methods=['POST'])
def upload_post():
    global CURRENT_USAGE
    CURRENT_USAGE += 1
    if CURRENT_USAGE > MAX_USAGE:
        raise TooHotError()
    ic(CURRENT_USAGE)
    try:
        file = request.files['file']
        image_bytes = rekognition.utils.convert_image_bytes_popular(file.read())
        result: List[rekognition.search_face.ParsedSearchFaceResponse] = rekognition.search_face.search_multiple_faces_by_image(image_bytes=image_bytes)
    except rekognition.search_face.NoFaceInSearchingError:
        return respond('upload.html', error_code=-1, message=f"Face detected, but cannot identify him/her.")
    except rekognition.utils_boto3.RequestError:
        raise
    except Exception:
        raise

    assert result is not None
    message = f"Found {len(result)} faces."
    searcheds = []
    for idx, each in enumerate(result):
        message += f"{idx}th: Looks like {each['MostFaceMatch']['Face']['ExternalImageId']}. {each['MostFaceMatch']['Similarity']:3.0f}% similar."
        assert hasattr(each['MostFaceMatch'], 'keys') and hasattr(each['MostFaceMatch'], 'values'), "Result is expected as dict-like."
        searcheds.append(SearchedEach(matches=[each['MostFaceMatch']], searched_face_bounding_box=each['SearchedFaceBoundingBox']))
    response_payload = UploadPostPayload(searcheds=searcheds)
    error_code = 0
    return respond('upload.html', error_code=error_code, message=message, **response_payload)


UnicodeEncodedStr = Type[str]
class IdolMeta(TypedDict, total=False):
    idol_id: str
    idol_display_name: UnicodeEncodedStr
    namu_url: str
    tags: str
    has_instagram_individual: int
    instagram_url: str
    weibo_url: str
def build_markdown_from_idol_meta(idol_meta: IdolMeta) -> str:
    markdown_str = f"## {idol_meta['idol_display_name']}\n- [namu {idol_meta['idol_display_name']}]({idol_meta['namu_url']})\n- tags: {idol_meta['tags']}"
    if 'instagram_url' in idol_meta:
        markdown_str += f"\n- [Instagram 🏠]({idol_meta['instagram_url']})"
    return markdown_str
class DetailPayload(TypedDict):
    markdown: str
_detail_session = requests.session()
_detail_session.mount(rekognition.config.firebase_realtime_db_idols_meta_prefix, rekognition.utils.build_retry_http_adapter())
@app.route('/detail/<idol_id>')
def detail(idol_id: str):
    global _detail_session

    response = _detail_session.get(url=posixpath.join(rekognition.config.firebase_realtime_db_idols_meta_prefix, f'{idol_id}.json'))

    assert response.text != 'null'

    idol_meta = IdolMeta(idol_id=idol_id, **response.json())
    return respond('', error_code=0, markdown=build_markdown_from_idol_meta(idol_meta=idol_meta))


@app.route('/hello')
def hello():
    return respond('', error_code=0, message='Hello World')


@app.errorhandler(500)
def server_error(e):
    assert 'werkzeug.exceptions.InternalServerError' in str(type(e))
    original_exception = e.original_exception
    try:
        return respond('', error_code=-1, exception=f'{type(original_exception)}: {str(original_exception)}'), 500
    finally:
        rekognition.utils_alert.alert_slack_exception(error_code=-1, exception=original_exception)
