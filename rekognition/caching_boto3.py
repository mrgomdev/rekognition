from typing import List, Dict

import boto3

try:
    from . import utils_alert
    from . import utils_boto3
    from .idol import Idol
except ImportError:
    import utils_alert
    import utils_boto3
    from idol import Idol


_LIST_FACES: Dict[str, List[utils_boto3.Face]] = dict()
@utils_alert.alert_slack_when_exception
@utils_boto3.handle_request_error
def list_faces(collection_id: str, fresh: bool, max_results=100) -> List[utils_boto3.Face]:
    if fresh or collection_id not in _LIST_FACES:
        client = boto3.client('rekognition')

        faces: List[utils_boto3.Face] = []
        response = client.list_faces(CollectionId=collection_id, MaxResults=max_results)
        while response is not None:
            faces.extend(list(response['Faces']))
            if 'NextToken' in response:
                next_token = response['NextToken']
                response = client.list_faces(CollectionId=collection_id, MaxResults=max_results, NextToken=next_token)
            else:
                response = None
        _LIST_FACES[collection_id] = faces
    return _LIST_FACES[collection_id]


_LIST_IDOLS: Dict[str, List[Idol]] = dict()
@utils_alert.alert_slack_when_exception
@utils_boto3.handle_request_error
def list_idols(collection_id: str, fresh: bool, max_results=100) -> List[Idol]:
    faces = list_faces(collection_id=collection_id, fresh=fresh, max_results=max_results)
    return [Idol.from_face_dict_aws(face_dict=face) for face in faces]
