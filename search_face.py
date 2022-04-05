from icecream import ic
# ic = print

import boto3

from utils import *
import caching_boto3


def is_reference_external_image(external_image_id: str) -> bool:
    return external_image_id.startswith('idol-')


REFERENCE_FACES_COLLECTION_ID = "idols"
REFERENCE_FACES = [{key: face_dict[key] for key in ['ExternalImageId', 'FaceId']} for face_dict in caching_boto3.list_faces(collection_id=REFERENCE_FACES_COLLECTION_ID, fresh=False) if is_reference_external_image(face_dict['ExternalImageId'])]


def search_face_id(face_id: str, collection_id: str):
    threshold = 90
    max_faces = 2
    client = boto3.client('rekognition')
    response = client.search_faces(CollectionId=collection_id, FaceId=face_id, FaceMatchThreshold=threshold, MaxFaces=max_faces)
    assert response['SearchedFaceId'] == face_id
    assert len(response['FaceMatches']) >= 1
    assert list(response['FaceMatches']) == list(sorted(response['FaceMatches'], key=lambda face_match: face_match['Similarity'], reverse=True))
    for face_match in list(response['FaceMatches']):
        ic(face_match['Face'])


def search_face_by_image(image_bytes: bytes, collection_id: str, max_matches: int = 10, threshold: int = 70) -> dict:
    client = boto3.client('rekognition')
    response = client.search_faces_by_image(CollectionId=collection_id, Image={'Bytes': image_bytes}, FaceMatchThreshold=threshold, MaxFaces=max_matches)
    face_matches = response['FaceMatches']
    reference_face_matches = [face_match for face_match in face_matches if is_reference_external_image(face_match['Face']['ExternalImageId'])]
    if len(reference_face_matches) > 1:
        raise NotImplementedError('Not yet support multiple reference image for a single reference person.')

    return reference_face_matches[0]


if __name__ == '__main__':
    image_bytes = load_image_bytes(image_path='./resources/jisu_single.jpg')
    collection_id = 'idols'
    threshold = 70
    max_matches = 3

    ic(search_face_by_image(image_bytes=image_bytes, collection_id=collection_id, max_matches=max_matches, threshold=threshold))
