"""
Visual regression testing for Face Sequencer Pro
Tests UI components for visual consistency across versions
"""

import os
import io
import pytest
import time
import json
import base64
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Base URL for testing
BASE_URL = os.environ.get('TEST_BASE_URL', 'http://localhost:5000')

# Directories for storing and comparing screenshots
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), 'screenshots')
BASELINE_DIR = os.path.join(SCREENSHOT_DIR, 'baseline')
CURRENT_DIR = os.path.join(SCREENSHOT_DIR, 'current')
DIFF_DIR = os.path.join(SCREENSHOT_DIR, 'diff')

# Make sure directories exist
os.makedirs(BASELINE_DIR, exist_ok=True)
os.makedirs(CURRENT_DIR, exist_ok=True)
os.makedirs(DIFF_DIR, exist_ok=True)

# Threshold for pixel difference (0-1, where 0 means exact match)
DIFF_THRESHOLD = 0.01

class TestVisualRegression:
    """Visual regression tests for UI components"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up WebDriver before each test"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        yield
        
        # Cleanup
        self.driver.quit()
    
    def wait_for_element(self, by, value, timeout=10):
        """Wait for an element to be present and return it"""
        return self.wait.until(EC.presence_of_element_located((by, value)))
    
    def take_element_screenshot(self, element_id, name, wait_time=1):
        """Take a screenshot of a specific element"""
        try:
            # Wait for element to be present and visible
            element = self.wait_for_element(By.ID, element_id)
            time.sleep(wait_time)  # Allow any animations to complete
            
            # Take screenshot of the specific element
            screenshot = element.screenshot_as_png
            
            # Save the screenshot
            screenshot_path = os.path.join(CURRENT_DIR, f"{name}.png")
            with open(screenshot_path, "wb") as file:
                file.write(screenshot)
            
            return screenshot_path
        except Exception as e:
            pytest.fail(f"Could not take screenshot of element {element_id}: {str(e)}")
    
    def compare_screenshots(self, name):
        """Compare current screenshot with baseline"""
        current_path = os.path.join(CURRENT_DIR, f"{name}.png")
        baseline_path = os.path.join(BASELINE_DIR, f"{name}.png")
        diff_path = os.path.join(DIFF_DIR, f"{name}.png")
        
        # If baseline doesn't exist, create it
        if not os.path.exists(baseline_path):
            print(f"Creating baseline for {name}")
            shutil.copy(current_path, baseline_path)
            return True
        
        # Open images
        baseline_img = Image.open(baseline_path)
        current_img = Image.open(current_path)
        
        # Make sure they're the same size
        if baseline_img.size != current_img.size:
            current_img = current_img.resize(baseline_img.size)
        
        # Calculate difference
        diff_img = ImageChops.difference(baseline_img, current_img)
        
        # Convert to numpy array for analysis
        diff_array = np.array(diff_img)
        total_pixels = diff_array.size / 3  # RGB image
        different_pixels = np.count_nonzero(diff_array) / 3
        
        # Calculate difference percentage
        diff_percentage = different_pixels / total_pixels if total_pixels > 0 else 0
        
        # If difference is above threshold, save diff image and return False
        if diff_percentage > DIFF_THRESHOLD:
            # Create a visual diff by highlighting differences
            diff_highlight = Image.new('RGBA', baseline_img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(diff_highlight)
            
            for y in range(diff_img.height):
                for x in range(diff_img.width):
                    pixel = diff_img.getpixel((x, y))
                    if sum(pixel) > 0:  # If there's any difference
                        draw.rectangle([x, y, x+1, y+1], fill=(255, 0, 0, 128))
            
            # Composite the images
            result = Image.alpha_composite(baseline_img.convert('RGBA'), diff_highlight)
            result.save(diff_path)
            
            print(f"Visual difference detected for {name}: {diff_percentage:.2%}")
            return False
        
        return True
    
    def test_main_interface(self):
        """Test the main interface appearance"""
        self.driver.get(f"{BASE_URL}/")
        
        # Wait for the page to load
        self.wait_for_element(By.TAG_NAME, "body")
        time.sleep(1)  # Allow for any dynamic content to load
        
        # Take screenshot of main container
        self.driver.save_screenshot(os.path.join(CURRENT_DIR, "main_interface.png"))
        
        # Compare with baseline
        assert self.compare_screenshots("main_interface"), "Main interface visual regression detected"
    
    def test_audio_upload_component(self):
        """Test the audio upload component appearance"""
        self.driver.get(f"{BASE_URL}/")
        
        # Take screenshot of audio upload section
        self.take_element_screenshot("audioSection", "audio_upload_component")
        
        # Compare with baseline
        assert self.compare_screenshots("audio_upload_component"), "Audio upload component visual regression detected"
    
    def test_audio_visualization(self):
        """Test the audio visualization component appearance"""
        self.driver.get(f"{BASE_URL}/")
        
        # Switch to audio timing mode
        timing_toggle = self.wait_for_element(By.ID, "timingModeToggle")
        timing_toggle.click()
        time.sleep(1)  # Wait for mode switch
        
        # Take screenshot of visualization container
        self.take_element_screenshot("audioVisualizationContainer", "audio_visualization")
        
        # Compare with baseline
        assert self.compare_screenshots("audio_visualization"), "Audio visualization visual regression detected"
    
    def test_sequence_preview(self):
        """Test the sequence preview component appearance"""
        self.driver.get(f"{BASE_URL}/")
        
        try:
            # Wait for sequence preview to be available
            self.wait_for_element(By.ID, "previewContainer")
            
            # Take screenshot of preview section
            self.take_element_screenshot("previewContainer", "sequence_preview")
            
            # Compare with baseline
            assert self.compare_screenshots("sequence_preview"), "Sequence preview visual regression detected"
        except TimeoutException:
            pytest.skip("Sequence preview component not available")
    
    @pytest.mark.parametrize('device', [
        {'name': 'mobile', 'width': 375, 'height': 667},
        {'name': 'tablet', 'width': 768, 'height': 1024},
        {'name': 'desktop', 'width': 1280, 'height': 800},
    ])
    def test_responsive_layout(self, device):
        """Test responsive layout at different screen sizes"""
        # Set window size according to device
        self.driver.set_window_size(device['width'], device['height'])
        
        # Load the page
        self.driver.get(f"{BASE_URL}/")
        self.wait_for_element(By.TAG_NAME, "body")
        time.sleep(1)  # Allow for any responsive adjustments
        
        # Take screenshot
        self.driver.save_screenshot(os.path.join(CURRENT_DIR, f"responsive_{device['name']}.png"))
        
        # Compare with baseline
        assert self.compare_screenshots(f"responsive_{device['name']}"), f"Responsive layout regression detected for {device['name']}"

def update_baselines():
    """Utility function to update all baseline images from current screenshots"""
    if not os.path.exists(CURRENT_DIR):
        print("No current screenshots found.")
        return
    
    # Create baseline directory if it doesn't exist
    os.makedirs(BASELINE_DIR, exist_ok=True)
    
    # Copy all current screenshots to baseline
    for filename in os.listdir(CURRENT_DIR):
        if filename.endswith('.png'):
            src = os.path.join(CURRENT_DIR, filename)
            dst = os.path.join(BASELINE_DIR, filename)
            shutil.copy2(src, dst)
            print(f"Updated baseline: {filename}")

if __name__ == "__main__":
    # If run directly, provide option to update baselines
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--update-baselines":
        update_baselines()
    else:
        pytest.main(["-v", __file__])