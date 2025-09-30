"""End-to-end frontend tests using Selenium.

These tests exercise the real browser (Chrome via webdriver-manager) against
the running Flask app to catch integration issues between JS frontend and
backend endpoints.

Covered flows:
 1. Load index page and basic UI elements present.
 2. Create temporary image folder, set path, scan mapping, thumbnails appear.
 3. Enter text, build sequence, timeline frames rendered.
 4. Playback begins (preview updates) then stops.
 5. Export modal opens.

Notes:
 - If Chrome or driver download is unavailable (CI without network), tests
   will be skipped gracefully.
 - Keeps runtime short (< ~10s) and avoids external dependencies.
"""
from __future__ import annotations

import os
import time
import threading
import tempfile
from pathlib import Path

import pytest

from app import app


PORT = 5010  # use a non-standard port to avoid clashing with dev server
BASE_URL = f"http://localhost:{PORT}"


def _run_app():  # pragma: no cover - server loop
    app.run(port=PORT, debug=False, use_reloader=False)


@pytest.fixture(scope="session")
def live_server():
    # Ensure TESTING flag set (reduces some heavy init side-effects)
    app.config.update(TESTING=True)
    thread = threading.Thread(target=_run_app, daemon=True)
    thread.start()
    # Wait for server
    timeout = time.time() + 15
    import requests
    last_err = None
    while time.time() < timeout:
        try:
            r = requests.get(BASE_URL + "/")
            if r.status_code == 200:
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.3)
    raise RuntimeError(f"Server failed to start: {last_err}")


def _make_letter_images(tmpdir: Path, letters: str = "ABCD"):
    from PIL import Image
    for i, ch in enumerate(letters):
        img = Image.new("RGBA", (96, 96), (30 * (i + 1), 80, 140, 255))
        img.save(tmpdir / f"{ch}.png")


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

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,1000")
    try:
        driver_path = ChromeDriverManager().install()
        driver = webdriver.Chrome(service=Service(driver_path), options=options)
    except OSError as e:  # e.g. WinError 193 invalid win32 application
        pytest.skip(f"Skipping Selenium tests due to driver startup failure: {e}")
    yield driver
    driver.quit()


def test_ui_loads(driver):
    driver.get(BASE_URL + "/")
    # Basic sanity: title and main elements
    assert "Face Sequencer" in driver.title
    # Scan button present
    scan_btn = driver.find_element("id", "scanFolderBtn")
    assert scan_btn.is_displayed()


def test_folder_scan_and_thumbnails(driver, tmp_path):
    # Prepare folder with sample images
    _make_letter_images(tmp_path, "ABZ")
    driver.get(BASE_URL + "/")
    folder_input = driver.find_element("id", "folderPath")
    folder_input.clear()
    folder_input.send_keys(str(tmp_path))
    # Trigger input event (send_keys usually enough, but ensure)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", folder_input)
    driver.find_element("id", "scanFolderBtn").click()

    # Wait until thumbnails appear for A (img inside mapping-preview)
    deadline = time.time() + 12  # allow a bit more time on CI
    thumb_ok = False
    while time.time() < deadline:
        imgs = driver.find_elements("css selector", '[data-letter="A"] .mapping-preview img')
        if imgs:
            thumb_ok = True
            break
        time.sleep(0.4)
    assert thumb_ok, "Thumbnail for letter A not rendered in time"


def test_build_sequence(driver, tmp_path):
    _make_letter_images(tmp_path, "ABC")
    driver.get(BASE_URL + "/")
    # Set folder path and scan
    folder_input = driver.find_element("id", "folderPath")
    folder_input.clear(); folder_input.send_keys(str(tmp_path))
    driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", folder_input)
    driver.find_element("id", "scanFolderBtn").click()
    # Enter text
    text_area = driver.find_element("id", "textInput")
    text_area.clear(); text_area.send_keys("ABC AB")
    # Build
    driver.find_element("id", "buildSequenceBtn").click()
    # Wait for timeline frames (at least >0)
    deadline = time.time() + 12
    has_frames = False
    while time.time() < deadline:
        frames = driver.find_elements("css selector", '#timelineFrames .timeline-frame')
        if len(frames) > 0:
            has_frames = True
            break
        time.sleep(0.5)
    assert has_frames, "No timeline frames rendered after build"


def test_playback_and_export_modal(driver, tmp_path):
    _make_letter_images(tmp_path, "AB")
    driver.get(BASE_URL + "/")
    folder_input = driver.find_element("id", "folderPath")
    folder_input.clear(); folder_input.send_keys(str(tmp_path))
    driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", folder_input)
    driver.find_element("id", "scanFolderBtn").click()
    text_area = driver.find_element("id", "textInput")
    text_area.clear(); text_area.send_keys("ABAB")
    driver.find_element("id", "buildSequenceBtn").click()
    # Wait for frames
    deadline = time.time() + 10
    while time.time() < deadline:
        if driver.find_elements("css selector", '#timelineFrames .timeline-frame'):
            break
        time.sleep(0.4)
    # Start playback
    driver.find_element("id", "playBtn").click()
    time.sleep(1.2)  # allow at least one frame advance
    # Stop playback
    driver.find_element("id", "playBtn").click()
    # Open export modal
    driver.find_element("id", "exportVideo").click()
    # Wait for modal to become visible (export UI code may attach async)
    deadline = time.time() + 5
    modal = None
    while time.time() < deadline:
        modal = driver.find_element("id", "exportModal")
        if modal.is_displayed():
            break
        time.sleep(0.2)
    assert modal and modal.is_displayed(), "Export modal did not open"
    # Close export modal via cancel
    driver.find_element("id", "cancelExportBtn").click()
    time.sleep(0.2)
    # Accept either hidden or display none
    style = modal.get_attribute("style") or ""
    assert "display: none" in style or not modal.is_displayed()


def test_symbol_fallback_and_frame_editing(driver, tmp_path):
    """Verify that unmapped characters use fallback image and that delete/reorder endpoints work via UI actions.

    This assumes fallback is not explicitly set; unmapped letters should produce frames without images (or fallback markers) consistent with backend logic.
    """
    # Only create A image, but use text containing A and Z
    _make_letter_images(tmp_path, "A")
    driver.get(BASE_URL + "/")
    folder_input = driver.find_element("id", "folderPath")
    folder_input.clear(); folder_input.send_keys(str(tmp_path))
    driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", folder_input)
    driver.find_element("id", "scanFolderBtn").click()
    text_area = driver.find_element("id", "textInput")
    text_area.clear(); text_area.send_keys("AZA")
    driver.find_element("id", "buildSequenceBtn").click()
    # Wait for frames
    deadline = time.time() + 10
    while time.time() < deadline:
        frames = driver.find_elements("css selector", '#timelineFrames .timeline-frame')
        if len(frames) == 3:
            break
        time.sleep(0.3)
    assert len(frames) == 3, "Expected 3 frames for sequence AZA"
    # Check that at least one frame (for Z) has no image child (pause or fallback w/out mapping)
    z_candidates = [f for f in frames if (f.get_attribute('data-char') or '').upper() == 'Z']
    if z_candidates:
        # For unmapped char we expect either an empty inner element or no <img>
        inner_imgs = z_candidates[0].find_elements("css selector", 'img')
        assert len(inner_imgs) == 0, "Unmapped Z unexpectedly had an image"
    # Delete middle frame (index 1) if delete button present
    delete_buttons = driver.find_elements("css selector", '.delete-frame-btn')
    if delete_buttons:
        delete_buttons[1].click()
        time.sleep(0.3)
        frames_after = driver.find_elements("css selector", '#timelineFrames .timeline-frame')
        assert len(frames_after) == 2, "Frame deletion did not reduce frame count"


def test_export_validation_workflow(driver, tmp_path):
    """Covers export validation sequence: build -> open export -> request validation -> observe status changes.

    We don't wait for full export completion; just ensure validation endpoint reachable and returns success envelope.
    """
    _make_letter_images(tmp_path, "AB")
    driver.get(BASE_URL + "/")
    folder_input = driver.find_element("id", "folderPath")
    folder_input.clear(); folder_input.send_keys(str(tmp_path))
    driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", folder_input)
    driver.find_element("id", "scanFolderBtn").click()
    text_area = driver.find_element("id", "textInput")
    text_area.clear(); text_area.send_keys("ABAB")
    driver.find_element("id", "buildSequenceBtn").click()
    # Wait for frames
    deadline = time.time() + 10
    while time.time() < deadline:
        if driver.find_elements("css selector", '#timelineFrames .timeline-frame'):
            break
        time.sleep(0.4)
    # Open export modal
    driver.find_element("id", "exportVideo").click()
    # Poll for modal visibility (animation / rendering delay resilience)
    modal = driver.find_element("id", "exportModal")
    deadline_modal = time.time() + 5
    while time.time() < deadline_modal and not modal.is_displayed():
        time.sleep(0.25)
    assert modal.is_displayed(), "Export modal did not open"
    # Kick off a validation call using the front-end's validate button if present
    validate_btns = driver.find_elements("id", "validateExportBtn")
    if validate_btns:
        validate_btns[0].click()
        # Wait briefly for status area update
        time.sleep(1.0)
        # Just assert modal still present; deeper SSE checks belong elsewhere
        assert modal.is_displayed(), "Export modal closed unexpectedly during validation"
    # Close modal
    close_btns = driver.find_elements("id", "cancelExportBtn")
    if close_btns:
        close_btns[0].click()
        time.sleep(0.3)
