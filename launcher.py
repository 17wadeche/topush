# launcher.py
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
APP_EXE_BASENAME = "validation-ui.exe"  # what we call it locally
PBI_TOOLS_BASENAME = "pbi-tools.exe"
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
    target = tmp_dir / src.name  # keep original filename
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
def _version_newer(v1: str, v2: str) -> bool:
    def parse(v: str):
        return [int(p) for p in v.split(".") if p.isdigit()]
    return parse(v1) > parse(v2)
def ensure_latest(app_dir: Path) -> Path:
    app_dir.mkdir(parents=True, exist_ok=True)
    exe_path = app_dir / APP_EXE_BASENAME
    local_version = _read_local_version(app_dir)
    info = _fetch_latest_info()
    if not info or "version" not in info or "url" not in info:
        return exe_path
    remote_version = str(info["version"]).strip()
    url = str(info["url"]).strip()
    expected_sha = str(info.get("sha256", "")).strip().lower()
    needs_update = (
        not exe_path.exists()
        or not local_version
        or _version_newer(remote_version, local_version)
    )
    if not needs_update:
        return exe_path
    try:
        downloaded = _download(url)
    except Exception:
        return exe_path
    if expected_sha:
        actual_sha = _sha256(downloaded).lower()
        if actual_sha != expected_sha:
            return exe_path if exe_path.exists() else downloaded
    try:
        if exe_path.exists():
            exe_path.unlink()
        downloaded.rename(exe_path)
        _write_local_version(app_dir, remote_version)
    except Exception:
        return exe_path if exe_path.exists() else downloaded
    return exe_path
def ensure_pbi_tools(app_dir: Path) -> None:
    target = app_dir / PBI_TOOLS_BASENAME
    if target.exists():
        return  # already there
    info = _fetch_latest_info()
    if not info:
        return
    url = str(info.get("pbi_tools_url", "")).strip()
    if not url:
        return  # not configured
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
        downloaded.rename(target)
    except Exception:
        return
def main() -> None:
    app_dir = _get_app_dir()
    exe_path = ensure_latest(app_dir)
    ensure_pbi_tools(app_dir)
    info = _fetch_latest_info() or {}
    latest_version = str(info.get("version", "")).strip()
    rt = _read_runtime(app_dir)
    if rt:
        host = rt.get("host", "127.0.0.1")
        port = int(rt.get("port", 8000))
        token = str(rt.get("token", "")).strip()
        running_url = f"http://{host}:{port}"
        ping = _http_get_json(running_url + "/ping")
        if ping and ping.get("ok") is True:
            running_version = str(ping.get("version", "")).strip()
            if latest_version and running_version == latest_version:
                _open_browser(running_url)
                sys.exit(0)
            if token:
                _http_post(running_url + "/shutdown", token=token)
                for _ in range(10):
                    time.sleep(0.2)
                    if not _http_get_json(running_url + "/ping"):
                        break
    if not exe_path.exists():
        import tkinter.messagebox as mbox
        mbox.showerror(
            "Medtronic Validation Tool",
            "Contact Chey Wade (chey.wade@medtronic.com) for access"
        )
        sys.exit(1)
    args = [str(exe_path)] + sys.argv[1:]
    subprocess.Popen(args, cwd=str(app_dir))
    sys.exit(0)
if __name__ == "__main__":
    main()