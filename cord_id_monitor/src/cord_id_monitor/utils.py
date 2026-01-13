# Helper functions for UI formatting

def format_speed(speed_mbps_str: str) -> str:
    """
    Converts raw Mbps string (e.g. "5000") to human-readable format (e.g. "5 Gbps").
    Returns a tuple of (Formatted String, USB Marketing Label)
    """
    if not speed_mbps_str or speed_mbps_str == "N/A":
        return "Unknown", ""

    try:
        mbps = int(speed_mbps_str)
    except ValueError:
        return speed_mbps_str, ""

    # Specific Matches based on standard signaling rates and marketing names
    if mbps == 1: # 1.5 rounded
        return "1.5 Mbps", "USB 1.1 Low Speed"
    if mbps == 12:
        return "12 Mbps", "USB 1.1 Full Speed"
    if mbps == 480:
        return "480 Mbps", "USB 2.0 High Speed"
    if mbps == 5000:
        return "5 Gbps", "USB 3.2 Gen 1 (SuperSpeed)"
    if mbps == 10000:
        return "10 Gbps", "USB 3.2 Gen 2 (SuperSpeed+)"
    if mbps == 20000:
        return "20 Gbps", "USB 3.2 Gen 2x2 (SuperSpeed+ 20G)"
    if mbps == 40000:
        return "40 Gbps", "USB4 Gen 3x2"
    if mbps == 80000:
        return "80 Gbps", "USB4 Gen 4 (USB4 v2)"
    
    if mbps >= 1000:
        return f"{mbps/1000:g} Gbps", ""
    
    return f"{mbps} Mbps", ""

def get_usb_version_label(version_str: str) -> str:
    """
    Maps sysfs version string to detailed friendly name.
    """
    if not version_str or version_str == "N/A":
        return "Unknown"
    
    v = version_str.strip()
    # Note: version string from kernel reflects the protocol version, not necessarily the speed
    if v.startswith("1.1"): return "USB 1.1"
    if v.startswith("2.0"): return "USB 2.0"
    if v.startswith("2.1"): return "USB 2.1"
    if v.startswith("3.0"): return "USB 3.0"
    if v.startswith("3.1"): return "USB 3.1"
    if v.startswith("3.2"): return "USB 3.2"
    if v.startswith("4.0"): return "USB4"
    
    return f"USB {v}"

import urllib.request
import json
import threading

class UpdateChecker:
    REPO_URL = "https://api.github.com/repos/meliorisse/CordIDMonitor/releases/latest"
    
    @staticmethod
    def check_for_updates(current_version, on_update_found):
        """
        Checks for updates in a background thread.
        :param current_version: The current version string (e.g. "0.1.0")
        :param on_update_found: Callback(latest_version, download_url)
        """
        def _check():
            try:
                # Set User-Agent to avoid 403 Forbidden
                req = urllib.request.Request(
                    UpdateChecker.REPO_URL, 
                    headers={'User-Agent': 'CordIDMonitor'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    tag_name = data.get('tag_name', '').lstrip('v')
                    
                    if UpdateChecker._is_newer(current_version, tag_name):
                        html_url = data.get('html_url', '')
                        on_update_found(tag_name, html_url)
            except Exception as e:
                print(f"Update check failed: {e}")

        threading.Thread(target=_check, daemon=True).start()

    @staticmethod
    def _is_newer(current, latest):
        # specific to version format "x.y.z"
        try:
            c_parts = [int(x) for x in current.split('.')]
            l_parts = [int(x) for x in latest.split('.')]
            
            # Normalize length
            while len(c_parts) < 3: c_parts.append(0)
            while len(l_parts) < 3: l_parts.append(0)
            
            return l_parts > c_parts
        except:
            return False
