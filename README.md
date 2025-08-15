# Window Arranger

A window arrangement tool for Windows 11 that can move specified windows to specified monitors.

## Features

- Configurable hotkey for automatic window arrangement (default: `Ctrl+Alt+I`)
- Move Opera and "RD Tabs" windows to Monitor 1 (left)
- Move all other windows to Monitor 2 (right, primary monitor)
- Support for custom configuration

## Usage

### First Time Setup

1. Double-click `setup_and_run.bat`
2. Wait for virtual environment setup and dependency installation
3. After program starts, press `Ctrl+Alt+I` to arrange windows

### Regular Usage

Double-click `run.bat` to start the program

### After Copying to New Location

If you copy the entire directory to a new location, run `setup_and_run.bat` directly, it will automatically:
- Check if virtual environment is valid
- Recreate if invalid
- Reinstall dependencies

### After Adding to System PATH

If you've added the directory to system environment variable PATH, you can execute from any location:
- `run.bat` - Automatically switches to script directory
- `setup_and_run.bat` - Automatically switches to script directory

**Note**: All batch files automatically switch to the script directory to ensure virtual environment and dependency files can be found correctly.

## File Description

- `window_arranger.py` - Main Python script
- `monitor_detector.py` - Monitor information detection script
- `requirements.txt` - Python dependency package list
- `setup_and_run.bat` - First-time setup and run script
- `run.bat` - Quick start script (automatically detects and fixes virtual environment issues)
- `config.json` - Configuration file (customizable hotkeys, etc.)
- `config_example.json` - Configuration example file

## Requirements

- Windows 11 system
- Python 3.7+
- Program runs in background, listening for hotkeys
- Press `Ctrl+Alt+Q` to exit program

## Configuration

### Hotkey Configuration

You can customize hotkeys in the `config.json` file:

```json
{
    "hotkey": "ctrl+alt+i"
}
```

Supported hotkey formats:
- `ctrl+alt+i` - Ctrl+Alt+I
- `ctrl+shift+a` - Ctrl+Shift+A
- `f12` - F12 key
- `ctrl+1` - Ctrl+1

**Note**: Exit hotkey is fixed as `Ctrl+Alt+Q` and cannot be configured

### Application Configuration

You can configure which applications move to which monitor:

```json
{
    "monitor_1_apps": ["opera", "RD Tabs"],
    "monitor_2_apps": ["*"]
}
```

- `monitor_1_apps`: List of applications to move to Monitor 1
- `monitor_2_apps`: List of applications to move to Monitor 2 (`*` means all other applications)

**Note**: Applications not in `monitor_1_apps` will automatically be moved to Monitor 2. 