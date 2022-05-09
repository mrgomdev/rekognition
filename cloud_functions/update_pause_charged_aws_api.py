from types import MappingProxyType
import requests


_session = requests.session()


CHARGED_APIS = MappingProxyType({
    'Rekognition': (
        'index_faces',
        'search_faces_by_image',
        'search_faces',
        'detect_faces'
    ),
    's3': tuple()
})


def update_hot_charged_logs(event, context):
    response = _session.get('https://modi-11e0c-default-rtdb.firebaseio.com/rekognition/logs.json')
    parsed = response.json()
    count = 0
    for key, value in sorted(parsed.items(), key=lambda kv: kv[1]['kst']):
        if value['client_service_id'] not in CHARGED_APIS:
            raise KeyError(f'Invalid client_class_name')
        client_service_id = value['client_service_id']

        is_charged = False
        if value['client_api_name'] in CHARGED_APIS[client_service_id]:
            is_charged = True
            count += 1
        print(f'is_charged: {is_charged}, {key}: {value}')

    configs = _session.get('https://modi-11e0c-default-rtdb.firebaseio.com/rekognition/configs.json').json()
    assert isinstance(configs['max-every-minute'], int)

    pause_charged_aws_api = count >= configs['max-every-minute']
    response = _session.put('https://modi-11e0c-default-rtdb.firebaseio.com/rekognition/flags/pause-charged-aws-api.json', json=pause_charged_aws_api)
    print(response)
    assert response.ok
