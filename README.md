# Cord ID Monitor

**Cord ID Monitor** helps you instantly identify your USB cable's actual specifications and performance.

Designed for Linux, this GUI application gives you real-time visibility into your USB connections, verifying if your cables and devices are performing at their advertised speeds or if they have been downgraded due to poor quality or incompatibility.

## What This Does

*   **Real-Time Monitoring:** Detects when devices are plugged in or removed instantly.
*   **Speed Verification:** Displays the actual negotiated link speed (e.g., 480 Mbps, 5 Gbps, 10 Gbps, 40 Gbps) compared to standard USB tiers.
*   **Link Health Check:** Automatically alerts you if a device connects at a slower speed than it is capable of (e.g., a USB 3.0 drive connecting at USB 2.0 speeds).
*   **Device Identification:** identifies devices by Serial Number when available, ensuring unique tracking even if you change ports.
*   **History & Logging:** Keeps a record of every connection event and the speeds observed for each device over time.

---

## Installation

### Option A: Quick Install (Recommended)
Use the automated installer to download the AppImage and add it to your system menu.

```bash
curl -s https://raw.githubusercontent.com/meliorisse/CordIDMonitor/main/install.sh | bash
```

### Option B: Manual AppImage
If you prefer to just download the portable file.

1.  **Download:** [Click here to download the latest `Cord_ID_Monitor-x86_64.AppImage`](https://github.com/meliorisse/CordIDMonitor/releases/latest/download/Cord_ID_Monitor-x86_64.AppImage)
2.  **Make Executable:**
    *   Right-click the downloaded file -> Properties -> Permissions -> Check "Allow executing file as program".
    *   *Or via terminal:* `chmod +x Cord_ID_Monitor-x86_64.AppImage`
3.  **Run:** Double-click the file to start the application.

### Option C: Running from Source
For developers or users who prefer running the Python code directly.

**Prerequisites:**
*   Python 3.8+
*   GTK4 Development Libraries (System Packages)

**Steps:**
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/meliorisse/CordIDMonitor.git
    cd CordIDMonitor
    ```

2.  **Install System Libraries:**
    
    *Ubuntu / Debian:*
    ```bash
    sudo apt update
    sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 libgirepository1.0-dev libcairo2-dev
    ```

    *Fedora:*
    ```bash
    sudo dnf install python3-gobject gtk4 gobject-introspection-devel cairo-gobject-devel
    ```

    *Arch Linux:*
    ```bash
    sudo pacman -S python-gobject gtk4 gobject-introspection
    ```

3.  **Set up Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run:**
    ```bash
    ./run_app.sh
    ```

---

## Uninstalling

If you installed via the **Quick Install** script or **AppImage**, you can remove the application by deleting the following files:

```bash
# Remove AppImage and Desktop Shortcuts
rm ~/.local/bin/cord-id-monitor.AppImage
rm ~/.local/share/applications/cord-id-monitor.desktop
rm ~/.local/share/icons/hicolor/512x512/apps/cord-id-monitor.png

# Update Desktop Cache
update-desktop-database ~/.local/share/applications
```

To remove your history and configuration data:
```bash
rm -rf ~/.config/cord_id_monitor
```

---

## How to Use

1.  **Launch:** Start the application. You will see two lists:
    *   **All Connected Devices:** A live list of everything currently plugged in.
    *   **Previously Monitored:** Devices you have specifically tracked in the past that are currently connected.
2.  **Select & Monitor:** Click on any device in the "All Connected Devices" list and click the **Monitor Selected** button.
3.  **Dashboard:** You are now in the dashboard view.
    *   **Speed Gauge:** Prominently shows the current link speed (e.g., "5 Gbps").
    *   **Connection Details:** View the USB protocol version, serial number, and power usage.
4.  **Test Your Cables:**
    *   Unplug the device. The dashboard will show "Disconnected".
    *   Plug it back in using a different cable or port.
    *   The app will automatically reconnect and update the speed.
    *   **Downgrade Alert:** If the device previously connected at 10 Gbps but now only connects at 480 Mbps, a yellow warning badge "⚠️ Link Downgraded" will appear.

## Limitations
*   **Hubs:** The app focuses on endpoint devices.
*   **Thunderbolt/USB4:** Tracks the USB interface exposed by the kernel.
