"""End-to-end test for Video Editor enhanced subtitle generation.

Covers:
 1. Loading index page and ensuring video editor UI present.
 2. Injecting a small synthetic audio blob (WebM/Opus) via MediaRecorder polyfill stub.
 3. Entering sample text and triggering Generate subtitles.
 4. Verifying upload succeeds (no 422) and streaming phases advance to at least 'transcribe' or completion.
 5. Ensuring partial transcript panel appears and token counter updates.

Skips gracefully if selenium/webdriver-manager unavailable.
"""
from __future__ import annotations

import os
import time
import threading
import base64
from pathlib import Path

import pytest

from app import app

PORT = 5011
BASE_URL = f"http://localhost:{PORT}"

# A very small valid WebM (Opus) encoded silence snippet (couple of frames)
# Generated externally; kept tiny to minimize decode overhead.
# If decoding fails in some browsers, fallback JS will still attempt upload.
MINI_WEBM_BASE64 = (
    "GkXfo59ChoEBQveBAULygQFC8oEBQv6BAUL+hAFC/oQBTmVtYWRhdGGEAAAAA"
    "AAAAA//8AALgAAAAAAAC4AAAAAAAAAAAAAAAAAAAAAAA="
)

def _run_app():  # pragma: no cover
    app.config.update(TESTING=True)
    app.run(port=PORT, debug=False, use_reloader=False)

@pytest.fixture(scope="session")
def live_server():
    t = threading.Thread(target=_run_app, daemon=True)
    t.start()
    import requests
    deadline = time.time() + 15
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(BASE_URL + "/")
            if r.status_code == 200:
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.3)
    raise RuntimeError(f"Server did not start: {last_err}")


def _skip_if_no_selenium():
    try:
        import selenium  # noqa: F401
        from webdriver_manager.chrome import ChromeDriverManager  # noqa: F401
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Selenium/webdriver-manager not available: {e}")

@pytest.fixture()
def driver(live_server):  # noqa: PT004
    _skip_if_no_selenium()
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1600,1000")
    try:
        driver_path = ChromeDriverManager().install()
        drv = webdriver.Chrome(service=Service(driver_path), options=opts)
    except OSError as e:
        pytest.skip(f"Skipping video editor alignment E2E due to driver startup failure: {e}")
    yield drv
    drv.quit()


def test_enhanced_alignment_stream(driver):
    driver.get(BASE_URL + "/")

    # Basic sanity
    assert "Face Sequencer" in driver.title

    # Inject synthetic audio blob and stub extraction path:
    # We patch the VideoEditor.alignAudioWithText to bypass real MediaRecorder path
    js_patch = f"""
    (function() {{
      const blob = new Blob([Uint8Array.from(atob('{MINI_WEBM_BASE64}'), c=>c.charCodeAt(0))], {{type:'audio/webm'}});
      const original = window.videoEditor?.alignAudioWithText;
      if(!original) return;
      window.__e2eUploaded = false;
      window.videoEditor.alignAudioWithText = async function(fakeBlob, text, progressCb) {{
        // Force using our synthetic blob always
        return original.call(this, blob, text, progressCb);
      }};
    }})();
    """
    driver.execute_script(js_patch)

    # Provide a small text (Portuguese to match language param)
    text_area = driver.find_element("id", "textInput")
    text_area.clear(); text_area.send_keys("Olá mundo teste")

    # Trigger generate subtitles (button id assumed present)
    gen_btn = driver.find_element("id", "generateSubtitlesBtn")
    gen_btn.click()

    # Wait for either partial transcript div or completion token counter
    deadline = time.time() + 25
    saw_partial = False
    saw_progress_phase = False
    while time.time() < deadline:
        # Partial transcript panel class
        panels = driver.find_elements("css selector", ".partial-transcript-panel")
        if panels:
            saw_partial = True
        # Look for any progress label update in DOM (token counter element?)
        # We search by text content heuristically
        body_txt = driver.find_element("tag name", "body").text.lower()
        if "transcrevendo" in body_txt or "alinhando" in body_txt:
            saw_progress_phase = True
        # Detect error 422 surfaced via toast or console (heuristic) -> fail early
        if "422" in body_txt and "upload failed" in body_txt:
            raise AssertionError("Encountered 422 upload failure in UI during alignment")
        if saw_partial and saw_progress_phase:
            break
        time.sleep(0.6)

    assert saw_partial, "Partial transcript panel never appeared"
    assert saw_progress_phase, "Did not observe any streaming progress phase keywords"

    # If complete event occurs, resume button should disable; just sanity-check no fatal error message
    page_txt = driver.find_element("tag name", "body").text.lower()
    assert "streaming alignment error" not in page_txt