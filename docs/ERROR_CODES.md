# DubSync Error Codes Reference

This document describes the error codes used in DubSync crash reports.

## Error Code Format

Error codes are 4-digit numbers organized by category:

| Range | Category |
|-------|----------|
| 1xxx | General Errors |
| 2xxx | File Errors |
| 3xxx | Database Errors |
| 4xxx | UI Errors |
| 5xxx | Plugin Errors |
| 6xxx | Media Errors |
| 7xxx | Import/Export Errors |
| 8xxx | Memory Errors |
| 9xxx | Network Errors |

---

## General Errors (1xxx)

### 1000 - UNKNOWN_ERROR
An error occurred that couldn't be classified.

**Possible causes:**
- Unexpected application state
- Unknown exception type

**What to do:**
- Check the traceback in the crash report
- Report the issue with the full crash report

### 1001 - UNHANDLED_EXCEPTION
An unhandled exception occurred in the application.

**Possible causes:**
- Bug in application code
- Unexpected input data

**What to do:**
- Note what action triggered the error
- Report with crash report attached

### 1002 - ASSERTION_ERROR
An internal assertion failed.

**Possible causes:**
- Internal state inconsistency
- Programming error

**What to do:**
- This is likely a bug - please report it

---

## File Errors (2xxx)

### 2001 - FILE_NOT_FOUND
A required file could not be found.

**Possible causes:**
- File was moved or deleted
- Incorrect file path
- Project references missing file

**What to do:**
- Check if the file exists at the expected location
- Re-link the file if it was moved

### 2002 - FILE_READ_ERROR
Error reading from a file.

**Possible causes:**
- File is corrupted
- File is locked by another application
- Insufficient permissions

**What to do:**
- Close other applications that may be using the file
- Check file permissions
- Try opening a backup

### 2003 - FILE_WRITE_ERROR
Error writing to a file.

**Possible causes:**
- Disk is full
- File is read-only
- Insufficient permissions

**What to do:**
- Check available disk space
- Check file/folder permissions
- Save to a different location

### 2004 - FILE_PERMISSION_ERROR
Insufficient permissions to access a file.

**Possible causes:**
- File is read-only
- No access to the folder
- File owned by different user

**What to do:**
- Check file permissions
- Run as administrator (if appropriate)
- Save to a different location

### 2005 - FILE_CORRUPT
A file appears to be corrupted.

**Possible causes:**
- File was partially written
- Disk errors
- Incompatible file version

**What to do:**
- Try opening a backup
- Check disk for errors
- Re-import the original source file

---

## Database Errors (3xxx)

### 3001 - DATABASE_ERROR
General database error.

**Possible causes:**
- Invalid query
- Data integrity issue

**What to do:**
- Check the crash report for details
- Try creating a new project

### 3002 - DATABASE_CORRUPT
The project database is corrupted.

**Possible causes:**
- Application crashed during save
- Disk errors
- File was modified externally

**What to do:**
- Try opening an auto-save backup
- Create a new project and re-import data

### 3003 - DATABASE_LOCKED
The database file is locked.

**Possible causes:**
- Another instance of DubSync is using the file
- Previous crash left lock file

**What to do:**
- Close other DubSync instances
- Restart the application
- Delete any .lock files next to the project

### 3004 - DATABASE_SCHEMA_ERROR
Database schema version mismatch.

**Possible causes:**
- Project created with different DubSync version
- Corrupted database structure

**What to do:**
- Update DubSync to latest version
- Try opening with the version that created the project

---

## UI Errors (4xxx)

### 4001 - UI_INITIALIZATION_ERROR
Failed to initialize the user interface.

**Possible causes:**
- Missing Qt libraries
- Display driver issues
- Corrupted settings

**What to do:**
- Update graphics drivers
- Reinstall DubSync
- Delete settings file and restart

### 4002 - UI_RENDER_ERROR
Error rendering the user interface.

**Possible causes:**
- Graphics driver bug
- Corrupted theme settings
- Widget state error

**What to do:**
- Update graphics drivers
- Reset theme to default
- Restart the application

### 4003 - WIDGET_ERROR
A UI widget encountered an error.

**Possible causes:**
- Invalid widget state
- Missing resources

**What to do:**
- Restart the application
- Report if issue persists

---

## Plugin Errors (5xxx)

### 5001 - PLUGIN_LOAD_ERROR
Failed to load a plugin.

**Possible causes:**
- Missing plugin dependencies
- Incompatible plugin version
- Corrupted plugin files

**What to do:**
- Disable the problematic plugin
- Reinstall the plugin
- Check plugin requirements

### 5002 - PLUGIN_EXECUTION_ERROR
Error during plugin execution.

**Possible causes:**
- Bug in plugin code
- Invalid input to plugin
- Missing plugin resources

**What to do:**
- Disable the plugin temporarily
- Report to plugin author
- Check plugin documentation

### 5003 - PLUGIN_DEPENDENCY_ERROR
Missing plugin dependency.

**Possible causes:**
- Required package not installed
- Incompatible dependency version

**What to do:**
- Install missing dependencies
- Check plugin requirements.txt
- Use: `pip install -r requirements.txt`

---

## Media Errors (6xxx)

### 6001 - VIDEO_LOAD_ERROR
Failed to load video file.

**Possible causes:**
- Unsupported video format
- Missing video codecs
- Corrupted video file

**What to do:**
- Install FFmpeg
- Convert video to supported format (MP4/H.264)
- Check if video plays in other applications

### 6002 - VIDEO_PLAYBACK_ERROR
Error during video playback.

**Possible causes:**
- Video codec issue
- Memory shortage
- Graphics driver problem

**What to do:**
- Restart the application
- Update graphics drivers
- Convert video to different format

### 6003 - AUDIO_ERROR
Audio playback error.

**Possible causes:**
- Missing audio device
- Unsupported audio format
- Audio driver issue

**What to do:**
- Check audio device is connected
- Update audio drivers
- Convert to supported audio format

---

## Import/Export Errors (7xxx)

### 7001 - SRT_PARSE_ERROR
Error parsing SRT subtitle file.

**Possible causes:**
- Invalid SRT format
- Encoding issues
- Corrupted file

**What to do:**
- Check SRT file format
- Convert to UTF-8 encoding
- Validate with another subtitle editor

### 7002 - SRT_EXPORT_ERROR
Error exporting SRT file.

**Possible causes:**
- Disk full
- Permission denied
- Invalid characters in subtitles

**What to do:**
- Check disk space
- Check folder permissions
- Remove special characters from text

### 7003 - PDF_EXPORT_ERROR
Error exporting PDF.

**Possible causes:**
- Missing fonts
- Very long document
- Disk full

**What to do:**
- Check disk space
- Try exporting fewer cues
- Check for special characters

### 7004 - PROJECT_LOAD_ERROR
Error loading project file.

**Possible causes:**
- Corrupted project file
- Incompatible project version
- Missing linked files

**What to do:**
- Try opening an auto-save
- Check if all linked files exist
- Create new project and re-import

### 7005 - PROJECT_SAVE_ERROR
Error saving project.

**Possible causes:**
- Disk full
- Permission denied
- File locked

**What to do:**
- Check disk space
- Check folder permissions
- Save to different location

---

## Memory Errors (8xxx)

### 8001 - OUT_OF_MEMORY
System ran out of memory.

**Possible causes:**
- Very large project
- Memory leak
- Too many applications running

**What to do:**
- Close other applications
- Restart DubSync
- Work with smaller chunks of data

### 8002 - RESOURCE_EXHAUSTED
System resources exhausted.

**Possible causes:**
- Too many open files
- Thread limit reached
- Handle limit reached

**What to do:**
- Restart the application
- Restart the computer
- Close other applications

---

## Network Errors (9xxx)

### 9001 - NETWORK_ERROR
General network error.

**Possible causes:**
- No internet connection
- Firewall blocking connection
- Server unavailable

**What to do:**
- Check internet connection
- Check firewall settings
- Try again later

### 9002 - DOWNLOAD_ERROR
Error downloading resource.

**Possible causes:**
- Connection interrupted
- Server error
- File not found on server

**What to do:**
- Check internet connection
- Try again later
- Download manually if possible

---

## Reporting Issues

When reporting issues, please include:

1. **Error code** from the crash dialog
2. **Crash report file** from `crash_reports/` folder
3. **Steps to reproduce** - what you were doing when the error occurred
4. **Expected behavior** - what should have happened

Submit issues at: https://github.com/Levi0725/DubSync/issues

Thank you for helping improve DubSync!
