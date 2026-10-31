"""Public login assets must not process attacker-controlled range explosions."""
from fastapi.testclient import TestClient

from bi_dashboard.service import app


def test_public_asset_ignores_excessive_ranges():
    client = TestClient(app)
    normal = client.get('/login.css')
    assert normal.status_code == 200
    # Keep the request below nginx's header limit while exceeding the parser's
    # range count bound. No production requests or CPU-exhaustion test is used.
    header = 'bytes=' + ','.join(['0-0'] * 1000)
    response = client.get('/login.css', headers={'Range': header})
    assert response.status_code == 200
    assert response.content == normal.content
    assert 'content-range' not in response.headers
