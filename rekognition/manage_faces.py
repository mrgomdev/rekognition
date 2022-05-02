from __future__ import annotations
from typing import Union, IO, Optional, List

import os
import glob
from tqdm import tqdm

import boto3

try:
    from . import utils_alert
    from . import config
    from .idol import Idol
    from . import utils_boto3
    from .caching_boto3 import list_faces
except ImportError:
    import utils_alert
    import config
    from idol import Idol
    import utils_boto3
    from caching_boto3 import list_faces
if not config.VERBOSE:
    def tqdm(iterable=None, *_, **__):
        return iterable


@utils_alert.alert_slack_when_exception
def _clear_all_idols(collection_id: str) -> None:
    client = boto3.client('rekognition')
    client.delete_collection(CollectionId=collection_id)
    client.create_collection(CollectionId=collection_id)
def clear_all_idols() -> None:
    _clear_all_idols(collection_id=config.idols_collection_id)


@utils_alert.alert_slack_when_exception
def upload_idol_local(image_path: str, idol_id: str) -> dict:
    image_s3_bucket_name = config.idols_bucket_name
    image_s3_object_key = os.path.join(config.idols_profile_root_path, idol_id, os.path.basename(image_path))
    if os.sep == '\\' and os.sep in image_s3_object_key:
        image_s3_object_key = image_s3_object_key.replace(os.sep, '/')
    with open(image_path, 'rb') as file:
        image = file.read()
    return upload_idol(image=image, idol_id=idol_id, image_s3_bucket_name=image_s3_bucket_name, image_s3_object_key=image_s3_object_key)


@utils_alert.alert_slack_when_exception
def upload_idol(image: Union[str, IO], idol_id: str, image_s3_bucket_name: str, image_s3_object_key: str, content_type: Optional[str] = None):
    utils_boto3.upload_s3(file=image, bucket_name=image_s3_bucket_name, key=image_s3_object_key, content_type=content_type)
    idol = Idol(idol_id=idol_id, image_s3_bucket_name=config.idols_bucket_name, image_s3_object_key=image_s3_object_key)

    collection_id = config.idols_collection_id
    try:
        client = boto3.client('rekognition')
        return client.index_faces(Image=dict(S3Object=dict(Bucket=idol.image_s3_bucket_name, Name=idol.image_s3_object_key)), CollectionId=collection_id, ExternalImageId=idol.to_external_image_id(), DetectionAttributes=['ALL'], MaxFaces=1)
    except:
        client = boto3.client('s3')
        client.delete_object(Bucket=config.idols_bucket_name, Key=image_s3_object_key)
        raise


@utils_alert.alert_slack_when_exception
def upload_idols_from_directory(root_path: str) -> List[dict]:
    idols_responses = []
    for dir_path in filter(os.path.isdir, tqdm(glob.glob(os.path.join(root_path, '*')))):
        idol_id = os.path.basename(dir_path)
        for image_path in filter(os.path.isfile, glob.glob(os.path.join(dir_path, '*'))):
            idols_responses.append(upload_idol_local(image_path=image_path, idol_id=idol_id))

    return idols_responses


if __name__ == '__main__' and True:
    clear_all_idols()

    upload_idols_from_directory(root_path="C:\\Users\\gomde\\Downloads\\sample_profiles")

    faces = list_faces(collection_id=config.idols_collection_id, fresh=True)
    for face in faces:
        idol = Idol.from_face_dict_aws(face_dict=face)
        print(idol)
