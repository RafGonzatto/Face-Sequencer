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
        resp = d.value()
    assert resp.status_code == 400
    body = resp.get_json()

def test_not_found_classification():
    d = Dummy()
    with flask_app.app_context():
        resp = d.not_found()
    assert resp.status_code == 404
    body = resp.get_json()

def test_timeout_classification():
    d = Dummy()
    with flask_app.app_context():
        resp = d.timeout()
    assert resp.status_code == 504
    body = resp.get_json()

def test_classified_passthrough():
    d = Dummy()
    with flask_app.app_context():
        resp = d.classified()
    assert resp.status_code == 422
    body = resp.get_json()

def test_unexpected_error():
    d = Dummy()
    with flask_app.app_context():
        resp = d.unexpected()
    assert resp.status_code == 500
    body = resp.get_json()
