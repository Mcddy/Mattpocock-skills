"""Desktop launcher for a forge app (Release tier): one double-click opens the app in its own window.

It starts the app's local server on a free 127.0.0.1 port, waits until it answers, opens a native window
(pywebview, which uses Microsoft Edge WebView2 on Windows 10 and 11) or, if that is missing, the default
browser with a small "running" window that has Open and Quit buttons. Closing the app stops the server.
Data lives in the user's own app-data folder, never beside the EXE. A second launch reuses the running copy.

Copy this file into the app's release/ folder and fill in CONFIG. The server module must have
main(argv) that runs until stopped and accepts --port N (forge's reference apps do).

Usage:
  python launcher.py              run the app (what the EXE does)
  python launcher.py --self-test  start the server, check it answers, stop it, exit 0 (used by build checks)
  python launcher.py --no-window  start the server and print its address; Ctrl+C stops it
  (internal) launcher.py --serve PORT   runs the server itself; the launcher starts this as a child process
Exit codes: 0 fine. 1 the server did not start (the log path is printed and shown). 2 bad arguments.
"""
import json, os, pathlib, signal, socket, subprocess, sys, time, urllib.request, webbrowser

# ----- CONFIG: fill in per app -----
CONFIG = {
    "app_name": "Plant Round",        # window title and folder names
    "app_id": "PlantRound",           # data folder name: %APPDATA%\\<app_id> on Windows
    "server_module": "server",        # a module on the path with main(argv)
    "server_args": ["--db", "{data}/plants.db"],   # {data} becomes the data folder
    "health_path": "/api/health",     # answers 200 when ready
    "window": (1180, 820),            # width, height
    "min_window": (380, 640),
}
# -----------------------------------
VERSION = "forge 3.3.2"
FROZEN = getattr(sys, "frozen", False)
HERE = pathlib.Path(sys._MEIPASS) if FROZEN else pathlib.Path(__file__).resolve().parent  # noqa: SLF001


def data_dir():
    if os.name == "nt":
        base = pathlib.Path(os.environ.get("APPDATA") or pathlib.Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = pathlib.Path.home() / "Library" / "Application Support"
    else:
        base = pathlib.Path(os.environ.get("XDG_DATA_HOME") or pathlib.Path.home() / ".local" / "share")
    d = base / CONFIG["app_id"]
    (d / "logs").mkdir(parents=True, exist_ok=True)
    return d


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def answers(port, timeout=1.0):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, CONFIG["health_path"]), timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def serve(port):
    """Child mode: run the app's server in this process until it is stopped."""
    for p in (HERE, HERE.parent / "app"):
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import importlib
    server = importlib.import_module(CONFIG["server_module"])
    args = [a.replace("{data}", str(data_dir())) for a in CONFIG["server_args"]]
    return server.main(["--port", str(port)] + args)


def start_server(port, log):
    cmd = [sys.executable, "--serve", str(port)] if FROZEN else [sys.executable, str(pathlib.Path(__file__).resolve()), "--serve", str(port)]
    flags = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW: no console window flashes up
    out = open(log, "a", encoding="utf-8")
    out.write("\n--- %s starting on port %d ---\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), port)); out.flush()
    return subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, creationflags=flags)


def stop(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()


def show_error(text):
    print(text, file=sys.stderr)
    try:
        import tkinter, tkinter.messagebox
        root = tkinter.Tk(); root.withdraw()
        tkinter.messagebox.showerror(CONFIG["app_name"], text)
        root.destroy()
    except Exception:  # noqa: BLE001
        pass


def open_ui(url, proc):
    """A native window if pywebview is available, else the browser plus a small Open / Quit window."""
    try:
        import webview
        w, h = CONFIG["window"]
        webview.create_window(CONFIG["app_name"], url, width=w, height=h, min_size=CONFIG["min_window"])
        webview.start()
        return
    except Exception:  # noqa: BLE001  (pywebview missing, or WebView2 missing on this PC)
        pass
    webbrowser.open(url)
    try:
        import tkinter
        root = tkinter.Tk(); root.title(CONFIG["app_name"]); root.resizable(False, False)
        tkinter.Label(root, text="%s is running at %s" % (CONFIG["app_name"], url), padx=18, pady=12).pack()
        row = tkinter.Frame(root, pady=10); row.pack()
        tkinter.Button(row, text="Open", width=10, command=lambda: webbrowser.open(url)).pack(side="left", padx=6)
        tkinter.Button(row, text="Quit", width=10, command=root.destroy).pack(side="left", padx=6)
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()
    except Exception:  # noqa: BLE001  (no tkinter: run until the server stops or Ctrl+C)
        print("%s is running at %s. Press Ctrl+C to stop." % (CONFIG["app_name"], url))
        try:
            if proc:
                proc.wait()
        except KeyboardInterrupt:
            pass


def main(argv):
    if "--version" in argv:
        print(VERSION); return 0
    if argv[:1] == ["--serve"]:
        if len(argv) < 2 or not argv[1].isdigit():
            print("launcher: --serve needs a port", file=sys.stderr); return 2
        return serve(int(argv[1]))
    unknown = [a for a in argv if a not in ("--self-test", "--no-window")]
    if unknown:
        print("launcher: unknown argument %s" % unknown[0], file=sys.stderr); return 2
    d = data_dir(); lock = d / "instance.json"; log = d / "logs" / "server.log"
    if hasattr(signal, "SIGTERM"):                          # a polite stop still stops the server
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    if "--self-test" not in argv and lock.exists():           # one copy at a time: reuse a running server
        try:
            port = json.loads(lock.read_text(encoding='utf-8'))["port"]
            if answers(port):
                open_ui("http://127.0.0.1:%d/" % port, None) if "--no-window" not in argv else print("already running on port %d" % port)
                return 0
        except Exception:  # noqa: BLE001
            pass
    port = free_port(); proc = start_server(port, log)
    try:
        for _ in range(150):                                # up to 15 s
            if answers(port, 0.5):
                break
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        if not answers(port):
            show_error("%s could not start. Details are in %s" % (CONFIG["app_name"], log)); return 1
        url = "http://127.0.0.1:%d/" % port
        if "--self-test" in argv:
            print("self-test: server answered on %s (data in %s)" % (url, d), flush=True); return 0
        lock.write_text(json.dumps({"port": port, "pid": proc.pid}), encoding='utf-8')
        if "--no-window" in argv:
            print("%s on %s (data in %s). Ctrl+C stops it." % (CONFIG["app_name"], url, d), flush=True)
            try:
                proc.wait()
            except KeyboardInterrupt:
                pass
        else:
            open_ui(url, proc)
        return 0
    finally:
        stop(proc)
        try:
            if lock.exists() and json.loads(lock.read_text(encoding='utf-8')).get("port") == port:
                lock.unlink()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
