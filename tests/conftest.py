import pytest

@pytest.fixture()
def client():
	# Lazy import app to avoid side-effects before tests begin
	from app import app as flask_app
	with flask_app.test_client() as c:
		yield c
