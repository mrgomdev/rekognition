from typing import Optional, TypedDict, List, Type, Collection, Union

import os
from icecream import ic

import requests

from flask_app import app

from flask import request, render_template

import rekognition.utils_alert

import flask_app
if not flask_app.INCLUDE_VIEWS:
    class RenderTemplateResponse(TypedDict):
        error_code: int
        body: dict

    @rekognition.utils_alert.alert_slack_when_exception
    def render_template(_: Optional[str], error_code: int, **kwargs) -> RenderTemplateResponse:
        assert 'error_code' not in kwargs
        return dict(error_code=error_code, body=kwargs)
from rekognition import search_face, utils, utils_boto3, config

CURRENT_USAGE = 0
MAX_USAGE = int(os.environ.get('MAX_USAGE', 50))


class SearchedEach(TypedDict):
    matches: List[utils_boto3.FaceMatch]
    searched_face_bounding_box: utils_boto3.BoundingBox
class UploadPostPayload(TypedDict):
    searcheds: List[SearchedEach]
@app.route('/upload', methods=['POST'])
def upload_post():
    global CURRENT_USAGE
    CURRENT_USAGE += 1
    if CURRENT_USAGE > MAX_USAGE:
        exit(1)
    ic(CURRENT_USAGE)
    try:
        file = request.files['file']
        image_bytes = utils.convert_image_bytes_popular(file.read())
        result: List[search_face.ParsedSearchFaceResponse] = search_face.search_multiple_faces_by_image(image_bytes=image_bytes)
    except search_face.NoFaceInSearchingError:
        return render_template('upload.html', error_code=-1, message=f"Face detected, but cannot identify him/her.")
    except utils_boto3.RequestError:
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
    return render_template('upload.html', error_code=error_code, message=message, **response_payload)


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
@app.route('/detail/<idol_id>')
def detail(idol_id: str):
    with requests.session() as request_session:
        response = request_session.get(url=f'https://modi-11e0c-default-rtdb.firebaseio.com/idols-meta/{idol_id}.json')

        assert response.text != 'null'

        idol_meta = IdolMeta(idol_id=idol_id, **response.json())
    return render_template('', error_code=0, markdown=build_markdown_from_idol_meta(idol_meta=idol_meta))


@app.route('/resetgomdev')
def resetgomdev():
    global CURRENT_USAGE
    CURRENT_USAGE = 0

    return render_template('', error_code=0, message=f"Reset done. CURRENT_USAGE={CURRENT_USAGE}, MAX_USAGE={MAX_USAGE}")
