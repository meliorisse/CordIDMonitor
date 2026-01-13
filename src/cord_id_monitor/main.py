import sys
import gi
import signal

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib

from .ui import MainWindow

class CordIDMonitorApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.cordidmonitor",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(self)
        self.window.present()

    def do_shutdown(self):
        if self.window:
            self.window.do_shutdown()
        super().do_shutdown()

def main():
    # Enable Ctrl+C to quit
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = CordIDMonitorApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
