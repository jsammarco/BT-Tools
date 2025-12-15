# BT-Tools

BT-Tools is an early-stage toolkit aimed at finding and tracking nearby Bluetooth devices. The goal is to keep scanning even when devices rotate their MAC addresses and to optionally raise audible alerts (beeps) when specific devices are detected.

## Project status
This repository currently contains project scaffolding only. The core scanning and alerting code has not been published yet. The README outlines the intended direction so contributors know what is planned.

## Planned features
- **Persistent scanning:** Continuously monitor nearby Bluetooth advertisements.
- **Rotating MAC handling:** Track devices even when they randomize their MAC address.
- **Targeted alerts:** Emit configurable beeps when matching devices are found.
- **Filter presets:** Maintain allow/deny lists for common device types.
- **Logging:** Store sightings with timestamps for later analysis.

## Environment assumptions
- Linux with [BlueZ](http://www.bluez.org/) and `bluetoothd` running.
- Python 3.10+ with access to a Bluetooth adapter that supports Low Energy scanning.
- Optional: speakers or a buzzer connected to the host for audible alerts.

## Getting started
1. Clone the repository:
   ```bash
   git clone https://github.com/jsammarco/BT-Tools.git
   cd BT-Tools
   ```
2. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies once the requirements file is available:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the scanner (command to be documented when the implementation lands).

## Development notes
- Contributions should include clear reproduction steps and logs for any Bluetooth adapter issues.
- If you add new command-line tools, document the flags and include a sample output snippet.
- Keep platform-specific instructions (e.g., udev rules) in the README so Linux distributions are covered explicitly.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
