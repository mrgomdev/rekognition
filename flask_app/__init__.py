from flask import Flask
app = Flask(__name__)

import rekognition.utils_alert

INCLUDE_VIEWS = False

from . import models

if INCLUDE_VIEWS:
    from . import views
else:
    @app.route('/hello')
    def hello():
        return models.render_template('', error_code=0, message='Hello World')

    @app.errorhandler(500)
    def server_error(e):
        assert 'werkzeug.exceptions.InternalServerError' in str(type(e))
        original_exception = e.original_exception
        try:
            return models.render_template('', error_code=-1, body=dict(exception=f'{type(original_exception)}: {str(original_exception)}')), 500
        finally:
            rekognition.utils_alert.alert_slack_exception(error_code=-1, exception=original_exception)
