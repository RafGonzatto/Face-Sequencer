from error_handlers import handle_api_errors, ClassifiedAPIError
from app import app as flask_app

class Dummy:
    @handle_api_errors()
    def value(self):
        raise ValueError('Bad input')

    @handle_api_errors()
    def not_found(self):
        raise FileNotFoundError('Missing resource')

    @handle_api_errors()
    def timeout(self):
        raise TimeoutError('Too slow')

    @handle_api_errors()
    def classified(self):
        raise ClassifiedAPIError('Broken', error_type='processing_error', status=422, details={'hint': 'x'})

    @handle_api_errors()
    def unexpected(self):
        raise RuntimeError('Boom')

def test_value_error_classification():
    d = Dummy()
    with flask_app.app_context():
        body, status = d.value()
    assert status == 400

def test_not_found_classification():
    d = Dummy()
    with flask_app.app_context():
        body, status = d.not_found()
    assert status == 404

def test_timeout_classification():
    d = Dummy()
    with flask_app.app_context():
        body, status = d.timeout()
    assert status == 504

def test_classified_passthrough():
    d = Dummy()
    with flask_app.app_context():
        body, status = d.classified()
    assert status == 422

def test_unexpected_error():
    d = Dummy()
    with flask_app.app_context():
        body, status = d.unexpected()
    assert status == 500
