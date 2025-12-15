import asyncio
import time
from bleak import BleakScanner
import winsound

# Pick your target here
c = "75:56:8C:25:DE:DF"
t = "69:AA:23:FA:6D:62"#jim
t = "52:15:6A:FA:9C:6F"#mark
TARGET_ADDR = t.upper()

# RSSI thresholds (tune these)
IN_RANGE_RSSI = -75    # ~15 ft (adjust for your space)
MAX_RSSI = -65         # very close
MIN_RSSI = -85         # far / unreliable

last_seen_time = 0.0
last_rssi = None

def rssi_to_freq(rssi: int) -> int:
    """Map RSSI to beep frequency (Hz). Stronger signal -> higher pitch."""
    rssi = max(MIN_RSSI, min(MAX_RSSI, rssi))
    norm = (rssi - MIN_RSSI) / (MAX_RSSI - MIN_RSSI)  # 0..1
    return int(400 + norm * 1600)  # 400–2000 Hz

def detection_callback(device, adv):
    global last_seen_time, last_rssi

    addr = getattr(device, "address", "").upper()
    if addr != TARGET_ADDR:
        return

    # RSSI is often on adv on Windows; fallback to device if present
    rssi = getattr(adv, "rssi", None)
    if rssi is None:
        rssi = getattr(device, "rssi", None)

    last_seen_time = time.time()
    last_rssi = rssi

async def beep_loop():
    while True:
        now = time.time()
        present = (now - last_seen_time) < 2.0

        if present and (last_rssi is not None) and (last_rssi >= IN_RANGE_RSSI):
            freq = rssi_to_freq(int(last_rssi))
            await asyncio.to_thread(winsound.Beep, freq, 120)
        else:
            await asyncio.sleep(0.15)

async def status_loop():
    while True:
        now = time.time()
        age = now - last_seen_time if last_seen_time else None
        present = age is not None and age < 2.0

        if present:
            rssi_str = "?" if last_rssi is None else str(last_rssi)
            print(f"[SEEN]  {TARGET_ADDR}  RSSI={rssi_str} dBm  last_seen={age:.1f}s ago")
        else:
            if age is None:
                print(f"[NOT SEEN] {TARGET_ADDR}  (never seen yet)")
            else:
                print(f"[NOT SEEN] {TARGET_ADDR}  last_seen={age:.1f}s ago  last_rssi={last_rssi}")

        await asyncio.sleep(1.0)

async def main():
    scanner = BleakScanner(detection_callback)
    await scanner.start()
    print(f"Watching for {TARGET_ADDR}... (beeps when RSSI >= {IN_RANGE_RSSI} dBm)")
    try:
        await asyncio.gather(beep_loop(), status_loop())
    finally:
        await scanner.stop()

if __name__ == "__main__":
    asyncio.run(main())
