from harvesters.core import Harvester
import cv2
import numpy as np
import json
import math

CTI_PATH = r"C:\Program Files\The Imaging Source Europe GmbH\IC4 GenTL Driver for GigEVision Devices\bin\ic4-gentl-gev.cti"
OUTPUT_JSON = "calibration_mm_px.json"

DISPLAY_SCALE = 1  # ---- ZOOM OUT DISPLAY ----

points = []
frozen_frame = None
live_mode = True


def mouse_callback(event, x, y, flags, param):
    global points, frozen_frame

    if frozen_frame is None:
        return

    # Map display coords → original image coords
    x_orig = int(x / DISPLAY_SCALE)
    y_orig = int(y / DISPLAY_SCALE)

    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
        points.append((x_orig, y_orig))
        print(f"📍 Point {len(points)}: ({x_orig}, {y_orig})")

        if len(points) == 2:
            save_calibration()


def save_calibration():
    p1, p2 = points
    px_dist = math.dist(p1, p2)

    real_mm = float(input("👉 Enter real distance in mm: "))

    mm_per_px = real_mm / px_dist
    px_per_mm = 1.0 / mm_per_px

    calib = {
        "image_width": frozen_frame.shape[1],
        "image_height": frozen_frame.shape[0],
        "point1_px": list(p1),
        "point2_px": list(p2),
        "pixel_distance": round(px_dist, 4),
        "real_distance_mm": real_mm,
        "mm_per_pixel": round(mm_per_px, 8),
        "pixel_per_mm": round(px_per_mm, 4)
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(calib, f, indent=4)

    print("\n✅ CALIBRATION SAVED")
    print(f"📁 {OUTPUT_JSON}")
    print(f"mm / pixel  = {mm_per_px:.8f}")
    print(f"pixel / mm = {px_per_mm:.4f}\n")


def main():
    global frozen_frame, live_mode, points

    h = Harvester()
    h.add_cti_file(CTI_PATH)
    h.update()

    if not h.device_info_list:
        print("❌ No camera detected")
        return

    ia = h.create_image_acquirer(0)
    nodemap = ia.remote_device.node_map
    nodemap.PixelFormat.value = "Mono8"

    ia.start_acquisition()

    print("📸 LIVE VIEW")
    print("F = freeze | R = reset | L = live | Q = quit")

    cv2.namedWindow("Calibration")
    cv2.setMouseCallback("Calibration", mouse_callback)

    try:
        while True:
            if live_mode:
                with ia.fetch_buffer(timeout=3000) as buffer:
                    component = buffer.payload.components[0]
                    frame = component.data.copy().reshape(
                        component.height,
                        component.width
                    )
            else:
                frame = frozen_frame

            display = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX)

            # Draw points & line (scale for display)
            for p in points:
                cv2.circle(
                    display,
                    (int(p[0] * DISPLAY_SCALE), int(p[1] * DISPLAY_SCALE)),
                    5,
                    (255,),
                    -1
                )

            if len(points) == 2:
                cv2.line(
                    display,
                    (int(points[0][0] * DISPLAY_SCALE), int(points[0][1] * DISPLAY_SCALE)),
                    (int(points[1][0] * DISPLAY_SCALE), int(points[1][1] * DISPLAY_SCALE)),
                    (255,),
                    2
                )
                px_dist = math.dist(points[0], points[1])
                cv2.putText(
                    display,
                    f"{px_dist:.2f} px",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255,),
                    2
                )

            # ---- ZOOM OUT DISPLAY ----
            display_zoomed = cv2.resize(
                display,
                None,
                fx=DISPLAY_SCALE,
                fy=DISPLAY_SCALE,
                interpolation=cv2.INTER_AREA
            )

            cv2.imshow("Calibration", display_zoomed)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break

            elif key == ord('f') and live_mode:
                frozen_frame = frame.copy()
                points.clear()
                live_mode = False
                print("🧊 Frame frozen")

            elif key == ord('l'):
                frozen_frame = None
                points.clear()
                live_mode = True
                print("▶ Live view resumed")

            elif key == ord('r'):
                points.clear()
                print("🔄 Points reset")

    except Exception as e:
        print("❌ Error:", e)

    finally:
        ia.stop_acquisition()
        ia.destroy()
        h.reset()
        cv2.destroyAllWindows()
        print("🛑 Camera stopped cleanly")


if __name__ == "__main__":
    main()
