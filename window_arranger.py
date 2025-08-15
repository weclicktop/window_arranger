#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
import os
from pywinauto import Desktop, Application
from pywinauto.findwindows import find_windows
import keyboard
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WindowArranger:
    def __init__(self):
        self.desktop = Desktop(backend="uia")
        self.config = self.load_config()
        self.monitor_1_apps = self.config.get("monitor_1_apps", ["opera", "RD Tabs"])
        self.monitor_2_apps = self.config.get("monitor_2_apps", ["*"])
        self.hotkey = self.config.get("hotkey", "ctrl+alt+i")
    
    def load_config(self):
        """Load configuration file"""
        config_file = "config.json"
        default_config = {
            "hotkey": "ctrl+alt+i",
            "monitor_1_apps": ["opera", "RD Tabs"],
            "monitor_2_apps": ["*"]
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

def main():
    """Main function"""
    logger.info("Window Arranger starting...")
    
    # Create window arranger instance
    arranger = WindowArranger()
    
    # Register hotkey
    def on_hotkey():
        logger.info("Hotkey detected, starting window arrangement...")
        arranger.arrange_windows()
    
    # Register configured hotkey
    keyboard.add_hotkey(arranger.hotkey, on_hotkey)
    logger.info(f"Registered hotkey {arranger.hotkey}")
    logger.info(f"Press {arranger.hotkey} to arrange windows")
    
    try:
        # Keep program running, use Ctrl+Alt+Q to exit
        logger.info("Program started, waiting for hotkeys...")
        logger.info(f"Press {arranger.hotkey} to arrange windows")
        logger.info("Press Ctrl+Alt+Q to exit program")
        
        # Register exit hotkey
        exit_flag = False
        
        def exit_program():
            nonlocal exit_flag
            logger.info("Exit signal received, exiting...")
            exit_flag = True
        
        keyboard.add_hotkey('ctrl+alt+q', exit_program)
        
        # Keep program running
        while not exit_flag:
            time.sleep(0.1)  # Reduce delay for better responsiveness
        
        logger.info("Program exiting")
        logger.info("Exiting virtual environment...")
        
        # Exit virtual environment
        try:
            import os
            if 'VIRTUAL_ENV' in os.environ:
                logger.info("Virtual environment exited")
        except Exception as e:
            logger.warning(f"Warning when exiting virtual environment: {e}")
        
        return
        
    except Exception as e:
        logger.error(f"Program error: {e}")
    
    logger.info("Program exited")
    sys.exit(0)

if __name__ == "__main__":
    main() 