import os
import subprocess
from pathlib import Path

def test():
    colmap_root = Path("tools/colmap/COLMAP-3.9.1-windows-no-cuda").resolve()
    colmap_exe = str(colmap_root / "bin" / "colmap.exe")
    env = os.environ.copy()
    env["PATH"] = str(colmap_root / "lib") + os.pathsep + env.get("PATH", "")
    env["QT_PLUGIN_PATH"] = str(colmap_root / "lib" / "plugins")
    
    res = subprocess.run([colmap_exe, "help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    print("Direct colmap.exe returncode:", res.returncode)
    first_line = (res.stdout + res.stderr).splitlines()[0] if (res.stdout + res.stderr) else "none"
    print("First line:", first_line)

if __name__ == "__main__":
    test()
