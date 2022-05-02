import io
from typing import Optional, TypedDict, List, Union, Tuple

from PIL import Image
from icecream import ic
# ic = print

import boto3

try:
    from . import utils
    from . import utils_alert
    from . import utils_boto3

    from . import config
except ImportError:
    import utils
    import utils_alert
    import utils_boto3

    import config


class NoFaceInSearchingError(utils_boto3.RequestError):
    def __init__(self, boto_exception: utils_boto3.ClientError):
        super(NoFaceInSearchingError, self).__init__(message=f'No Faces are found in the search. Each face must not be smaller than 40x40 in 1920x1080.', boto_exception=boto_exception)


class ImageTooLargeError(utils_boto3.RequestError):
    def __init__(self, boto_exception: utils_boto3.ClientError):
        super(ImageTooLargeError, self).__init__(message=f'Image is too large. size < 5MB and (height and width) < 4096 pixels.', boto_exception=boto_exception)


class NoMatchedFaceError(LookupError):
    def __init__(self, collection_id: str):
        super(NoMatchedFaceError, self).__init__(f'No matched faces in the collection {collection_id}.')


class SearchFaceResponse(TypedDict):
    SearchedFaceBoundingBox: utils_boto3.BoundingBox
    SearchedFaceConfidence: float
    FaceMatches: List[utils_boto3.FaceMatch]
    ResponseMetadata: dict
class ParsedSearchFaceResponse(TypedDict):
    SearchedFaceBoundingBox: utils_boto3.BoundingBox
    MostFaceMatch: utils_boto3.FaceMatch
@utils_alert.alert_slack_when_exception
@utils_boto3.handle_request_error
def _search_face_by_image(image_bytes: bytes, collection_id: str, max_matches: int = 10, threshold: int = 90) -> ParsedSearchFaceResponse:
    client = boto3.client('rekognition')
    try:
        response: SearchFaceResponse = client.search_faces_by_image(CollectionId=collection_id, Image={'Bytes': image_bytes}, FaceMatchThreshold=threshold, MaxFaces=max_matches)
    except client.exceptions.InvalidParameterException as e:
        raise NoFaceInSearchingError(boto_exception=e)
    except client.exceptions.ImageTooLargeException as e:
        raise ImageTooLargeError(boto_exception=e)
    face_matches = response['FaceMatches']
    if len(face_matches) > 1:
        # TODO:
        # raise NotImplementedError('Not yet support multiple reference image for a single reference person.')
        pass

    if len(face_matches) == 0:
        raise NoMatchedFaceError(collection_id=collection_id)
    else:
        # TODO:
        # assert len(face_matches) == 1
        if config.VERBOSE:
            print(face_matches)
        return dict(MostFaceMatch=face_matches[0], SearchedFaceBoundingBox=response['SearchedFaceBoundingBox'])


def search_face_by_image(image_bytes: bytes, threshold: Optional[int] = None) -> ParsedSearchFaceResponse:
    collection_id = config.idols_collection_id
    max_matches = config.max_matches
    threshold = threshold if threshold is not None else config.default_threshold
    return _search_face_by_image(image_bytes=image_bytes, collection_id=collection_id, max_matches=max_matches, threshold=threshold)


if __name__ == '__main__':
    image_path = '../resources/jisoo_single.jpg'
    with open(image_path, 'rb') as file:
        image_bytes = file.read()
    image_bytes = utils.convert_image_bytes_popular(image_bytes=image_bytes)

    ic(search_face_by_image(image_bytes=image_bytes))


def detect_faces_by_image(image: Union[Image.Image, bytes]) -> List[utils_boto3.BoundingBox]:
    image_bytes = utils.as_image_bytes(image)
    assert isinstance(image_bytes, bytes) and len(image_bytes) > 100

    client = boto3.client('rekognition')
    response = client.detect_faces(Image={'Bytes': image_bytes})
    bounding_boxes: List[utils_boto3.BoundingBox] = [face_detail['BoundingBox'] for face_detail in response['FaceDetails']]
    return bounding_boxes


def get_all_detected_faces(image: Image.Image) -> List[Tuple[utils_boto3.BoundingBox, Image.Image]]:
    bounding_boxes = detect_faces_by_image(image=image)
    cropped_faces = []
    for bounding_box in bounding_boxes:
        margined_bounding_box = utils_boto3.margin_bounding_box(bounding_box=bounding_box)
        abs_margined_bounding_box_corners = utils_boto3.to_abs_bounding_box_corners(bounding_box=margined_bounding_box, size=image.size)
        cropped_image = image.crop(box=abs_margined_bounding_box_corners)
        cropped_faces.append((margined_bounding_box, cropped_image))
    return cropped_faces


def search_multiple_faces_by_image(image_bytes: bytes, threshold: Optional[int] = None) -> List[ParsedSearchFaceResponse]:
    image = Image.open(io.BytesIO(image_bytes))

    searcheds = []
    faces = get_all_detected_faces(image=image)
    for face_bounding_box, face_image in faces:
        try:
            searched = search_face_by_image(image_bytes=utils.pillow_to_bytes(face_image), threshold=threshold)
            searched['SearchedFaceBoundingBox'] = utils_boto3.join_relative_bounding_boxes(face_bounding_box, searched['SearchedFaceBoundingBox'])

            searcheds.append(searched)
        except NoMatchedFaceError:
            pass
    return searcheds


if __name__ == '__main__':
    image_path = '/home/gimun/Downloads/image_readtop_2021_1136232_16394818474883815.jpg'
    image = Image.open(image_path)
    searcheds = search_multiple_faces_by_image(image_bytes=utils.pillow_to_bytes(image=image))
    ic(searcheds)

    from PIL import ImageDraw
    def suggest_line_width(size: Tuple[float, float]) -> int:
        longer = max(size)
        return max(1, int(longer * 0.01))

    draw = ImageDraw.Draw(im=image,)
    for searched in searcheds:
        bounding_box_corners = utils_boto3.to_abs_bounding_box_corners(bounding_box=searched['SearchedFaceBoundingBox'], size=image.size)
        draw.rounded_rectangle(xy=bounding_box_corners, radius=suggest_line_width(image.size) * 4, width=suggest_line_width(image.size))
    image.show()
