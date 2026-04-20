import snap7
from snap7 import util
import json
import time
import os

PLC_IP = "192.168.0.1"
RACK = 0
SLOT = 1

DB_NUMBER = 1

HOLECOUNT_OFFSET = 0     # DB1.DBW0
BASE_OFFSET = 2          # Holes[1].X
HOLE_SIZE = 8            # X(4) + Y(4)
REAL_SIZE = 4

DATAVALID_BYTE = 178     # DB1.DBX178.0
DATAVALID_BIT = 0

DATA_FILE = "hole_coordinates_mm.json"

def write_real(plc, db, offset, value):
    buf = bytearray(REAL_SIZE)
    util.set_real(buf, 0, float(value))
    plc.db_write(db, offset, buf)

def write_int(plc, db, offset, value):
    buf = value.to_bytes(2, byteorder="big", signed=True)
    plc.db_write(db, offset, buf)

def write_bool(plc, db, byte, bit, value):
    buf = plc.db_read(db, byte, 1)
    util.set_bool(buf, 0, bit, value)
    plc.db_write(db, byte, buf)

plc = snap7.client.Client()
sent_once = False

while True:
    try:
        if not plc.get_connected():
            plc.connect(PLC_IP, RACK, SLOT)
            print("Connected to PLC")

        if sent_once:
            time.sleep(0.5)
            continue

        if not os.path.exists(DATA_FILE):
            time.sleep(0.2)
            continue

        with open(DATA_FILE, "r") as f:
            holes = json.load(f)

        if not holes:
            time.sleep(0.2)
            continue

        hole_count = min(len(holes), 22)

        # ---- WRITE HoleCount ----
        write_int(plc, DB_NUMBER, HOLECOUNT_OFFSET, hole_count)

        # ---- WRITE ALL HOLES ----
        for i in range(hole_count):
            x_offset = BASE_OFFSET + i * HOLE_SIZE
            y_offset = x_offset + 4

            write_real(plc, DB_NUMBER, x_offset, holes[i]["x"])
            write_real(plc, DB_NUMBER, y_offset, holes[i]["y"])

        # ---- SIGNAL DATA VALID ----
        write_bool(plc, DB_NUMBER, DATAVALID_BYTE, DATAVALID_BIT, True)

        print(f"Sent {hole_count} holes to PLC")

        sent_once = True

    except Exception as e:
        print("PLC Error:", e)
        time.sleep(1)
