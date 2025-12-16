from __future__ import annotations
import json
import hashlib
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
import time
from pathlib import Path
APP_DIR_NAME = "MedtronicValidationTool"
LATEST_URL = r"\\hcwda30449e\Validation-Tool\latest.json"
APP_EXE_BASENAME = "validation-ui.exe"
PBI_TOOLS_BASENAME = "pbi-tools.exe"
LAUNCHER_EXE_BASENAME = "ValidationLauncher.exe"
def _get_app_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_DIR_NAME
def _read_local_version(app_dir: Path) -> str:
    ver_file = app_dir / "version.txt"
    if not ver_file.exists():
        return ""
    try:
        return ver_file.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
def _read_runtime(app_dir: Path) -> dict | None:
    p = app_dir / "runtime.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
def _http_get_json(url: str, timeout: float = 0.6) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None
def _http_post(url: str, token: str, timeout: float = 0.8) -> bool:
    try:
        req = urllib.request.Request(url, method="POST", data=b"")
        req.add_header("X-Validation-Token", token)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            _ = r.read()
        return True
    except Exception:
        return False
def _open_browser(url: str) -> None:
    try:
        os.startfile(url)  # type: ignore[attr-defined]
    except Exception:
        pass
def _write_local_version(app_dir: Path, version: str) -> None:
    ver_file = app_dir / "version.txt"
    app_dir.mkdir(parents=True, exist_ok=True)
    ver_file.write_text(version.strip(), encoding="utf-8")
def _download(path_str: str) -> Path:
    src = Path(path_str)
    tmp_dir = Path(tempfile.mkdtemp(prefix="validation_update_"))
    target = tmp_dir / src.name
    target.write_bytes(src.read_bytes())
    return target
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
def _fetch_latest_info() -> dict | None:
    try:
        raw = Path(LATEST_URL).read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception:
        return None
def _kill_all_validation_ui_processes() -> None:
    if os.name != "nt":
        return
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", 
             "Stop-Process -Name 'validation-ui' -Force -ErrorAction SilentlyContinue"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5.0,
        )
        time.sleep(0.5)
    except Exception:
        pass
def ensure_latest(app_dir: Path) -> Path:
    app_dir.mkdir(parents=True, exist_ok=True)
    info = _fetch_latest_info()
    target = app_dir / APP_EXE_BASENAME
    if not info or "version" not in info or "url" not in info:
        return target
    remote_version = str(info["version"]).strip()
    url = str(info["url"]).strip()
    expected_sha = str(info.get("sha256", "")).strip().lower()
    if target.exists() and _read_local_version(app_dir) == remote_version:
        return target
    try:
        downloaded = _download(url)
    except Exception:
        return target
    if expected_sha and _sha256(downloaded).lower() != expected_sha:
        return target
    try:
        tmp = app_dir / (APP_EXE_BASENAME + ".new")
        tmp.write_bytes(downloaded.read_bytes())
        os.replace(tmp, target)
        _write_local_version(app_dir, remote_version)
        for p in app_dir.glob("validation-ui-*.exe"):
            try: 
                p.unlink()
            except Exception: 
                pass
    except Exception:
        return target
    return target
def ensure_pbi_tools(app_dir: Path) -> None:
    target = app_dir / PBI_TOOLS_BASENAME
    if target.exists():
        return
    info = _fetch_latest_info()
    if not info:
        return
    url = str(info.get("pbi_tools_url", "")).strip()
    if not url:
        return
    try:
        downloaded = _download(url)
    except Exception:
        return
    expected_sha = str(info.get("pbi_tools_sha256", "")).strip().lower()
    if expected_sha:
        actual_sha = _sha256(downloaded).lower()
        if actual_sha != expected_sha:
            return
    try:
        if target.exists():
            target.unlink()
        target.write_bytes(downloaded.read_bytes())
    except Exception:
        return
def ensure_launcher_updated(app_dir: Path) -> bool:
    info = _fetch_latest_info()
    if not info:
        return False
    launcher_url = str(info.get("launcher_url", "")).strip()
    if not launcher_url:
        return False
    launcher_sha = str(info.get("launcher_sha256", "")).strip().lower()
    if not launcher_sha:
        return False
    current_launcher = Path(sys.executable)
    if not current_launcher.exists():
        return False
    current_sha = _sha256(current_launcher).lower()
    if current_sha == launcher_sha:
        return False
    try:
        downloaded = _download(launcher_url)
    except Exception:
        return False
    if _sha256(downloaded).lower() != launcher_sha:
        return False
    target = app_dir / LAUNCHER_EXE_BASENAME
    batch_path = app_dir / "update_launcher.bat"
    try:
        target.write_bytes(downloaded.read_bytes())
        batch_content = f"""@echo off
timeout /t 1 /nobreak >nul
copy /y "{target}" "{current_launcher}"
del "{target}"
del "%~f0"
start "" "{current_launcher}"
"""
        batch_path.write_text(batch_content, encoding="utf-8")
        subprocess.Popen(
            ["cmd", "/c", str(batch_path)],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False
def main() -> None:
    app_dir = _get_app_dir()
    app_dir.mkdir(parents=True, exist_ok=True)
    if ensure_launcher_updated(app_dir):
        sys.exit(0)
    info = _fetch_latest_info() or {}
    latest_version = str(info.get("version", "")).strip()
    _kill_all_validation_ui_processes()
    rt = _read_runtime(app_dir)
    if rt:
        host = rt.get("host", "127.0.0.1")
        port = int(rt.get("port", 8000))
        token = str(rt.get("token", "")).strip()
        running_url = f"http://{host}:{port}"
        ping = _http_get_json(running_url + "/ping")
        if ping and ping.get("ok") is True:
            time.sleep(1.0)
            _kill_all_validation_ui_processes()
            time.sleep(0.5)
    exe_path = ensure_latest(app_dir)
    ensure_pbi_tools(app_dir)
    if not exe_path.exists():
        import tkinter.messagebox as mbox
        mbox.showerror(
            "Medtronic Validation Tool",
            "Contact Chey Wade (chey.wade@medtronic.com) for access"
        )
        sys.exit(1)
    subprocess.Popen([str(exe_path)] + sys.argv[1:], cwd=str(app_dir))
    sys.exit(0)
if __name__ == "__main__":
    main()