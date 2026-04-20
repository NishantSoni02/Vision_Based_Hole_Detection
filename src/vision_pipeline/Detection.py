from harvesters.core import Harvester
import cv2
import numpy as np
import json
import threading
from datetime import datetime

CTI_PATH = r"C:\Program Files\The Imaging Source Europe GmbH\IC4 GenTL Driver for GigEVision Devices\bin\ic4-gentl-gev.cti"

# ================= USER CONFIG =================
MM_PER_PIXEL = 0.13965118
ROW_TOLERANCE_PX = 25
DISPLAY_SCALE = 0.5

ROI = {
    "x": 300,
    "y": 300,
    "w": 1500,
    "h": 1500
}

OUTPUT_COORDS = "hole_coordinates_mm.json"
# ==============================================

# ── Shared state between camera thread and main thread ──────────────────────
latest_frame   = None
frame_lock     = threading.Lock()
stop_event     = threading.Event()


def set_node(nodemap, name, value):
    try:
        node = nodemap.get_node(name)
        if node and node.is_writable:
            node.value = value
    except:
        pass


def save_hole_coordinates(coords):
    data = {
        "unit": "mm",
        "holes": [
            {"id": idx, "x_mm": round(x, 3), "y_mm": round(y, 3)}
            for idx, x, y in coords
        ]
    }
    with open(OUTPUT_COORDS, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Coordinates saved -> {OUTPUT_COORDS}")


def save_screenshot(image):
    image_name = f"detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    cv2.imwrite(image_name, image)
    print(f"Screenshot saved -> {image_name}")


def detect_holes(frame):
    frame = np.ascontiguousarray(frame.astype(np.uint8))
    output = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    x, y, w, h = ROI["x"], ROI["y"], ROI["w"], ROI["h"]
    roi_img = frame[y:y + h, x:x + w]
    blurred = cv2.GaussianBlur(roi_img, (5, 5), 0)

    holes = []

    # STEP 1: Dark blob detection
    _, thresh = cv2.threshold(blurred, 10, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 150 < area < 3000:
            (cx, cy), radius = cv2.minEnclosingCircle(cnt)
            holes.append({"x_px": cx + x, "y_px": cy + y, "radius_px": radius})

    if len(holes) >= 5:
        method = "BLOB"
    else:
        # STEP 2: Hough circles
        holes = []
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT,
            dp=1.1, minDist=55, param1=110, param2=20,
            minRadius=10, maxRadius=20
        )
        if circles is not None:
            for (xr, yr, r) in circles[0]:
                holes.append({"x_px": xr + x, "y_px": yr + y, "radius_px": r})
        method = "HOUGH"

    # Always draw ROI on the output image
    cv2.rectangle(output, (x, y), (x + w, y + h), (255, 0, 0), 2)

    if not holes:
        print("[STATUS] holes=0 | error=No holes detected in ROI")
        return output, []

    print(f"Detection mode: {method}")

    holes.sort(key=lambda h: h["y_px"])
    rows = []
    for hole in holes:
        for row in rows:
            if abs(row[0]["y_px"] - hole["y_px"]) < ROW_TOLERANCE_PX:
                row.append(hole)
                break
        else:
            rows.append([hole])

    for row in rows:
        row.sort(key=lambda h: h["x_px"])
    rows.reverse()
    ordered = [h for row in rows for h in row]

    x_ref = ROI["x"]
    y_ref = ROI["y"] + ROI["h"]
    coords = []

    for idx, hole in enumerate(ordered, start=1):
        x_mm = (hole["x_px"] - x_ref) * MM_PER_PIXEL
        y_mm = (y_ref - hole["y_px"]) * MM_PER_PIXEL
        coords.append([int(idx), float(x_mm), float(y_mm)])

        cx = int(round(hole["x_px"]))
        cy = int(round(hole["y_px"]))
        radius = int(round(hole["radius_px"]))

        cv2.circle(output, (cx, cy), radius, (0, 255, 0), 2)
        cv2.circle(output, (cx, cy), 2, (0, 0, 255), -1)
        cv2.putText(output, str(idx), (cx - 12, cy - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    print(f"Detected {len(coords)} holes")
    return output, coords


def camera_thread(ia):
    """Runs in background — continuously grabs frames into latest_frame."""
    global latest_frame
    while not stop_event.is_set():
        try:
            with ia.fetch(timeout=3000) as buffer:
                comp = buffer.payload.components[0]
                frame = comp.data.copy().reshape(comp.height, comp.width)
            with frame_lock:
                latest_frame = frame
        except Exception as e:
            if not stop_event.is_set():
                print(f"Capture error: {e}")
            break


def main():
    global latest_frame

    h = Harvester()
    h.add_cti_file(CTI_PATH)
    h.update()

    if not h.device_info_list:
        print("[STATUS] error=No camera detected")
        return

    ia = h.create_image_acquirer(0)
    nodemap = ia.remote_device.node_map

    set_node(nodemap, "PixelFormat", "Mono8")
    set_node(nodemap, "ExposureAuto", "Off")
    set_node(nodemap, "ExposureTime", 10000)
    set_node(nodemap, "GainAuto", "Off")
    set_node(nodemap, "Gain", 0)

    ia.start_acquisition()
    print("[STATUS] running=true | Camera started | Press D to detect")

    # Start camera capture on background thread
    t = threading.Thread(target=camera_thread, args=(ia,), daemon=True)
    t.start()

    # Only pre-create the live window
    cv2.namedWindow("Live", cv2.WINDOW_NORMAL)

    detection_result  = None   # holds the last detection image
    detection_window  = False  # tracks if Detected Holes window is open

    try:
        while True:
            # Get latest frame (non-blocking)
            with frame_lock:
                frame = latest_frame.copy() if latest_frame is not None else None

            if frame is not None:
                overlay = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                rx, ry, rw, rh = ROI["x"], ROI["y"], ROI["w"], ROI["h"]
                cv2.rectangle(overlay, (rx, ry), (rx + rw, ry + rh), (255, 0, 0), 2)
                display = cv2.resize(overlay, None, fx=DISPLAY_SCALE, fy=DISPLAY_SCALE)
                cv2.imshow("Live", display)

            # Keep pumping the detection window every loop so it stays alive
            if detection_window and detection_result is not None:
                cv2.imshow("Detected Holes", detection_result)

            # waitKey pumps ALL OpenCV windows — must be called every loop
            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                break

            elif key == ord('d'):
                with frame_lock:
                    snap = latest_frame.copy() if latest_frame is not None else None
                if snap is not None:
                    result_img, coords = detect_holes(snap)
                    save_hole_coordinates(coords)
                    save_screenshot(result_img)
                    detection_result = cv2.resize(result_img, None,
                                                  fx=DISPLAY_SCALE, fy=DISPLAY_SCALE)
                    # Create window only on first detection
                    if not detection_window:
                        cv2.namedWindow("Detected Holes", cv2.WINDOW_NORMAL)
                        detection_window = True
                    # Structured summary for the UI status panel
                    if coords:
                        print(f"[STATUS] holes={len(coords)} | method=BLOB/HOUGH | saved={OUTPUT_COORDS}")
                    else:
                        print(f"[STATUS] holes=0 | No holes detected in ROI")

            elif key == ord('c') and detection_window:
                cv2.destroyWindow("Detected Holes")
                detection_window  = False
                detection_result  = None

    finally:
        stop_event.set()
        t.join(timeout=3)
        ia.stop_acquisition()
        ia.destroy()
        h.reset()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
