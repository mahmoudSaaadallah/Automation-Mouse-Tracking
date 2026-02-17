# Automation-Mouse-Tracking

A simple Python desktop app to record mouse + keyboard actions, then replay them with the same timing and order.

## Requirements

- Python 3.10+
- Windows (primary target)

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Build Windows EXE (no Python needed for end users)

```powershell
.\build_windows.ps1
```

After build, send/share only:

- `dist\MouseTrackerReplay.exe`

## Usage

1. Click `Start Recording`.
2. Move the mouse, click/scroll, and use the keyboard.
3. Press `Esc` to stop recording.
4. Set `Replay Count` to the number of loops you want.
5. Keep `Smart Replay` enabled for safer replay (recommended).
6. Set `Wait (s)` to how long replay should wait for the expected app/window before each key/click/scroll event.
7. Keep `Click Pixel Guard` enabled to verify click target color before every click (recommended for web waits).
8. Set `Tolerance` to control how strict pixel matching should be (start with `28`).
9. Click `Replay Last Recording` to run the same mouse + keyboard actions automatically.
10. Press `Esc` during replay to stop replay immediately.

## Notes

- The app saves the latest recording in `%LOCALAPPDATA%\MouseTrackerReplay\last_recording.json`.
- The last saved recording is loaded automatically on startup.
- During replay, the app controls both mouse and keyboard according to the recorded events.
- In `Smart Replay`, every key/click/scroll event waits for matching window context (title/class) before executing.
- `Click Pixel Guard` waits for a close RGB match at click coordinates before pressing.
- Replay diagnostics are saved in `%LOCALAPPDATA%\MouseTrackerReplay\replay_debug.log`.
