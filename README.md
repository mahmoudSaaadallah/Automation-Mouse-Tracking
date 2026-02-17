# Automation-Mouse-Tracking

A simple Python desktop app to record mouse movement and actions (click/scroll), then replay them with the same timing and path.

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

## Usage

1. Click `Start Recording`.
2. Move the mouse and perform clicks or scrolls.
3. Press `Esc` to stop recording.
4. Click `Replay Last Recording` to run the same mouse path/actions automatically.

## Notes

- The app saves the latest recording to `last_recording.json`.
- The last saved recording is loaded automatically on startup.
- During replay, the app fully controls the mouse according to the recorded events.
