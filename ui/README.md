# Python Program Runner — Local Setup

## Folder structure

```
python_runner/
├── server.py          ← Flask backend
├── index.html         ← Frontend UI (open in browser)
├── requirements.txt
└── scripts/
    ├── camera_test_main.py     ← continuous (Launch / Stop)
    ├── test5_main.py           ← continuous (Launch / Stop)
    ├── calibrate_camera.py     ← interactive (Launch / Stop)
    └── send_to_plc.py          ← one-shot (Run / shows output)
```

## Setup

```bash
pip install -r requirements.txt
```

## Run

1. Start the backend:
   ```bash
   python server.py
   ```

2. Open `index.html` in your browser (double-click).

## How the UI works

| Badge        | Behaviour |
|--------------|-----------|
| `continuous` | Opens an OpenCV window. Click Launch to start, Stop to terminate. |
| `interactive`| Same — you interact via the OpenCV window (clicks, keypresses). |
| `oneshot`    | Runs once, output appears in the panel below. |

## Adding more scripts

Drop any .py file into scripts/ and click Refresh.
To set its type, add an entry in SCRIPT_CONFIG in server.py.
