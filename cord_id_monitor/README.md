# Cord ID Monitor

A Linux GUI application to monitor USB device connection states and negotiated speeds in real-time.

## Design Overview

### Architecture
The application follows a modular event-driven architecture:

1.  **Device Manager (Backend):**
    *   **Data Source:** Uses `libudev` (via `pyudev`) to query `/sys/bus/usb` for device properties.
    *   **Enumeration:** Scans for devices with `DEVTYPE=usb_device`.
    *   **Event Watcher:** Runs a `pyudev.Monitor` in a background thread to listen for kernel `udev` events (`add`, `remove`, `bind`, `unbind`).
    *   **Identity Matcher:**
        *   **Primary Key:** `ID_SERIAL_SHORT` (Serial Number). This is the gold standard for unique identification.
        *   **Fallback Key:** Composite string of `ID_VENDOR_ID:ID_MODEL_ID` + Physical Port Path (e.g., `1-2.3`). This handles devices without serial numbers by assuming if a device with the same VID/PID appears on the same port, it is likely the same device.

2.  **UI (Frontend):**
    *   Built with **Python** and **GTK4 (PyGObject)**.
    *   **State 1 (Selection):** Displays a list of currently connected devices.
    *   **State 2 (Monitoring):** A dedicated dashboard that updates in real-time based on signals emitted by the Device Manager.
    *   **Thread Safety:** `GLib.idle_add` is used to marshall events from the background udev thread to the main GTK UI thread.

### Data Extraction
*   **Negotiated Speed:** Read from `/sys/bus/usb/devices/.../speed` (e.g., `480`, `5000`, `10000`).
*   **USB Version:** Read from `/sys/bus/usb/devices/.../version`.
*   **Topology:** Derived from the `devpath` attribute (e.g., `bus-port.port`).

## Installation & Running

### Prerequisites
*   **Linux** (Ubuntu 22.04+, Fedora 36+, etc.)
*   **Python 3.8+**
*   **GTK4 Development Libraries** (System level)

### Setup (Ubuntu/Debian)

1.  **Install System Dependencies:**
    ```bash
    sudo apt update
    sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 libgirepository1.0-dev libgirepository-2.0-dev libglib2.0-dev gcc libcairo2-dev pkg-config python3-dev
    ```

2.  **Create Virtual Environment (Optional but Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the App
From the root of the repository:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 src/cord_id_monitor/main.py
```

Alternatively, use the provided script:
```bash
./run_app.sh
```

## Usage
1.  **Select:** Launch the app. You will see a list of connected USB devices.
2.  **Monitor:** Click on a device row, then click "Monitor Selected Device".
3.  **Test:** Unplug the device. The UI will show "Disconnected". Plug it back in (even with a different cable) to the same port (or any port if it has a Serial Number). The UI will automatically reconnect and update the speed stats.

## Limitations
*   **Hubs:** The app currently focuses on endpoint devices. Monitoring a Hub itself is possible but may show aggregate info.
*   **No Serial Number:** Devices without a serial number are tracked by their physical port. If you move a non-serialized device to a different USB port, the app will treat it as a new/different device and will not automatically reconnect.
*   **Permissions:** Standard user permissions are usually sufficient to read USB sysfs attributes. No root required.
*   **Thunderbolt/USB4:** These may appear as PCI devices or abstract USB roots depending on the kernel version. This app tracks the USB interface exposed by the kernel.