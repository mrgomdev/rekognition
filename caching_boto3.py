from typing import List, Dict

import boto3


_list_faces: Dict[str, List[dict]] = dict()
def list_faces(collection_id: str, fresh: bool, max_results=100) -> List[dict]:
    if fresh or collection_id not in _list_faces:
        client = boto3.client('rekognition')

        faces = []
        response = client.list_faces(CollectionId=collection_id, MaxResults=max_results)
        while response is not None:
            faces.extend(list(response['Faces']))
            if 'NextToken' in response:
                next_token = response['NextToken']
                response = client.list_faces(CollectionId=collection_id, MaxResults=max_results, next_token=next_token)
            else:
                response = None
        _list_faces[collection_id] = faces
    return _list_faces[collection_id]
