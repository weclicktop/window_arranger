#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import win32api
import win32con
import win32gui
from ctypes import windll

def get_monitor_info():
    """Get detailed monitor information"""
    try:
        # Get primary monitor information
        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        print(f"Primary monitor resolution: {primary_width} x {primary_height}")
        
        # Get virtual screen information (total range of all monitors)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        
        print(f"Virtual screen range: ({virtual_left}, {virtual_top}) - ({virtual_left + virtual_width}, {virtual_top + virtual_height})")
        
        # Get monitor count
        monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)
        print(f"Monitor count: {monitor_count}")
        
        # Enumerate monitors
        def enum_monitor_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = win32gui.GetMonitorInfo(hMonitor)
            print(f"Monitor: {info['Device']}")
            print(f"  Work area: {info['Work']}")
            print(f"  Monitor area: {info['Monitor']}")
            print(f"  Primary monitor: {info['Flags'] & win32con.MONITORINFOF_PRIMARY != 0}")
            print()
            return True
        
        win32gui.EnumDisplayMonitors(None, None, enum_monitor_proc, 0)
        
        return {
            'primary': (primary_width, primary_height),
            'virtual': (virtual_left, virtual_top, virtual_width, virtual_height),
            'count': monitor_count
        }
        
    except Exception as e:
        print(f"Failed to get monitor information: {e}")
        return None

if __name__ == "__main__":
    print("Monitor Information Detection:")
    print("=" * 50)
    get_monitor_info()
    input("Press Enter to exit...") 