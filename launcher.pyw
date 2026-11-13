import os, sys, socket, threading, time, subprocess, webbrowser, traceback
BASE = os.path.dirname(os.path.abspath(__file__)); os.chdir(BASE)
PORT = 5057; URL = "http://127.0.0.1:%d" % PORT
AUTO_PRINT = False  # True = dialog ke baghair seedha default printer par print (pehle Black Copper ko default bana lein)

def up():
    s = socket.socket(); s.settimeout(0.5)
    try: return s.connect_ex(("127.0.0.1", PORT)) == 0
    finally: s.close()

def find_browser():
    roots = [os.environ.get(k, "") for k in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData")]
    for rel in (r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe"):
        for r in roots:
            p = os.path.join(r, rel)
            if r and os.path.exists(p): return p
    return None

def main():
    started = False
    if not up():
        import app as shifa
        threading.Thread(target=lambda: shifa.app.run(host="127.0.0.1", port=PORT, use_reloader=False, threaded=True), daemon=True).start()
        started = True
        for _ in range(80):
            if up(): break
            time.sleep(0.25)
    exe = find_browser()
    if exe:
        args = [exe, "--app=" + URL, "--user-data-dir=" + os.path.join(BASE, "browser_profile"),
                "--no-first-run", "--window-size=1280,800"]
        if AUTO_PRINT: args.append("--kiosk-printing")
        p = subprocess.Popen(args)
        if started: p.wait()          # window band hote hi app bhi band
    else:
        webbrowser.open(URL)
        while started: time.sleep(3600)

try: main()
except Exception: open(os.path.join(BASE, "launcher.log"), "w").write(traceback.format_exc())
