from flask import render_template

import rekognition.utils_alert
from flask_app import app


@app.route('/')
def hello():
    return render_template('index.html')


@app.route('/upload', methods=['GET'])
def upload_get():
    return render_template('upload.html')


@app.errorhandler(500)
def server_error(e):
    try:
        return render_template('error.html', body=str(e.original_exception)), 500
    finally:
        rekognition.utils_alert.alert_slack_exception(error_code=-1, exception=e)
