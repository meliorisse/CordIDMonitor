import threading
import logging
import time
from typing import Optional, List, Callable, Dict
import pyudev

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class USBDevice:
    """
    Represents a snapshot of a USB Device's state.
    """
    def __init__(self, udev_device: pyudev.Device):
        self._device = udev_device
        self._forced_stable_id = None
        
        # Core Identifiers
        self.sys_path = udev_device.sys_path
        self.sys_name = udev_device.sys_name  # e.g., 1-2.3
        self.device_node = udev_device.device_node
        
        # Attributes
        self.vendor = udev_device.get('ID_VENDOR', 'Unknown')
        self.model = udev_device.get('ID_MODEL', 'Unknown')
        self.serial = udev_device.get('ID_SERIAL_SHORT', None)
        self.vid = udev_device.get('ID_VENDOR_ID', '----')
        self.pid = udev_device.get('ID_MODEL_ID', '----')
        self.bus_num = udev_device.get('BUSNUM', '?')
        self.dev_num = udev_device.get('DEVNUM', '?')
        
        # Topology
        self.dev_path = udev_device.get('DEVPATH', '') # internal kernel path
        
        # Connection Stats (May not be present if disconnected/unbound, but usually cached in udev db)
        # Note: For real-time speed, we often need to read sysfs directly, 
        # as udev properties might be stale until an event fires.
        self.speed = self._read_sysfs_attr('speed')
        self.version = self._read_sysfs_attr('version')
        self.max_power = self._read_sysfs_attr('bMaxPower')
        self.num_interfaces = self._read_sysfs_attr('bNumInterfaces')

    def _read_sysfs_attr(self, attr: str) -> str:
        """Helper to read sysfs attributes directly for freshest data."""
        try:
            # udev_device.sys_path points to /sys/devices/...
            with open(f"{self.sys_path}/{attr}", 'r') as f:
                return f.read().strip()
        except (IOError, FileNotFoundError, AttributeError):
            # Fallback to udev properties if file read fails
            return self._device.properties.get(attr.upper(), 'N/A')

    @property
    def stable_id(self) -> str:
        """
        Returns a unique identifier for this device.
        Strategy:
        1. Serial Number (Best)
        2. Vendor:Model + Physical Port Path (Fallback)
        """
        if self._forced_stable_id:
            return self._forced_stable_id

        if self.serial:
            return f"SERIAL:{self.serial}"
        
        # Fallback: Use VID:PID + sys_name (kernel name roughly maps to topology 1-1.2)
        # We strip the device number parts if they fluctuate, but typically sys_name like '1-2' is bus-port.
        return f"PATH:{self.vid}:{self.pid}:{self.sys_name}"

    def get_friendly_name(self) -> str:
        name = f"{self.vendor} {self.model}".strip()
        if name == "Unknown Unknown":
            name = f"USB Device ({self.vid}:{self.pid})"
        return name.replace('_', ' ')

    def __repr__(self):
        return f"<USBDevice {self.get_friendly_name()} [{self.stable_id}]>"


class DeviceManager:
    """
    Manages USB device enumeration and monitoring.
    """
    def __init__(self, on_device_event: Optional[Callable] = None):
        """
        :param on_device_event: Callback(event_type: str, device: USBDevice)
                                event_type is 'add', 'remove', 'change'
        """
        self.context = pyudev.Context()
        self.monitor = None
        self.monitor_thread = None
        self.running = False
        self.on_device_event = on_device_event
        
        # Internal cache of stable_id -> USBDevice
        # This helps us debounce or track state if needed, 
        # though currently we pass fresh objects on events.
        self._device_cache: Dict[str, USBDevice] = {}
        self._syspath_map: Dict[str, str] = {}

    def list_devices(self) -> List[USBDevice]:
        """Scans current system for USB devices."""
        devices = []
        # Filter for 'usb' subsystem and verify it is a physical device (devtype=usb_device)
        # We skip interfaces (usb_interface) to avoid duplicate entries for the same plug.
        for device in self.context.list_devices(subsystem='usb', DEVTYPE='usb_device'):
            usb_dev = USBDevice(device)
            devices.append(usb_dev)
            self._device_cache[usb_dev.stable_id] = usb_dev
            self._syspath_map[usb_dev.sys_path] = usb_dev.stable_id
        return devices

    def start_monitoring(self):
        """Starts the background udev monitoring thread."""
        if self.running:
            return

        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='usb', device_type='usb_device')
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Cord ID Monitoring started.")

    def stop_monitoring(self):
        """Stops the monitoring thread."""
        self.running = False
        # The thread is daemon, so it will die with the app, 
        # but clean shutdown is nice if we extend this.

    def _monitor_loop(self):
        """Background loop processing udev events."""
        while self.running:
            try:
                # Poll for events. Blocking call with timeout to allow checking self.running
                device = self.monitor.poll(timeout=1.0)
                if device:
                    usb_dev = USBDevice(device)
                    action = device.action # 'add', 'remove', 'change', 'bind', 'unbind'
                    
                    # Handle ID Persistence
                    if action == 'add':
                        self._syspath_map[usb_dev.sys_path] = usb_dev.stable_id
                    elif action == 'remove' or action == 'unbind':
                        if usb_dev.sys_path in self._syspath_map:
                            known_id = self._syspath_map[usb_dev.sys_path]
                            usb_dev._forced_stable_id = known_id
                            if action == 'remove':
                                del self._syspath_map[usb_dev.sys_path]
                    
                    # Log raw event
                    logger.info(f"Monitor Event: {action} on {usb_dev.sys_name} | StableID: {usb_dev.stable_id}")

                    # Update Cache
                    if action == 'add':
                        self._device_cache[usb_dev.stable_id] = usb_dev
                    elif action == 'remove':
                        if usb_dev.stable_id in self._device_cache:
                            del self._device_cache[usb_dev.stable_id]
                    
                    # Notify UI/Listener
                    if self.on_device_event:
                        self.on_device_event(action, usb_dev)
                        
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(1) # Prevent tight loop on error
