"""Native desktop window for Operator.

The interface is a local web app, so "desktop mode" means hosting it in a real
window instead of a browser tab. Three routes are tried in order:

  1. pywebview  — a proper native window using the Edge WebView2 runtime that
                  ships with Windows 10/11 (WebKit on macOS, GTK on Linux).
  2. app mode   — Edge or Chrome launched with --app=, which gives a chromeless
                  window with its own taskbar entry and no address bar.
  3. browser    — an ordinary tab, as a last resort.

Whatever happens, the server is the same one `server.py` runs, so nothing about
the game changes and the pop-out flight window still works.
"""
import os
import subprocess
import sys
import threading
import time
import webbrowser


def _log(msg):
    try:
        from server import _log as slog
        slog(msg)
    except Exception:
        print(msg, flush=True)


def _icon_path():
    from server import HERE
    for p in (os.path.join(HERE, "brand", "favicon.ico"),
              os.path.join(HERE, "static", "brand", "favicon.ico")):
        if os.path.exists(p):
            return p
    return None


def _hide_console():
    """Once a native window is showing, the console behind it is just clutter."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)   # SW_HIDE
    except Exception:
        pass


def _message_box(title, text):
    """Last-ditch error reporting when there is no console to print to."""
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)
            return
    except Exception:
        pass
    print(f"{title}: {text}", flush=True)


# ---------------------------------------------------------------- 1. pywebview
def _run_pywebview(url, on_ready=None):
    import webview

    class Bridge:
        """Exposed to the page as window.pywebview.api"""
        def pop_flight(self):
            webview.create_window("Operator — Flight", url + "/flight", width=520, height=720,
                                  resizable=True, on_top=True, minimized=False)
            return True

        def open_external(self, target):
            webbrowser.open(target)
            return True

        def quit(self):
            for w in webview.windows:
                w.destroy()
            return True

    window = webview.create_window(
        "Operator — Ferry, Cargo & ACMI", url,
        width=1440, height=940, min_size=(1024, 680),
        js_api=Bridge(), text_select=True, confirm_close=False,
    )

    def _ready():
        try:
            window.evaluate_js("window.__operatorDesktop = true; if (window.renderStatus) renderStatus();")
        except Exception:
            pass
        if on_ready:
            on_ready()

    window.events.loaded += _ready
    _log("desktop: using pywebview")
    _hide_console()
    webview.start(private_mode=False, storage_path=_storage_path())
    return True


def _storage_path():
    from server import _home
    p = os.path.join(_home(), "save", "window")
    os.makedirs(p, exist_ok=True)
    return p


# ---------------------------------------------------------------- 2. app mode
_APP_BROWSERS = [
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/microsoft-edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def _run_app_mode(url):
    from server import _home
    profile = os.path.join(_home(), "save", "window")
    os.makedirs(profile, exist_ok=True)
    for raw in _APP_BROWSERS:
        exe = os.path.expandvars(raw)
        if not os.path.exists(exe):
            continue
        args = [exe, f"--app={url}", f"--user-data-dir={profile}",
                "--window-size=1440,940", "--no-first-run", "--no-default-browser-check"]
        try:
            proc = subprocess.Popen(args)
            _log(f"desktop: using app mode via {os.path.basename(exe)}")
            _hide_console()
            proc.wait()          # block until the window closes, then shut the server down
            return True
        except Exception as e:
            _log(f"desktop: app mode failed for {exe}: {e}")
    return False


# ---------------------------------------------------------------- entry point
def run(port, prefer="auto"):
    """Start the window. Returns when the user closes it."""
    url = f"http://127.0.0.1:{port}"

    # wait for the server thread to answer before showing anything
    import urllib.request
    for _ in range(80):
        try:
            urllib.request.urlopen(url + "/api/state", timeout=1).read(1)
            break
        except Exception:
            time.sleep(0.25)

    if prefer in ("auto", "window"):
        try:
            return _run_pywebview(url)
        except ImportError:
            _log("desktop: pywebview not installed")
        except Exception as e:
            _log(f"desktop: pywebview failed ({e!r})")
            if prefer == "window":
                _message_box("Operator", f"The desktop window could not start:\n\n{e}\n\nFalling back to a browser window.")

    if prefer in ("auto", "app"):
        if _run_app_mode(url):
            return True

    _log("desktop: falling back to the default browser")
    webbrowser.open(url)
    # nothing to wait on, so keep the process alive until the user closes the console
    threading.Event().wait()
    return True
