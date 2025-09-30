import pytest

@pytest.fixture()
def client():
	# Lazy import app to avoid side-effects before tests begin
	from app import app as flask_app
	# Ensure essential blueprints are registered for tests that assume presence
	missing = []
	if 'models' not in flask_app.blueprints:
		try:
			from model_endpoints import model_bp
			flask_app.register_blueprint(model_bp)
		except Exception as e:  # noqa: BLE001
			missing.append(f"models:{e}")
	if 'export' not in flask_app.blueprints:
		try:
			from export_endpoints import export_bp
			flask_app.register_blueprint(export_bp)
		except Exception as e:  # noqa: BLE001
			missing.append(f"export:{e}")
	if 'util' not in flask_app.blueprints:
		try:
			from util_endpoints import util_bp
			flask_app.register_blueprint(util_bp)
		except Exception as e:  # noqa: BLE001
			missing.append(f"util:{e}")
	if missing:
		print(f"[conftest] Warning: missing blueprint(s) -> {missing}")
	# Debug: list some expected routes once
	try:
		paths = sorted({r.rule for r in flask_app.url_map.iter_rules() if any(seg in r.rule for seg in ['models','export/video','util/error-demo'])})
		print('[conftest] routes snapshot:', paths)
	except Exception:
		pass
	with flask_app.test_client() as c:
		yield c
