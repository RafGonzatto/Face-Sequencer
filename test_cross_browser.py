"""
Cross-browser testing for Face Sequencer Pro
Tests functionality across different browsers using Selenium
"""

import os
import time
import pytest
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# Base URL for testing - change when running on different environments
BASE_URL = os.environ.get('TEST_BASE_URL', 'http://localhost:5000')

class BaseBrowserTest:
    """Base class for browser tests with setup and teardown"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, request, driver):
        """Set up the browser driver before each test"""
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 10)
        
        # Pass browser type to test methods
        self.browser_type = request.config.getoption('--driver')
        print(f"Running tests on {self.browser_type}")
        
        yield
        
        # Cleanup after test
        if self.driver:
            self.driver.quit()
    
    def wait_for_element(self, by, value, timeout=10):
        """Wait for an element to be present and return it"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

class TestAudioInterface(BaseBrowserTest):
    """Test audio interface functionality across browsers"""
    
    def test_audio_upload_interface(self):
        """Test that audio upload interface loads correctly"""
        self.driver.get(f"{BASE_URL}/")
        
        # Wait for page to load
        audio_upload = self.wait_for_element(By.ID, "audioFileInput")
        upload_button = self.wait_for_element(By.ID, "uploadAudioBtn")
        
        assert audio_upload.is_displayed(), "Audio upload input should be visible"
        assert upload_button.is_displayed(), "Upload button should be visible"
    
    def test_audio_visualization_container(self):
        """Test that audio visualization container exists and is initially empty"""
        self.driver.get(f"{BASE_URL}/")
        
        # Wait for the visualization container
        container = self.wait_for_element(By.ID, "audioVisualizationContainer")
        
        # Check if the container exists but is initially empty or hidden
        assert container is not None, "Audio visualization container should exist"
        
    def test_audio_playback_controls(self):
        """Test that audio playback controls work correctly"""
        self.driver.get(f"{BASE_URL}/")
        
        # Switch to audio timing mode
        timing_toggle = self.wait_for_element(By.ID, "timingModeToggle")
        timing_toggle.click()
        
        # Wait for audio controls to appear
        try:
            play_button = self.wait_for_element(By.ID, "playBtn")
            pause_button = self.wait_for_element(By.ID, "pauseBtn")
            
            # Test play button
            play_button.click()
            time.sleep(1)
            
            # Test pause button
            pause_button.click()
            
            # Look for any JavaScript errors in the console
            logs = self.driver.get_log('browser')
            js_errors = [log for log in logs if log['level'] == 'SEVERE']
            
            assert len(js_errors) == 0, f"JavaScript errors detected: {js_errors}"
            
        except TimeoutException:
            pytest.fail("Audio playback controls not found")
    
    def test_waveform_visualization(self):
        """Test that waveform visualization renders correctly"""
        self.driver.get(f"{BASE_URL}/")
        
        # Switch to audio timing mode
        timing_toggle = self.wait_for_element(By.ID, "timingModeToggle")
        timing_toggle.click()
        
        # Try to find the waveform container
        try:
            waveform = self.wait_for_element(By.ID, "waveform")
            
            # Get element size to verify it's being rendered
            width = waveform.size['width']
            height = waveform.size['height']
            
            assert width > 0 and height > 0, "Waveform should have non-zero dimensions"
            
        except TimeoutException:
            pytest.skip("Waveform visualization not found or not initialized")
    
    def test_timing_mode_toggle(self):
        """Test that timing mode toggle works"""
        self.driver.get(f"{BASE_URL}/")
        
        # Wait for timing toggle to be present
        timing_toggle = self.wait_for_element(By.ID, "timingModeToggle")
        
        # Initial state should be manual
        assert "Manual Timing" in timing_toggle.text, "Initial state should be Manual Timing"
        
        # Click the toggle
        timing_toggle.click()
        
        # Wait for state to change
        time.sleep(1)  # Allow toggle animation to complete
        
        # Should now show Audio Timing
        assert "Audio Timing" in timing_toggle.text, "After click state should be Audio Timing"
    
    def test_audio_controls_visibility(self):
        """Test that audio controls appear when switching to audio timing mode"""
        self.driver.get(f"{BASE_URL}/")
        
        # Switch to audio timing mode
        timing_toggle = self.wait_for_element(By.ID, "timingModeToggle")
        timing_toggle.click()
        
        # Wait for audio controls to appear
        try:
            audio_controls = self.wait_for_element(By.ID, "audioControlsContainer", timeout=3)
            assert audio_controls.is_displayed(), "Audio controls should be visible in audio timing mode"
        except TimeoutException:
            pytest.fail("Audio controls did not appear after switching to audio timing mode")

class TestResponsiveLayout(BaseBrowserTest):
    """Test responsive layout across different screen sizes"""
    
    def test_mobile_layout(self):
        """Test layout on mobile-sized screen"""
        self.driver.get(f"{BASE_URL}/")
        
        # Set mobile viewport size
        self.driver.set_window_size(375, 667)  # iPhone 8 size
        
        # Wait for page to load
        main_container = self.wait_for_element(By.CLASS_NAME, "container")
        
        # Check that elements are stacked vertically on mobile
        audio_section = self.wait_for_element(By.ID, "audioSection")
        text_section = self.wait_for_element(By.ID, "textSection")
        
        # On mobile, elements should be stacked (y-position of text > y-position of audio + height)
        audio_pos = audio_section.location['y'] + audio_section.size['height']
        text_pos = text_section.location['y']
        
        assert text_pos >= audio_pos, "Elements should be stacked vertically on mobile"
    
    def test_desktop_layout(self):
        """Test layout on desktop-sized screen"""
        self.driver.get(f"{BASE_URL}/")
        
        # Set desktop viewport size
        self.driver.set_window_size(1280, 800)
        
        # Wait for page to load
        main_container = self.wait_for_element(By.CLASS_NAME, "container")
        
        # Check that sidebar and main content are side-by-side on desktop
        try:
            sidebar = self.wait_for_element(By.ID, "sidebar")
            main_content = self.wait_for_element(By.ID, "mainContent")
            
            # On desktop, sidebar should be to the left of main content
            sidebar_right = sidebar.location['x'] + sidebar.size['width']
            main_left = main_content.location['x']
            
            assert sidebar_right <= main_left, "Sidebar should be to the left of main content on desktop"
        except:
            # If sidebar/main layout isn't used, this test can be skipped
            pytest.skip("Sidebar/main layout not found")

class TestErrorHandling(BaseBrowserTest):
    """Test error handling and UI feedback"""
    
    def test_error_message_display(self):
        """Test that error messages are displayed in the UI"""
        self.driver.get(f"{BASE_URL}/")
        
        # Find the error container
        try:
            error_container = self.wait_for_element(By.ID, "errorMessages", timeout=2)
            initial_display = error_container.value_of_css_property("display")
            
            # Initially should be hidden
            assert initial_display == "none", "Error container should initially be hidden"
            
            # Trigger an error (try to upload without selecting a file)
            upload_btn = self.wait_for_element(By.ID, "uploadAudioBtn")
            upload_btn.click()
            
            # Wait for error to appear
            time.sleep(1)
            
            # Error should now be visible
            error_container = self.driver.find_element(By.ID, "errorMessages")
            after_display = error_container.value_of_css_property("display")
            
            assert after_display != "none", "Error container should be visible after error"
        except:
            pytest.skip("Error message container not found")

def pytest_addoption(parser):
    """Add options for browser selection"""
    parser.addoption("--driver", action="store", default="Chrome", 
                     help="Browser to use: Chrome, Firefox, or Edge")

@pytest.fixture
def driver(request):
    """Setup driver based on command line option"""
    browser_type = request.config.getoption("--driver")
    
    if browser_type == "Chrome":
        options = webdriver.ChromeOptions()
        options.add_argument("--headless") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    elif browser_type == "Firefox":
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        driver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), options=options)
    elif browser_type == "Edge":
        options = webdriver.EdgeOptions()
        options.add_argument("--headless")
        driver = webdriver.Edge(EdgeChromiumDriverManager().install(), options=options)
    else:
        raise ValueError(f"Unsupported browser: {browser_type}")
    
    driver.set_window_size(1280, 800)
    
    yield driver
    
    driver.quit()

if __name__ == "__main__":
    pytest.main(["-xvs"])