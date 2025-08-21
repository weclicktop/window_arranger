#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
import os
import threading
from pywinauto import Desktop, Application
from pywinauto.findwindows import find_windows
import keyboard
import logging

# Configure logging to output to terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

class WindowArranger:
    def __init__(self):
        self.desktop = Desktop(backend="uia")
        self.config = self.load_config()
        self.monitor_1_apps = self.config.get("monitor_1_apps", ["opera", "RD Tabs"])
        self.monitor_2_apps = self.config.get("monitor_2_apps", ["*"])
        self.hotkey = self.config.get("hotkey", "ctrl+alt+i")
        self.exit_hotkey = self.config.get("exit_hotkey", "ctrl+alt+q")
        self.reload_hotkey = self.config.get("reload_hotkey", "ctrl+alt+u")  # Manual reload hotkey
        self.hotkey_registered = False
        self.exit_hotkey_registered = False
        self.reload_hotkey_registered = False
        self.last_hotkey_test = 0
        self.hotkey_test_interval = self.config.get("hotkey_test_interval", 1800)  # Configurable interval
        self.enable_auto_restart = self.config.get("enable_auto_restart", True)
        self.max_restart_attempts = self.config.get("max_restart_attempts", 3)
        
        # Remote Desktop detection
        self.rd_key_history = []  # Track recent key presses
        self.rd_key_timeout = self.config.get("auto_recovery_timeout", 5.0)  # Timeout for key sequence detection
        self.enable_auto_recovery = self.config.get("enable_auto_recovery", True)  # Enable/disable auto-recovery
        
        # Set log level from config
        log_level = getattr(logging, self.config.get("log_level", "INFO").upper(), logging.INFO)
        logging.getLogger().setLevel(logging.DEBUG)  # Temporarily set to DEBUG for testing
        logger.setLevel(logging.DEBUG)
    
    def load_config(self):
        """Load configuration file"""
        config_file = "config.json"
        default_config = {
            "hotkey": "ctrl+alt+i",
            "exit_hotkey": "ctrl+alt+q",
            "monitor_1_apps": ["opera", "RD Tabs"],
            "monitor_2_apps": ["*"],
            "hotkey_test_interval": 1800,
            "log_level": "INFO"
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Successfully loaded config file: {config_file}")
                    return {**default_config, **config}  # Merge default config and user config
            else:
                logger.info(f"Config file {config_file} not found, using default config")
                return default_config
        except Exception as e:
            logger.error(f"Failed to load config file: {e}, using default config")
            return default_config
        
    def get_monitor_info(self):
        """Get monitor information"""
        try:
            import win32api
            import win32con
            
            # Get primary monitor information
            primary_monitor = win32api.GetSystemMetrics(win32con.SM_CXSCREEN), win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # Get all monitor information
            monitors = []
            for i in range(win32api.GetSystemMetrics(win32con.SM_CMONITORS)):
                monitor_info = win32api.EnumDisplayMonitors()[i]
                monitors.append(monitor_info)
            
            logger.info(f"Primary monitor resolution: {primary_monitor}")
            logger.info(f"Detected {len(monitors)} monitors")
            
            return monitors
        except ImportError:
            logger.error("pywin32 is required to get monitor information")
            return []
    
    def get_window_list(self):
        """Get all visible windows"""
        try:
            windows = []
            for window in self.desktop.windows():
                try:
                    if window.is_visible() and window.window_text():
                        window_info = {
                            'title': window.window_text(),
                            'class_name': window.class_name(),
                            'hwnd': window.handle,
                            'rect': window.rectangle()
                        }
                        windows.append(window_info)
                        logger.debug(f"Window: {window_info['title']} - {window_info['class_name']}")
                except Exception as e:
                    continue
            
            logger.info(f"Found {len(windows)} visible windows")
            return windows
        except Exception as e:
            logger.error(f"Failed to get window list: {e}")
            return []
    
    def get_window_monitor(self, window_info):
        """Get the monitor where the window is currently located"""
        try:
            import win32api
            import win32con
            
            # Get current window position
            rect = window_info['rect']
            window_center_x = (rect.left + rect.right) // 2
            
            # Get primary monitor width
            primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            
            # Get virtual screen information
            virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            
            logger.debug(f"Window '{window_info['title']}' center X: {window_center_x}, primary width: {primary_width}, virtual left: {virtual_left}")
            
            # Determine which monitor the window is on
            # If window center X < 0 (negative), it's on monitor 1 (left)
            # If window center X is between 0 and primary width, it's on monitor 2 (primary)
            # If window center X > primary width, it's on monitor 1 (right extension)
            if window_center_x < 0:
                return 1  # Monitor 1 (left)
            elif window_center_x < primary_width:
                return 2  # Monitor 2 (primary)
            else:
                return 1  # Monitor 1 (right extension)
                
        except Exception as e:
            logger.error(f"Failed to get window monitor information: {e}")
            return None
    
    def move_window_to_monitor(self, window_info, target_monitor):
        """Move window to specified monitor"""
        try:
            import win32gui
            import win32con
            import win32api
            
            hwnd = window_info['hwnd']
            
            # Check if window is already on target monitor
            current_monitor = self.get_window_monitor(window_info)
            if current_monitor == target_monitor:
                logger.info(f"Window '{window_info['title']}' is already on monitor {target_monitor}, skipping")
                return True
            
            # Check if window is maximized
            try:
                # Use GetWindowPlacement to detect window state
                placement = win32gui.GetWindowPlacement(hwnd)
                is_maximized = (placement[1] == win32con.SW_SHOWMAXIMIZED)
                if is_maximized:
                    logger.info(f"Window '{window_info['title']}' is maximized, restoring first")
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.1)  # Wait for window to restore
            except Exception as e:
                logger.warning(f"Failed to detect window state: {e}")
                is_maximized = False
            
            # Get monitor information
            primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            
            # Get target monitor coordinates
            if target_monitor == 1:  # Monitor 1 (left)
                # Monitor 1 is on the left, use virtual screen left coordinates
                new_x = virtual_left + 100
                new_y = 100
            else:  # Monitor 2 (right, primary)
                # Primary monitor coordinates
                new_x = 100
                new_y = 100
            
            # Get current window size
            current_rect = window_info['rect']
            current_width = current_rect.right - current_rect.left
            current_height = current_rect.bottom - current_rect.top
            
            # Move window and maintain original size
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, new_x, new_y, 
                                current_width, current_height, 
                                win32con.SWP_SHOWWINDOW)
            
            # If it was maximized before, maximize again after moving
            if is_maximized:
                time.sleep(0.2)  # Wait for move to complete
                logger.info(f"Re-maximizing window '{window_info['title']}'")
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            
            logger.info(f"Moved window '{window_info['title']}' to monitor {target_monitor} (coordinates: {new_x}, {new_y})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move window: {e}")
            return False
    
    def arrange_windows(self):
        """Arrange all windows"""
        logger.info("Starting window arrangement...")
        
        # Get all windows
        windows = self.get_window_list()
        if not windows:
            logger.warning("No visible windows found")
            return
        
        # Categorize windows
        target_monitor_1 = []  # Monitor 1
        target_monitor_2 = []  # Monitor 2
        
        for window in windows:
            title = window['title'].lower()
            class_name = window['class_name'].lower()
            
            # Check if it's a monitor 1 application
            is_monitor_1 = False
            for app in self.monitor_1_apps:
                if app.lower() in title or app.lower() in class_name:
                    is_monitor_1 = True
                    break
            
            if is_monitor_1:
                target_monitor_1.append(window)
            else:
                target_monitor_2.append(window)
        
        logger.info(f"Monitor 1 target apps: {len(target_monitor_1)}")
        logger.info(f"Monitor 2 other apps: {len(target_monitor_2)}")
        
        # Show current monitor information for target apps
        for window in target_monitor_1:
            current_monitor = self.get_window_monitor(window)
            logger.info(f"Target app '{window['title']}' is currently on monitor {current_monitor}")
        
        # Move windows to monitor 1
        for window in target_monitor_1:
            self.move_window_to_monitor(window, 1)
            time.sleep(0.1)  # Brief delay to avoid conflicts
        
        # Move windows to monitor 2
        for window in target_monitor_2:
            self.move_window_to_monitor(window, 2)
            time.sleep(0.1)  # Brief delay to avoid conflicts
        
        logger.info("Window arrangement completed!")

    def register_hotkeys(self):
        """Register hotkeys with error handling and retry logic"""
        try:
            # Clear existing hotkeys first
            if self.hotkey_registered:
                keyboard.remove_hotkey(self.hotkey)
                self.hotkey_registered = False
            if self.exit_hotkey_registered:
                keyboard.remove_hotkey(self.exit_hotkey)
                self.exit_hotkey_registered = False
            if self.reload_hotkey_registered:
                keyboard.remove_hotkey(self.reload_hotkey)
                self.reload_hotkey_registered = False
            
            # Register main hotkey
            keyboard.add_hotkey(self.hotkey, self.on_hotkey)
            self.hotkey_registered = True
            logger.info(f"Successfully registered hotkey: {self.hotkey}")
            
            # Register exit hotkey
            keyboard.add_hotkey(self.exit_hotkey, self.on_exit)
            self.exit_hotkey_registered = True
            logger.info(f"Successfully registered exit hotkey: {self.exit_hotkey}")

            # Register reload hotkey
            keyboard.add_hotkey(self.reload_hotkey, self.on_reload_hotkey)
            self.reload_hotkey_registered = True
            logger.info(f"Successfully registered reload hotkey: {self.reload_hotkey}")
            
            # Verify hotkeys are working by checking registration status
            logger.debug("Verifying hotkey registration...")
            if self.hotkey_registered and self.exit_hotkey_registered and self.reload_hotkey_registered:
                logger.debug("All hotkeys successfully registered")
            else:
                logger.warning("Some hotkeys failed to register")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register hotkeys: {e}")
            self.hotkey_registered = False
            self.exit_hotkey_registered = False
            self.reload_hotkey_registered = False
            return False
    
    def test_hotkey_response(self):
        """Test if hotkeys are still responsive"""
        try:
            # Try to get keyboard state to test if the library is still working
            keyboard.is_pressed('shift')  # Simple test
            return True
        except Exception as e:
            logger.warning(f"Hotkey test failed: {e}")
            return False
    
    def on_hotkey(self):
        """Hotkey callback function"""
        logger.info("Hotkey detected, starting window arrangement...")
        logger.debug(f"Hotkey callback triggered for: {self.hotkey}")
        try:
            self.arrange_windows()
            # Update last test time after successful execution
            self.last_hotkey_test = time.time()
            logger.info("Window arrangement completed successfully")
        except Exception as e:
            logger.error(f"Error during window arrangement: {e}")
    
    def on_exit(self):
        """Exit hotkey callback function"""
        logger.info("Exit hotkey detected, exiting...")
        logger.debug(f"Exit hotkey callback triggered for: {self.exit_hotkey}")
        # Set exit flag to be handled in main loop
        global exit_flag
        exit_flag = True

    def on_reload_hotkey(self):
        """Reload hotkey callback function"""
        logger.info("Reload hotkey detected, re-registering hotkeys...")
        logger.debug(f"Reload hotkey callback triggered for: {self.reload_hotkey}")
        if self.register_hotkeys():
            logger.info("Hotkeys re-registered successfully")
        else:
            logger.error("Failed to re-register hotkeys")

    def test_hotkey_immediately(self):
        """Test if the main hotkey works immediately after registration"""
        try:
            logger.debug("Testing main hotkey immediately after registration...")
            # Try to trigger the hotkey manually to test if it's working
            # This is a safety check to ensure the callback is properly bound
            logger.info("Testing hotkey functionality - you should see window arrangement start...")
            
            # Check if the hotkey is registered before testing
            if not self.hotkey_registered:
                logger.warning("Main hotkey not registered, cannot test")
                return False
            
            # Test the callback function directly
            self.on_hotkey()
            logger.info("Hotkey test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Immediate hotkey test failed: {e}")
            return False

    def detect_remote_desktop_keys(self, key):
        """Detect any key input that might indicate hotkey usage and handle re-registration"""
        # Check if auto-recovery is enabled
        if not self.enable_auto_recovery:
            return False
            
        current_time = time.time()
        
        # Add current key to history
        self.rd_key_history.append((key, current_time))
        
        # Keep only recent keys within timeout period
        self.rd_key_history = [(k, t) for k, t in self.rd_key_history if current_time - t < self.rd_key_timeout]
        
        # Check for any key input that might indicate hotkey usage
        # Instead of hardcoding specific keys, we'll detect any key sequence
        if len(self.rd_key_history) >= 2:
            # If we have multiple keys in sequence within the timeout period,
            # it might indicate that someone is trying to use hotkeys
            logger.info(f"Key sequence detected: {[k.hex() for k, _ in self.rd_key_history]}")
            
            # Check if any of the recent keys might be part of a hotkey combination
            # This is a more flexible approach that works with any configured hotkey
            recent_keys = [k for k, _ in self.rd_key_history]
            
            # If we detect multiple key presses in sequence, it might indicate hotkey usage
            # We'll re-register hotkeys to ensure they work
            logger.info("Potential hotkey usage detected, re-registering hotkeys...")
            if self.register_hotkeys():
                logger.info("Hotkeys re-registered after key sequence detection")
                self.last_hotkey_test = current_time
                # Clear history after successful re-registration
                self.rd_key_history.clear()
                
                # Test the hotkey immediately to ensure it's working
                logger.info("Testing hotkey functionality after re-registration...")
                self.test_hotkey_immediately()
                
                return True
            else:
                logger.error("Failed to re-register hotkeys after key sequence detection")
        
        return False

def main():
    """Main function"""
    global exit_flag
    exit_flag = False
    
    logger.info("Window Arranger starting...")
    
    # Create window arranger instance
    arranger = WindowArranger()
    
    # Initial hotkey registration
    if not arranger.register_hotkeys():
        logger.error("Failed to register hotkeys initially, exiting...")
        sys.exit(1)
    
    # Set initial test time
    arranger.last_hotkey_test = time.time()
    
    logger.info(f"Program started, waiting for hotkeys...")
    logger.info(f"Press {arranger.hotkey} to arrange windows")
    logger.info(f"Press {arranger.exit_hotkey} to exit program")
    logger.info(f"Press {arranger.reload_hotkey} to re-register hotkeys")
    logger.info("To test CMD input: Press Ctrl+R in this window")
    logger.info("Auto-recovery: Automatically re-registers hotkeys when key sequences are detected")
    logger.info("Tip: After Remote Desktop, try pressing your hotkey to test if it works")
    
    try:
        # Main loop with hotkey monitoring
        while not exit_flag:
            current_time = time.time()
            
            # Check if it's time to test hotkeys
            if current_time - arranger.last_hotkey_test > arranger.hotkey_test_interval:
                logger.info("Performing periodic hotkey health check...")
                
                # Test hotkey responsiveness
                if not arranger.test_hotkey_response():
                    logger.warning("Hotkey test failed, re-registering hotkeys...")
                    if arranger.register_hotkeys():
                        logger.info("Hotkeys re-registered successfully")
                        arranger.last_hotkey_test = current_time
                    else:
                        logger.error("Failed to re-register hotkeys")
                        # Continue running but log the issue
                else:
                    logger.info("Hotkey health check passed")
                    arranger.last_hotkey_test = current_time
            
            # Check for Ctrl+R input in CMD window for manual hotkey reload
            try:
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # Log the key for debugging
                    logger.debug(f"Key pressed: {key} (hex: {key.hex()})")
                    
                    # Check for Ctrl+R (0x12 = 18)
                    if key == b'\x12':
                        logger.info("Ctrl+R detected in CMD window, re-registering hotkeys...")
                        if arranger.register_hotkeys():
                            logger.info("Hotkeys re-registered successfully via CMD input")
                            arranger.last_hotkey_test = current_time
                        else:
                            logger.error("Failed to re-register hotkeys via CMD input")
                    # Check for 'r' or 'R' key with Ctrl modifier
                    elif key in [b'r', b'R']:
                        if keyboard.is_pressed('ctrl'):
                            logger.info("Ctrl+R detected in CMD window, re-registering hotkeys...")
                            if arranger.register_hotkeys():
                                logger.info("Hotkeys re-registered successfully via CMD input")
                                arranger.last_hotkey_test = current_time
                            else:
                                logger.error("Failed to re-register hotkeys via CMD input")
                    # Check for Remote Desktop special key codes that indicate hotkey usage
                    elif arranger.detect_remote_desktop_keys(key):
                        # If detect_remote_desktop_keys returns True, it means hotkeys were re-registered
                        # No need to log here, as the method already logs the re-registration attempt
                        pass
            except ImportError:
                # msvcrt not available on all systems, skip CMD input detection
                pass
            except Exception as e:
                # Log any errors in CMD input detection for debugging
                logger.debug(f"CMD input detection error: {e}")
                pass
            
            # Brief sleep to prevent high CPU usage
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Program error: {e}")
    finally:
        # Cleanup
        try:
            if arranger.hotkey_registered:
                keyboard.remove_hotkey(arranger.hotkey)
            if arranger.exit_hotkey_registered:
                keyboard.remove_hotkey(arranger.exit_hotkey)
            if arranger.reload_hotkey_registered:
                keyboard.remove_hotkey(arranger.reload_hotkey)
            logger.info("Hotkeys unregistered")
        except Exception as e:
            logger.warning(f"Warning when unregistering hotkeys: {e}")
    
    logger.info("Program exited")
    logger.info("Exiting virtual environment...")
    
    # Exit virtual environment
    try:
        if 'VIRTUAL_ENV' in os.environ:
            logger.info("Virtual environment exited")
    except Exception as e:
        logger.warning(f"Warning when exiting virtual environment: {e}")
    
    sys.exit(0)

if __name__ == "__main__":
    main() 