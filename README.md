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

## Usage

1. Click `Start Recording`.
2. Move the mouse, click/scroll, and use the keyboard.
3. Press `Esc` to stop recording.
4. Set `Replay Count` to the number of loops you want.
5. Click `Replay Last Recording` to run the same mouse + keyboard actions automatically.
6. Press `Esc` during replay to stop replay immediately.

## Notes

- The app saves the latest recording to `last_recording.json`.
- The last saved recording is loaded automatically on startup.
- During replay, the app controls both mouse and keyboard according to the recorded events.
