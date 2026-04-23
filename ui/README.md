# Python Program Runner — Local Setup

## Folder structure

```
python_runner/
├── server.py          ← Flask backend
├── Web_page.html         ← Frontend UI (open in browser)
└── requirements.txt
    
## Setup

```bash
pip install -r requirements.txt
```

## Run

1. Start the backend:
   ```bash
   python server.py
   ```

2. Open `Web_page.html` in your browser (double-click).

## How the UI works

| Badge        | Behaviour |
|--------------|-----------|
| `continuous` | Opens an OpenCV window. Click Launch to start, Stop to terminate. |
| `interactive`| Same — you interact via the OpenCV window (clicks, keypresses). |
| `oneshot`    | Runs once, output appears in the panel below. |



