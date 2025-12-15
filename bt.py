import asyncio
import time
from bleak import BleakScanner
import os
import csv
import hashlib

# -------------------------
# Globals
# -------------------------
logical_devices = {}       # logical_id -> info
addr_to_logical = {}       # address -> logical_id
logical_order = []         # stable display order
OUI_DB = {}

NEXT_LOGICAL_NUM = 1
ROTATION_TIME_WINDOW_SEC = 20  # MAC rotation merge window

# Common BLE manufacturer IDs
BLE_MANUFACTURERS = {
    0x004C: "Apple",
    0x0006: "Microsoft",
    0x000F: "Broadcom",
    0x0131: "Google",
    0x00E0: "Google",
    0x00FE: "Fitbit",
    0x0157: "Xiaomi",
    0x0075: "Samsung",
    0x0087: "Garmin",
    0x00C7: "Sony",
}

# -------------------------
# Utility
# -------------------------
def clear_console():
    os.system("cls" if os.name == "nt" else "clear")

def short_hash(b: bytes, n=8) -> str:
    return hashlib.sha1(b).hexdigest()[:n]

def fmt_clock(ts):
    return time.strftime("%H:%M:%S", time.localtime(ts)) if ts else ""

# -------------------------
# OUI CSV Loader
# -------------------------
def load_oui_csv(path="oui.csv"):
    if not os.path.exists(path):
        print(f"[WARN] OUI file not found: {path}")
        return

    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            a = row.get("Assignment")
            o = row.get("Organization Name")
            if a and o:
                OUI_DB[a.replace("-", ":").upper()] = o.strip()

    print(f"[OK] Loaded {len(OUI_DB):,} OUI entries")

# -------------------------
# Manufacturer resolution
# -------------------------
def manufacturer_from_adv(adv):
    if adv and getattr(adv, "manufacturer_data", None):
        for mid in adv.manufacturer_data:
            return BLE_MANUFACTURERS.get(mid, f"BLE:0x{mid:04X}")
    return "Unknown"

# -------------------------
# Device classification
# -------------------------
def classify_device(adv):
    parts = ["BLE"]
    if adv and getattr(adv, "manufacturer_data", None):
        parts.append("mfg")
    svc_uuids = getattr(adv, "service_uuids", None) or []
    if svc_uuids:
        parts.append(f"svc:{len(svc_uuids)}")
    try:
        conn = getattr(adv, "connectable", None)
        if conn is True:
            parts.append("conn")
        elif conn is False:
            parts.append("non-conn")
    except Exception:
        pass
    return ",".join(parts)

# -------------------------
# Fingerprinting (NO RSSI for tracking)
# -------------------------
def compute_fingerprint(adv, manufacturer):
    mfg_parts = []
    mdata = getattr(adv, "manufacturer_data", None) or {}
    for mid, blob in sorted(mdata.items(), key=lambda x: x[0]):
        b = bytes(blob) if blob else b""
        # include length + small hash to reduce collisions
        mfg_parts.append(f"{mid:04x}:{len(b)}:{short_hash(b)}")

    svc_uuids = getattr(adv, "service_uuids", None) or []
    svc_uuids_str = ",".join(sorted([u.lower() for u in svc_uuids]))

    sdata = getattr(adv, "service_data", None) or {}
    s_parts = []
    for k, v in sorted(sdata.items(), key=lambda x: x[0].lower()):
        vb = bytes(v) if v else b""
        s_parts.append(f"{k.lower()}:{len(vb)}:{short_hash(vb)}")

    return f"{manufacturer}|mfg:{'|'.join(mfg_parts)}|svc:{svc_uuids_str}|sdata:{'|'.join(s_parts)}"

def alloc_logical_id():
    global NEXT_LOGICAL_NUM
    lid = f"D{NEXT_LOGICAL_NUM:03d}"
    NEXT_LOGICAL_NUM += 1
    return lid

def pick_logical_device(addr, fp, now):
    # Keep existing mapping for an address
    if addr in addr_to_logical:
        return addr_to_logical[addr]

    # Match by fingerprint + recentness only (no RSSI)
    for lid, info in logical_devices.items():
        if info["fingerprint"] == fp and (now - info["last_seen"]) <= ROTATION_TIME_WINDOW_SEC:
            return lid

    return alloc_logical_id()

# -------------------------
# Detection callback
# -------------------------
def detection_callback(device, adv):
    now = time.time()
    addr = getattr(device, "address", "unknown")
    name = getattr(device, "name", "") or ""

    # RSSI location depends on Bleak backend/version
    rssi = getattr(adv, "rssi", None)
    if rssi is None:
        rssi = getattr(device, "rssi", None)

    manufacturer = manufacturer_from_adv(adv)
    dtype = classify_device(adv)
    fp = compute_fingerprint(adv, manufacturer)

    lid = pick_logical_device(addr, fp, now)
    addr_to_logical[addr] = lid

    if lid not in logical_devices:
        logical_devices[lid] = {
            "fingerprint": fp,
            "manufacturer": manufacturer,
            "type": dtype,
            "name": name,
            "first_seen": now,
            "last_seen": now,
            "last_rssi": rssi,
            "addresses": {addr},
            "latest_addr": addr,
        }
        logical_order.append(lid)
    else:
        ld = logical_devices[lid]
        ld["last_seen"] = now
        ld["last_rssi"] = rssi
        ld["latest_addr"] = addr
        ld["addresses"].add(addr)
        ld["manufacturer"] = manufacturer or ld["manufacturer"]
        ld["type"] = dtype or ld["type"]
        if name:
            ld["name"] = name

# -------------------------
# Display
# -------------------------
def print_table(present_window_sec=15):
    now = time.time()
    clear_console()

    print("\nNearby BLE devices (stable order, RSSI shown when available, no removals)")
    print("-" * 180)
    print(
        f"{'#':<3} {'ID':<5} {'PRES':<4} {'RSSI':<6} {'LAST(s)':<7} "
        f"{'LAST@':<8} {'FIRST@':<8} {'#MACs':<5} "
        f"{'LATEST_ADDR':<22} {'MANUFACTURER':<28} {'TYPE':<24} {'NAME':<22}"
    )
    print("-" * 180)

    for idx, lid in enumerate(logical_order, start=1):
        ld = logical_devices[lid]
        age = int(now - ld["last_seen"])
        pres = "YES" if age <= present_window_sec else "NO"
        rssi = "" if ld["last_rssi"] is None else str(ld["last_rssi"])

        print(
            f"{idx:<3} {lid:<5} {pres:<4} {rssi:<6} {age:<7} "
            f"{fmt_clock(ld['last_seen']):<8} {fmt_clock(ld['first_seen']):<8} "
            f"{len(ld['addresses']):<5} {ld['latest_addr']:<22} "
            f"{ld['manufacturer'][:28]:<28} {ld['type'][:24]:<24} "
            f"{(ld['name'] or '')[:22]:<22}"
        )

    print("-" * 180)

# -------------------------
# Main
# -------------------------
async def main():
    load_oui_csv("oui.csv")

    scanner = BleakScanner(detection_callback)
    await scanner.start()

    try:
        while True:
            print_table()
            await asyncio.sleep(1)
    finally:
        await scanner.stop()

if __name__ == "__main__":
    asyncio.run(main())
