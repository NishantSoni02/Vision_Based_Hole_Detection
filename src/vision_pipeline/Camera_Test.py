from harvesters.core import Harvester
import cv2
import numpy as np

CTI_PATH = r"C:\Program Files\The Imaging Source Europe GmbH\IC4 GenTL Driver for GigEVision Devices\bin\ic4-gentl-gev.cti"

def set_node(nodemap, name, value):
    try:
        node = nodemap.get_node(name)
        if node and node.is_writable:
            node.value = value
            print(f"✔ {name} set to {value}")
        else:
            print(f"⚠ {name} not writable or not found")
    except Exception as e:
        print(f"⚠ Failed to set {name}: {e}")

        
def set_roi(nodemap, width, height, offset_x, offset_y):
    try:
        nodemap.OffsetX.value = offset_x
        nodemap.OffsetY.value = offset_y
        nodemap.Width.value = width
        nodemap.Height.value = height
        print(f"🔍 ROI set: {width}x{height} @ ({offset_x}, {offset_y})")
    except Exception as e:
        print("⚠ ROI not supported or invalid:", e)


def main():
    h = Harvester()
    h.add_cti_file(CTI_PATH)
    h.update()

    if not h.device_info_list:
        print("❌ No camera detected")
        return

    print("✅ Camera detected:")
    for i, d in enumerate(h.device_info_list):
        print(f"[{i}] {d.model} | {d.vendor}")

    ia = h.create_image_acquirer(0)
    nodemap = ia.remote_device.node_map

    # -------- Camera configuration --------
    set_node(nodemap, "PixelFormat", "Mono8")
    set_node(nodemap, "ExposureAuto", "Off")
    set_node(nodemap, "ExposureTime", 10000)  # µs
    set_node(nodemap, "GainAuto", "Off")
    set_node(nodemap, "Gain", 0)
    # -------------------------------------

    ia.start_acquisition()
    print("📸 Live stream started (press 'q' to quit)")

    try:
        while True:
            with ia.fetch_buffer(timeout=3000) as buffer:
                component = buffer.payload.components[0]

                image = component.data.reshape(
                    component.height,
                    component.width
                )

                cv2.imshow("DMK 33GX178e - Mono8", image)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except Exception as e:
        print("❌ Streaming error:", e)

    finally:
        ia.stop_acquisition()
        ia.destroy()
        h.reset()
        cv2.destroyAllWindows()
        print("🛑 Camera stopped cleanly")

if __name__ == "__main__":
    main()
