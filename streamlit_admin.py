from typing import Tuple
import io
import posixpath
import urllib.parse
import json

from PIL import Image
import requests
import streamlit as st
st.set_page_config(page_title="Upload Face", layout='wide')

import rekognition.utils_alert
import rekognition.utils_boto3
import rekognition.utils
import rekognition.manage_faces

import utils_streamlit


SESSION_STATE_INITS = dict(file_uploader_key_index=0, urls=[])
for key, value in SESSION_STATE_INITS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def main():
    with st.container():
        st.header('Upload new image')

        st.button(label='Upload', on_click=upload)

        st.text_input(label='idol_id', placeholder='jennie-blackpink', key='idol_id', on_change=lambda: st.session_state.__setitem__('idol_id', st.session_state.idol_id.strip()))

        urls_container = st.container()

        input_url = st.text_input(label="input_url", placeholder="https://...", key='input_url')
        def add_input_url():
            assert isinstance(st.session_state.urls, list)
            st.session_state.urls.append(input_url)
            st.session_state.input_url = ''
        st.button('Add', on_click=add_input_url)

        col1, col2 = urls_container.columns(2)
        for idx, each_url in enumerate(st.session_state.urls):
            col1.text(f'{idx}. {each_url}')
            if col2.button('del', key=f'url_del_{idx}'):
                st.session_state.urls.remove(each_url)
                st.experimental_rerun()

        if len(st.session_state.urls) > 0:
            cols = urls_container.columns(len(st.session_state.urls))
            for idx, (col, each_url) in enumerate(zip(cols, st.session_state.urls)):
                col.image(each_url)
                col.caption(f'{idx}')

        # TODO:
        # file = st.file_uploader(label='image', accept_multiple_files=False, key=f'file_uploader{st.session_state.file_uploader_key_index}', on_change=clear_url)


def upload_each(idol_id: str, each_url: str) -> Tuple[dict, dict]:
    assert idol_id != ''

    content_type, image_bytes_io = load_image_from_url(url=each_url)

    image_s3_bucket_name = rekognition.config.idols_bucket_name
    image_s3_object_key = posixpath.join(rekognition.config.idols_profile_root_path, idol_id, posixpath.basename(urllib.parse.urlparse(url=each_url).path)).replace('\\', '/')

    result = rekognition.manage_faces.upload_idol(image=image_bytes_io, idol_id=idol_id, image_s3_bucket_name=image_s3_bucket_name, image_s3_object_key=image_s3_object_key, content_type=content_type)
    result['image_from_url'] = each_url

    face_meta = result['FaceRecords'][0]['Face']

    db_dict = {
        'face_id': face_meta['FaceId'],
        'idol_id': idol_id,
        'collection_id': rekognition.config.idols_collection_id,
        'image_id': face_meta['ImageId'],
        'external_image_id': face_meta['ExternalImageId'],
        'image_s3_bucket_name': image_s3_bucket_name,
        'image_s3_object_key': image_s3_object_key,
        'image_from_url': each_url
    }
    success_dict = dict(face=face_meta, idol_id=idol_id, image_s3_bucket_name=image_s3_bucket_name, image_s3_object_key=image_s3_object_key, content_type=content_type)
    return db_dict, success_dict


def upload():
    with st.spinner():
        try:
            if st.session_state.idol_id == '':
                raise ValueError("idol_id must not be empty!")
            idol_id = st.session_state.idol_id
        except ValueError as e:
            st.exception(e)
            return

        if len(st.session_state.urls) > 0:
            assert isinstance(st.session_state.urls, list)
            db_dicts = []
            for idx, each_url in enumerate(tuple(st.session_state.urls)):
                try:
                    db_dict, success_dict = upload_each(idol_id=idol_id, each_url=each_url)
                    st.caption(f'{idx}.')
                    st.success(json.dumps(success_dict, indent=2))
                    db_dicts.append(db_dict)
                except Exception as e:
                    st.exception(e)
                else:
                    st.session_state.urls.remove(each_url)
            if len(db_dicts) > 0:
                st.code('\n'.join([','.join([db_dict[key] for key in ['face_id', 'idol_id', 'collection_id', 'image_id', 'external_image_id', 'image_s3_bucket_name', 'image_s3_object_key', 'image_from_url']]) for db_dict in db_dicts]))

        if len(st.session_state.urls) == 0:
            st.session_state.idol_id = ''


def load_image_from_url(url: str):
    with requests.session() as session:
        response = session.get(url=url)
        if not response.headers['Content-Type'].startswith('image/'):
            raise ValueError(f"Should be image! {response.headers['Content-Type']}")
        image = Image.open(io.BytesIO(response.content))
        image = rekognition.utils.convert_pillow_image_popular(image)
    content_type = Image.MIME[image.format]
    image_bytes_io = io.BytesIO()
    image.save(image_bytes_io, format=image.format)
    image_bytes_io.seek(0)
    return content_type, image_bytes_io


if __name__ == '__main__':
    if utils_streamlit.ask_admin_password():
        main()
