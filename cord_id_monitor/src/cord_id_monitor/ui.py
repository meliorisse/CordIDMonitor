import gi
import datetime
import json
import os
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Pango, Gdk

from .core import DeviceManager, USBDevice
from .utils import format_speed, get_usb_version_label, UpdateChecker
from .version import __version__

# --- CSS Styling ---
# Using GTK4 named colors for theme consistency (Light/Dark mode support)
CSS_DATA = b"""
.title-1 { font-size: 24px; font-weight: bold; color: @theme_fg_color; }
.speed-hero { font-size: 48px; font-weight: 800; color: @accent_color; }
.speed-sub { font-size: 18px; font-weight: bold; color: alpha(@theme_fg_color, 0.7); }

/* Card: Use popover bg color or base color with subtle shadow */
.card { 
    background-color: @popover_bg_color; 
    color: @theme_fg_color;
    border-radius: 12px; 
    border: 1px solid alpha(@borders, 0.5); 
    padding: 24px; 
    box-shadow: 0 2px 8px rgba(0,0,0,0.08); 
}

/* Chart Nodes */
.chart-node { 
    padding: 6px 16px; 
    border-radius: 99px; /* Pill shape */
    font-weight: bold; 
    font-size: 14px;
    color: alpha(@theme_fg_color, 0.5); 
    background-color: alpha(@theme_fg_color, 0.1); 
    border: 1px solid transparent;
    transition: all 0.2s ease; 
}

.chart-node.active { 
    color: @accent_fg_color; 
    background-color: @accent_color; 
    box-shadow: 0 2px 6px alpha(@accent_color, 0.4); 
    transform: scale(1.05);
    font-weight: 900;
}

.chart-line { 
    background-color: alpha(@theme_fg_color, 0.2); 
    min-width: 30px; 
    min-height: 2px; 
    border-radius: 1px; 
    margin-left: 4px;
    margin-right: 4px;
}

/* Status Colors */
.success-status { color: @success_color; font-weight: bold; }
.error-status { color: @error_color; font-weight: bold; }
.dim-label { opacity: 0.5; }

/* Buttons */
.suggested-action { 
    background-color: @accent_color; 
    color: @accent_fg_color; 
    font-weight: bold; 
}

.warning-badge {
    background-color: @warning_color;
    color: @warning_fg_color;
    padding: 4px 12px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 14px;
    margin-bottom: 8px;
}
"""

def apply_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS_DATA)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), 
        provider, 
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

class DeviceRow(Gtk.ListBoxRow):
    """
    A custom row widget for the device list.
    """
    def __init__(self, device: USBDevice):
        super().__init__()
        self.device = device
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name("media-removable")
        icon.set_pixel_size(32)
        box.append(icon)
        
        # Info Box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        # Title: Vendor Model
        lbl_title = Gtk.Label(label=device.get_friendly_name())
        lbl_title.set_halign(Gtk.Align.START)
        lbl_title.add_css_class("heading")
        vbox.append(lbl_title)
        
        # Subtitle: Serial | Bus Info
        meta_text = f"Bus {device.bus_num} Port {device.sys_name}"
        if device.serial:
            meta_text += f" | S/N: {device.serial}"
        
        lbl_meta = Gtk.Label(label=meta_text)
        lbl_meta.set_halign(Gtk.Align.START)
        lbl_meta.add_css_class("caption")
        lbl_meta.set_opacity(0.7)
        vbox.append(lbl_meta)
        
        box.append(vbox)
        self.set_child(box)

class USBVersionChart(Gtk.Box):
    """
    Horizontal chart of USB speed tiers.
    """
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        
        # Nodes
        self.nodes = {}
        # We now use speed-based categories for the chart nodes as they are more descriptive
        # than the protocol version numbers.
        tiers = [
            (" 2.0 ", "480"), 
            (" 5G ", "5000"), 
            (" 10G ", "10000"), 
            (" 20G ", "20000"), 
            (" 40G ", "40000"),
            (" 80G ", "80000")
        ]
        
        for i, (label, key) in enumerate(tiers):
            if i > 0:
                line_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                line_box.set_valign(Gtk.Align.CENTER)
                line = Gtk.Box()
                line.add_css_class("chart-line")
                line.set_size_request(15, 2)
                line_box.append(line)
                self.append(line_box)
                
            lbl = Gtk.Label(label=label)
            lbl.add_css_class("chart-node")
            self.append(lbl)
            self.nodes[key] = lbl

    def set_active_speed(self, speed_mbps_str: str):
        # Reset all
        for node in self.nodes.values():
            node.remove_css_class("active")
            
        if not speed_mbps_str or speed_mbps_str == "N/A":
            return

        # Direct match for standard speeds
        if speed_mbps_str in self.nodes:
            self.nodes[speed_mbps_str].add_css_class("active")
        else:
            # Fallback for non-standard speeds (highlight nearest lower)
            try:
                val = int(speed_mbps_str)
                if val < 5000: self.nodes["480"].add_css_class("active")
                elif val < 10000: self.nodes["5000"].add_css_class("active")
                elif val < 20000: self.nodes["10000"].add_css_class("active")
                elif val < 40000: self.nodes["20000"].add_css_class("active")
                elif val < 80000: self.nodes["40000"].add_css_class("active")
                else: self.nodes["80000"].add_css_class("active")
            except:
                pass


class MonitoringPage(Gtk.Box):
    """
    The dashboard showing live stats for a specific device.
    """
    def __init__(self, stop_callback, history_cache: dict, save_callback):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.history_cache = history_cache
        self.save_callback = save_callback
        # Apply CSS for this window context
        apply_css()
        
        self.stop_callback = stop_callback
        self.current_target_id = None
        
        # --- Top Bar (Status) ---
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top_bar.set_margin_top(16)
        top_bar.set_margin_start(16)
        top_bar.set_margin_end(16)
        
        btn_back = Gtk.Button.new_from_icon_name("go-previous")
        btn_back.connect("clicked", self.on_stop_clicked)
        top_bar.append(btn_back)
        
        self.lbl_status = Gtk.Label(label="Disconnected")
        self.lbl_status.add_css_class("title-1")
        top_bar.append(self.lbl_status)
        
        self.append(top_bar)
        
        # --- Main Content (Scrollable) ---
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.append(scrolled)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content_box.set_margin_top(20)
        content_box.set_margin_bottom(20)
        content_box.set_margin_start(30)
        content_box.set_margin_end(30)
        scrolled.set_child(content_box)
        
        # 1. Device Header Card
        self.card_device = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.card_device.add_css_class("card")
        
        self.lbl_dev_name = Gtk.Label(label="Device Name")
        self.lbl_dev_name.add_css_class("title-1")
        self.lbl_dev_name.set_halign(Gtk.Align.CENTER)
        self.card_device.append(self.lbl_dev_name)
        
        self.lbl_dev_id = Gtk.Label(label="VID:PID")
        self.lbl_dev_id.set_opacity(0.6)
        self.card_device.append(self.lbl_dev_id)
        
        content_box.append(self.card_device)

        # 2. Speed Hero Section
        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        hero_box.set_halign(Gtk.Align.CENTER)
        
        # Link Health Badge (Dynamic)
        self.health_revealer = Gtk.Revealer()
        self.health_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        hero_box.append(self.health_revealer)
        
        self.lbl_health = Gtk.Label(label="")
        self.lbl_health.add_css_class("warning-badge") # We will add this CSS
        self.health_revealer.set_child(self.lbl_health)
        
        self.lbl_speed_val = Gtk.Label(label="--")
        self.lbl_speed_val.add_css_class("speed-hero")
        hero_box.append(self.lbl_speed_val)
        
        self.lbl_speed_sub = Gtk.Label(label="Link Speed")
        self.lbl_speed_sub.add_css_class("speed-sub")
        hero_box.append(self.lbl_speed_sub)
        
        content_box.append(hero_box)

        # 3. Horizontal Chart
        self.chart = USBVersionChart()
        content_box.append(self.chart)

        # 4. Details Grid
        details_frame = Gtk.Frame(label="Connection Details")
        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        details_box.set_margin_top(12)
        details_box.set_margin_bottom(12)
        details_box.set_margin_start(12)
        details_box.set_margin_end(12)
        details_frame.set_child(details_box)
        
        self.rows = {}
        fields = [
            ("USB Version", "version_row"),
            ("Serial Number", "serial_row"),
            ("Bus Location", "bus_row"),
            ("Max Power", "power_row")
        ]
        
        for label, key in fields:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            lbl_key = Gtk.Label(label=f"{label}:")
            lbl_key.set_halign(Gtk.Align.START)
            lbl_key.set_xalign(0)
            lbl_key.set_size_request(140, -1)
            
            lbl_val = Gtk.Label(label="--")
            lbl_val.set_halign(Gtk.Align.START)
            lbl_val.set_selectable(True)
            
            row_box.append(lbl_key)
            row_box.append(lbl_val)
            details_box.append(row_box)
            self.rows[key] = lbl_val
            
        content_box.append(details_frame)


    def on_stop_clicked(self, btn):
        self.current_target_id = None
        self.stop_callback()

    def set_target(self, device: USBDevice):
        self.current_target_id = device.stable_id
        # Set static info immediately
        self.lbl_dev_name.set_text(device.get_friendly_name())
        self.lbl_dev_id.set_text(f"{device.vendor} ({device.vid}:{device.pid})")
        
        self.update_view(device, connected=True)

    def update_view(self, device: USBDevice, connected: bool):
        if connected:
            self.lbl_status.set_text("Connected")
            self.lbl_status.remove_css_class("error-status")
            self.lbl_status.add_css_class("success-status")
            
            # Formatted Speed
            speed_str, speed_label = format_speed(device.speed)
            self.lbl_speed_val.set_text(speed_str)
            self.lbl_speed_sub.set_text(speed_label if speed_label else "Negotiated Link Speed")
            
            # Link Health Check
            # Logic: Update Max Known Speed, then compare current vs Max.
            is_downgraded = False
            known_max = 0
            current_speed = 0
            
            try:
                current_speed = int(device.speed)
                
                # Update History
                if device.stable_id not in self.history_cache:
                    self.history_cache[device.stable_id] = current_speed
                    self.save_callback() # Save new entry
                else:
                    if current_speed > self.history_cache[device.stable_id]:
                        self.history_cache[device.stable_id] = current_speed
                        self.save_callback() # Save improved speed
                
                known_max = self.history_cache[device.stable_id]
                
                # Downgrade Threshold: If current speed is less than what we've seen before
                if current_speed < known_max:
                    is_downgraded = True
                    max_speed_str, max_speed_moniker = format_speed(str(known_max))
                    history_text = f"We have previously observed this device on your system connect at {max_speed_str} ({max_speed_moniker})."
                    
                    if current_speed <= 480 and known_max >= 5000:
                        downgrade_msg = f"Running at legacy USB 2.0 speeds. {history_text}"
                    else:
                        downgrade_msg = f"Running at {speed_str} but {history_text}"

            except Exception as e:
                print(f"Error in health check: {e}")
            
            if is_downgraded:
                self.lbl_health.set_text("⚠️ Link Downgraded")
                self.lbl_health.set_tooltip_text(downgrade_msg)
                self.health_revealer.set_reveal_child(True)
            else:
                self.health_revealer.set_reveal_child(False)
            
            # Chart - Now based on speed
            self.chart.set_active_speed(device.speed)
            
            # Details
            self.rows['version_row'].set_text(get_usb_version_label(device.version))
            self.rows['serial_row'].set_text(device.serial if device.serial else "N/A")
            self.rows['bus_row'].set_text(f"Bus {device.bus_num} | Addr {device.dev_num} | Path {device.sys_name}")
            self.rows['power_row'].set_text(device.max_power)
            
        else:
            self.lbl_status.set_text("Disconnected - Waiting...")
            self.lbl_status.remove_css_class("success-status")
            self.lbl_status.add_css_class("error-status")
            
            # Dim values but keep them
            self.lbl_speed_val.set_opacity(0.5)

class HistoryWindow(Gtk.Window):
    def __init__(self, parent, event_log, device_registry):
        super().__init__(transient_for=parent)
        self.set_title("Device History")
        self.set_default_size(700, 500)
        self.set_modal(True)
        
        self.event_log = event_log
        self.device_registry = device_registry
        
        # Main Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(vbox)
        
        # Tabs
        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        stack_switcher.set_halign(Gtk.Align.CENTER)
        stack_switcher.set_margin_top(10)
        stack_switcher.set_margin_bottom(10)
        vbox.append(stack_switcher)
        vbox.append(stack)
        
        # --- Tab 1: Connection Log ---
        self.listbox_log = Gtk.ListBox()
        self.listbox_log.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox_log.add_css_class("card")
        
        self.log_view = self._create_log_view()
        stack.add_titled(self.log_view, "log", "Connection Log")
        
        # --- Tab 2: Device Registry ---
        self.listbox_registry = Gtk.ListBox()
        self.listbox_registry.set_selection_mode(Gtk.SelectionMode.NONE)
        
        self.registry_view = self._create_registry_view()
        stack.add_titled(self.registry_view, "registry", "Device Registry")

    def _create_log_view(self):
        # Header Row
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_start(10)
        header_box.set_margin_end(10)
        header_box.set_margin_top(10)
        header_box.set_margin_bottom(5)
        
        cols = [("Time", 100), ("Event", 100), ("Device", 250), ("Speed", 120), ("Bus Path", 150)]
        for name, width in cols:
            lbl = Gtk.Label(label=name)
            lbl.set_size_request(width, -1)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_xalign(0)
            lbl.add_css_class("heading")
            header_box.append(lbl)
        
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.append(header_box)
        container.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.listbox_log)
        container.append(scrolled)
        
        # Initial Population (Newest at top)
        for entry in reversed(self.event_log):
            self.add_event_to_list(entry)
            
        return container

    def add_event_to_list(self, entry, at_top=False):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row_box.set_margin_top(8)
        row_box.set_margin_bottom(8)
        row_box.set_margin_start(10)
        
        # Timestamp
        lbl_time = Gtk.Label(label=entry['time'])
        lbl_time.set_size_request(100, -1)
        lbl_time.set_halign(Gtk.Align.START)
        lbl_time.set_xalign(0)
        row_box.append(lbl_time)
        
        # Event
        lbl_evt = Gtk.Label(label=entry['event'])
        lbl_evt.set_size_request(100, -1)
        lbl_evt.set_halign(Gtk.Align.START)
        lbl_evt.set_xalign(0)
        if entry['event'] == 'Connected':
            lbl_evt.add_css_class("success-status")
        elif entry['event'] == 'Disconnected':
            lbl_evt.add_css_class("error-status")
        row_box.append(lbl_evt)
        
        # Device
        lbl_dev = Gtk.Label(label=entry['device_name'])
        lbl_dev.set_size_request(250, -1)
        lbl_dev.set_halign(Gtk.Align.START)
        lbl_dev.set_xalign(0)
        lbl_dev.set_ellipsize(Pango.EllipsizeMode.END)
        lbl_dev.set_tooltip_text(entry['device_name'])
        row_box.append(lbl_dev)
        
        # Speed
        lbl_spd = Gtk.Label(label=entry['speed'])
        lbl_spd.set_size_request(120, -1)
        lbl_spd.set_halign(Gtk.Align.START)
        lbl_spd.set_xalign(0)
        row_box.append(lbl_spd)
        
        # Bus
        lbl_bus = Gtk.Label(label=entry['bus'])
        lbl_bus.set_size_request(150, -1)
        lbl_bus.set_halign(Gtk.Align.START)
        lbl_bus.set_xalign(0)
        row_box.append(lbl_bus)
        
        if at_top:
            self.listbox_log.prepend(row_box)
        else:
            self.listbox_log.append(row_box)

    def refresh_registry(self):
        # Clear
        child = self.listbox_registry.get_first_child()
        while child:
            self.listbox_registry.remove(child)
            child = self.listbox_registry.get_first_child()
            
        # Re-populate
        for stable_id, data in self.device_registry.items():
            self._add_registry_row(stable_id, data)

    def _add_registry_row(self, stable_id, data):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        row.add_css_class("card")
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        row.set_margin_start(16)
        row.set_margin_end(16)
        
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_name = Gtk.Label(label=data['name'])
        lbl_name.set_markup(f"<b>{data['name']}</b>")
        header.append(lbl_name)
        
        lbl_id = Gtk.Label(label=f"ID: {stable_id}")
        lbl_id.set_opacity(0.5)
        header.append(lbl_id)
        row.append(header)
        
        speeds_fmt = []
        for s in sorted(list(data['speeds']), reverse=True):
            s_str, _ = format_speed(str(s))
            speeds_fmt.append(s_str)
        
        lbl_speeds = Gtk.Label(label=f"Observed Speeds: {', '.join(speeds_fmt)}")
        lbl_speeds.set_halign(Gtk.Align.START)
        row.append(lbl_speeds)
        
        lbl_seen = Gtk.Label(label=f"Last Seen: {data['last_seen']}")
        lbl_seen.set_halign(Gtk.Align.START)
        lbl_seen.set_opacity(0.7)
        row.append(lbl_seen)
        
        self.listbox_registry.append(row)

    def _create_registry_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.listbox_registry)
        self.refresh_registry()
        return scrolled

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Cord ID Monitor")
        self.set_default_size(1200, 700) # 1.5x of 800
        
        # Paths
        self.config_dir = os.path.expanduser("~/.config/cord_id_monitor")
        self.history_file = os.path.join(self.config_dir, "history.json")
        
        # Data Structures
        self.device_history = {} # Capability Cache: stable_id -> max_speed_mbps (int)
        self.event_log = [] # List[dict]
        self.device_registry = {} # stable_id -> {name, speeds: set, last_seen}
        self.active_history_window = None
        
        # Load persisted data
        self.load_history()
        
        # Apply global CSS
        apply_css()
        
        self.device_manager = DeviceManager(on_device_event=self.on_device_event_threadsafe)
        
        # Main Layout
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        # self.set_child(self.stack) - Removed in favor of Overlay
        
        # --- Page 1: Selection ---
        self.box_selection = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Header
        header = Gtk.HeaderBar()
        self.set_titlebar(header) # Global header
        
        # History Button
        btn_history = Gtk.Button(label="History")
        btn_history.connect("clicked", self.on_history_clicked)
        header.pack_end(btn_history)
        
        # Split View for Lists - Using Grid for 1:2 ratio
        self.split_grid = Gtk.Grid()
        self.split_grid.set_column_spacing(20)
        self.split_grid.set_vexpand(True)
        self.split_grid.set_margin_top(10)
        self.split_grid.set_margin_bottom(10)
        self.split_grid.set_margin_start(20)
        self.split_grid.set_margin_end(20)
        self.split_grid.set_column_homogeneous(False)
        
        # LEFT: Previously Monitored (1 unit wide)
        self.box_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.box_left.set_hexpand(True)
        
        lbl_left = Gtk.Label(label="Previously Monitored (Connected)")
        lbl_left.add_css_class("heading")
        lbl_left.set_halign(Gtk.Align.START)
        self.box_left.append(lbl_left)
        
        self.scroll_left = Gtk.ScrolledWindow()
        self.scroll_left.set_vexpand(True)
        self.scroll_left.add_css_class("card") # nice border
        self.list_left = Gtk.ListBox()
        self.list_left.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_left.connect("row-selected", self.on_left_selected)
        self.scroll_left.set_child(self.list_left)
        self.box_left.append(self.scroll_left)
        
        # Attach to grid: col=0, row=0, width=1, height=1
        self.split_grid.attach(self.box_left, 0, 0, 1, 1)
        
        # RIGHT: All Devices (2 units wide)
        self.box_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.box_right.set_hexpand(True)
        
        lbl_right = Gtk.Label(label="All Connected Devices")
        lbl_right.add_css_class("heading")
        lbl_right.set_halign(Gtk.Align.START)
        self.box_right.append(lbl_right)
        
        self.scroll_right = Gtk.ScrolledWindow()
        self.scroll_right.set_vexpand(True)
        self.scroll_right.add_css_class("card")
        self.list_right = Gtk.ListBox()
        self.list_right.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_right.connect("row-selected", self.on_right_selected)
        self.scroll_right.set_child(self.list_right)
        self.box_right.append(self.scroll_right)
        
        # Attach to grid: col=1, row=0, width=2, height=1
        self.split_grid.attach(self.box_right, 1, 0, 2, 1)
        
        self.box_selection.append(self.split_grid)
        
        # Action Area
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_margin_top(10)
        action_box.set_margin_bottom(20)
        action_box.set_halign(Gtk.Align.CENTER)
        
        btn_refresh = Gtk.Button(label="Refresh Lists")
        btn_refresh.connect("clicked", lambda x: self.refresh_devices())
        action_box.append(btn_refresh)
        
        btn_monitor = Gtk.Button(label="Monitor Selected")
        btn_monitor.add_css_class("suggested-action")
        btn_monitor.connect("clicked", self.on_monitor_clicked)
        action_box.append(btn_monitor)
        
        self.box_selection.append(action_box)
        
        self.stack.add_named(self.box_selection, "selection")
        
        # --- Page 2: Monitoring ---
        self.page_monitoring = MonitoringPage(
            stop_callback=self.stop_monitoring, 
            history_cache=self.device_history,
            save_callback=self.save_history
        )
        self.stack.add_named(self.page_monitoring, "monitoring")
        
        # --- Update Notification Bar ---
        self.update_bar = Gtk.Revealer()
        self.update_bar.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.update_bar.set_valign(Gtk.Align.END)
        
        upd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        upd_box.add_css_class("card")
        upd_box.set_margin_bottom(20)
        upd_box.set_margin_start(20)
        upd_box.set_margin_end(20)
        upd_box.set_halign(Gtk.Align.CENTER)
        
        lbl_upd = Gtk.Label(label="New version available!")
        self.btn_upd = Gtk.LinkButton(label="Download")
        
        upd_box.append(lbl_upd)
        upd_box.append(self.btn_upd)
        
        self.update_bar.set_child(upd_box)
        
        # Overlay the update bar on top of the stack
        overlay = Gtk.Overlay()
        overlay.set_child(self.stack)
        overlay.add_overlay(self.update_bar)
        self.set_child(overlay)

        # Start
        self.refresh_devices()
        self.device_manager.start_monitoring()
        
        # Check for updates
        UpdateChecker.check_for_updates(__version__, self._on_update_found)

    def _on_update_found(self, version, url):
        def _ui_update():
            self.btn_upd.set_label(f"Download v{version}")
            self.btn_upd.set_uri(url)
            self.update_bar.set_reveal_child(True)
        GLib.idle_add(_ui_update)

    def load_history(self):
        if not os.path.exists(self.history_file):
            return
            
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                
            self.device_history = data.get('device_history', {})
            self.event_log = data.get('event_log', [])
            
            # device_registry needs manual deserialization (list -> set)
            raw_registry = data.get('device_registry', {})
            for stable_id, entry in raw_registry.items():
                entry['speeds'] = set(entry['speeds']) # Convert list back to set
                self.device_registry[stable_id] = entry
                
            print(f"Loaded history from {self.history_file}")
        except Exception as e:
            print(f"Failed to load history: {e}")

    def save_history(self):
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir, exist_ok=True)
                
            # Prepare registry for JSON (set -> list)
            serializable_registry = {}
            for stable_id, entry in self.device_registry.items():
                # Copy entry to avoid modifying the running state
                entry_copy = entry.copy()
                entry_copy['speeds'] = list(entry['speeds'])
                serializable_registry[stable_id] = entry_copy
            
            data = {
                'device_history': self.device_history,
                'event_log': self.event_log,
                'device_registry': serializable_registry
            }
            
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            print(f"Saved history to {self.history_file}")
        except Exception as e:
            print(f"Failed to save history: {e}")

    def on_history_clicked(self, btn):
        if self.active_history_window:
            self.active_history_window.present()
            return
            
        win = HistoryWindow(self, self.event_log, self.device_registry)
        win.connect("close-request", self.on_history_window_closed)
        self.active_history_window = win
        win.present()

    def on_history_window_closed(self, win):
        self.active_history_window = None
        return False # Continue closing

    def on_left_selected(self, listbox, row):
        if row is not None:
            self.list_right.select_row(None) # Deselect right

    def on_right_selected(self, listbox, row):
        if row is not None:
            self.list_left.select_row(None) # Deselect left

    def refresh_devices(self):
        # Clear lists
        for lb in [self.list_left, self.list_right]:
            child = lb.get_first_child()
            while child:
                lb.remove(child)
                child = lb.get_first_child()
            
        devices = self.device_manager.list_devices()
        
        # Populate
        if not devices:
            # Add placeholders
            lbl = Gtk.Label(label="No USB devices connected.")
            lbl.set_margin_top(20)
            self.list_right.append(lbl)
            
            lbl2 = Gtk.Label(label="No known devices connected.")
            lbl2.set_margin_top(20)
            self.list_left.append(lbl2)
            return
        
        # Track seen IDs for left list to avoid duplicates if multiple connections? 
        # Requirement: "only show CONNECTED devices... previously monitored"
        
        count_left = 0
        
        for dev in devices:
            # Always add to Right List (All Devices)
            row_right = DeviceRow(dev)
            self.list_right.append(row_right)
            
            # Check for Left List (History)
            # device_history keys are stable_ids
            if dev.stable_id in self.device_history:
                row_left = DeviceRow(dev)
                self.list_left.append(row_left)
                count_left += 1
                
        if count_left == 0:
             lbl = Gtk.Label(label="No previously monitored devices found.")
             lbl.set_margin_top(20)
             lbl.set_opacity(0.6)
             self.list_left.append(lbl)

    def on_monitor_clicked(self, btn):
        # Determine selection
        target_row = self.list_left.get_selected_row() or self.list_right.get_selected_row()
        
        if target_row and isinstance(target_row, DeviceRow):
            self.page_monitoring.set_target(target_row.device)
            self.stack.set_visible_child_name("monitoring")

    def stop_monitoring(self):
        self.stack.set_visible_child_name("selection")
        self.refresh_devices()

    def on_device_event_threadsafe(self, action, device):
        # Called from background thread -> Marshal to main thread
        GLib.idle_add(self.handle_device_event, action, device)

    def handle_device_event(self, action, device):
        # Debug log
        print(f"DEBUG: Event '{action}' for device '{device.stable_id}'")
        
        # --- History Tracking ---
        # 1. Update Registry
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Helper: Clean Name Logic
        friendly_name = device.get_friendly_name()
        is_unknown_name = "----:----" in friendly_name or "Unknown" in friendly_name
        
        # If we have a better name in registry, use it (especially for remove events)
        if is_unknown_name and device.stable_id in self.device_registry:
            friendly_name = self.device_registry[device.stable_id]['name']

        if device.stable_id not in self.device_registry:
            # Only add to registry if we have a decent name, or if it's the first time
            self.device_registry[device.stable_id] = {
                'name': friendly_name,
                'speeds': set(),
                'last_seen': now_str
            }
        else:
            # Update name if the new one is BETTER (not unknown)
            if not is_unknown_name:
                self.device_registry[device.stable_id]['name'] = friendly_name
        
        # Update last seen
        reg_entry = self.device_registry[device.stable_id]
        reg_entry['last_seen'] = now_str
        
        try:
            spd = int(device.speed)
            reg_entry['speeds'].add(spd)
        except:
            pass
            
        # 2. Add to Event Log
        evt_type = "Changed"
        if action == 'add': evt_type = "Connected"
        elif action == 'remove': evt_type = "Disconnected"
        elif action == 'change': evt_type = "Changed"
        
        # Fix Speed Display for Disconnects
        speed_display = format_speed(device.speed)[0]
        if action == 'remove':
             speed_display = "-"
        
        log_entry = {
            'time': now_str,
            'event': evt_type,
            'device_name': friendly_name, # Use our cleaned name
            'speed': speed_display,
            'bus': f"{device.bus_num}-{device.sys_name}",
            'version': device.version
        }
        self.event_log.append(log_entry)
        
        # Live Update History Window if open
        if self.active_history_window:
            self.active_history_window.add_event_to_list(log_entry, at_top=True)
            self.active_history_window.refresh_registry()
        
        # Auto-save on event to ensure persistence
        self.save_history()
        
        # If in selection mode, maybe auto-refresh?
        if self.stack.get_visible_child_name() == "selection":
            if action in ['add', 'remove']:
                self.refresh_devices()
                
        # If in monitoring mode, check if it affects our target
        elif self.stack.get_visible_child_name() == "monitoring":
            target_id = self.page_monitoring.current_target_id
            
            # Strict Matching Logic
            if device.stable_id == target_id:
                if action == 'add' or action == 'bind' or action == 'change':
                    # Reconnected or Properties Changed!
                    self.page_monitoring.update_view(device, connected=True)
                elif action == 'remove' or action == 'unbind':
                    # Disconnected!
                    self.page_monitoring.update_view(device, connected=False)

        def do_shutdown(self):

            self.save_history()

            self.device_manager.stop_monitoring()

    