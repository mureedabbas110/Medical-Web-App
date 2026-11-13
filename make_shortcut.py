import os, sys, subprocess
base = os.path.dirname(os.path.abspath(__file__))
pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
ps = ("$d=[Environment]::GetFolderPath('Desktop');"
      "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($d+'\\Shifa Medical Centre.lnk');"
      "$s.TargetPath='%s';$s.Arguments='\"%s\"';$s.WorkingDirectory='%s';$s.IconLocation='%s';$s.Save()"
      % (pyw, os.path.join(base, "launcher.pyw"), base, os.path.join(base, "static", "img", "logo.ico")))
subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
