import os

api_url_root = os.environ['IDOL_STREAMLIT_API_URL_ROOT']
if api_url_root.endswith('/'):
    api_url_root = api_url_root[:-1]
assert not api_url_root.endswith('/')

image_types = ['jpg', 'jpeg', 'png', 'bmp', 'gif', 'webp']