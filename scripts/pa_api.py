"""PythonAnywhere Files/Webapps API 얇은 래퍼.

fetch_pythonanywhere.py 와 deploy_pythonanywhere.py 가 공유합니다.
자격증명은 .env(python-decouple) 또는 환경변수에서 읽고, 코드에는 두지 않습니다.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("requests 가 필요합니다:  pip install -r requirements-dev.txt")

BASE_DIR = Path(__file__).resolve().parent.parent

TIMEOUT = 60
RETRIES = 3

#: PythonAnywhere API 는 분당 요청 수를 제한합니다. 파일을 연속으로 올릴 때
#: 429 로 끊기지 않도록 호출 사이에 최소 간격을 둡니다. PA_API_DELAY 로 조정.
MIN_INTERVAL = float(os.environ.get("PA_API_DELAY", "1.6"))
RATE_LIMIT_RETRIES = 8

_last_call = [0.0]


def _throttle():
    elapsed = time.monotonic() - _last_call[0]
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_call[0] = time.monotonic()

#: 훑을 때 통째로 건너뛸 디렉터리/파일 이름
SKIP_NAMES = {
    "__pycache__", ".git", ".github", ".venv", "venv", "node_modules",
    ".pytest_cache", ".ruff_cache", "_pa_sync", "_pa_backup",
}
SKIP_SUFFIXES = (".pyc", ".pyo", ".log")


# --- 설정 -----------------------------------------------------------------

try:
    from decouple import Config, RepositoryEnv

    _env_file = BASE_DIR / ".env"
    _config = Config(RepositoryEnv(_env_file)) if _env_file.exists() else None
except ImportError:  # pragma: no cover
    _config = None


def setting(name, default=None):
    """.env 를 먼저 보고, 없으면 환경변수를 봅니다 (CI 에서는 환경변수)."""
    if _config is not None:
        try:
            return _config(name, default=default)
        except Exception:  # noqa: BLE001
            pass
    return os.environ.get(name, default)


USERNAME = setting("PA_USERNAME")
TOKEN = setting("PA_TOKEN")
HOST = setting("PA_HOST", "www.pythonanywhere.com")  # EU 계정이면 eu.pythonanywhere.com
REMOTE_DIR = setting("PA_REMOTE_DIR")
DOMAIN = setting("PA_DOMAIN") or (f"{USERNAME}.pythonanywhere.com" if USERNAME else None)


def die(message):
    sys.exit(f"오류: {message}")


def connect():
    """(session, base_url) 을 돌려줍니다."""
    if not USERNAME or not TOKEN:
        die(
            "PA_USERNAME / PA_TOKEN 이 설정되지 않았습니다.\n"
            "       로컬이면 .env 에, GitHub Actions 면 저장소 Secrets 에 넣으세요.\n"
            "       토큰 발급: https://www.pythonanywhere.com/account/#api_token"
        )
    session = requests.Session()
    session.headers["Authorization"] = f"Token {TOKEN}"
    return session, f"https://{HOST}/api/v0/user/{USERNAME}"


def request(session, method, url, **kwargs):
    """네트워크 오류와 429 만 재시도합니다. 인증 오류는 즉시 중단합니다.

    업로드는 파일 하나당 한 번씩 호출되므로 429 를 넉넉히 견뎌야 합니다.
    서버가 Retry-After 를 주면 그 값을 따릅니다.
    """
    kwargs.setdefault("timeout", TIMEOUT)
    body = kwargs.get("files") or kwargs.get("data")
    last = None
    net_attempt = 0
    rate_attempt = 0

    while net_attempt < RETRIES and rate_attempt < RATE_LIMIT_RETRIES:
        # 재시도 시 파일 핸들이 이미 소진되었으면 되감습니다.
        if isinstance(body, dict):
            for value in body.values():
                if hasattr(value, "seek"):
                    value.seek(0)

        _throttle()
        try:
            response = session.request(method, url, **kwargs)
        except requests.RequestException as exc:
            last = exc
            net_attempt += 1
            time.sleep(2 ** net_attempt)
            continue

        if response.status_code == 401:
            die("토큰이 거부되었습니다 (401). PA_TOKEN 을 확인하세요.")
        if response.status_code == 403:
            die(f"접근이 거부되었습니다 (403). 계정/호스트를 확인하세요: {HOST}")
        if response.status_code == 429:
            rate_attempt += 1
            wait = response.headers.get("Retry-After")
            delay = float(wait) if wait and wait.isdigit() else min(15 * rate_attempt, 90)
            print(f"    · rate limit — {delay:.0f}초 대기 후 재시도 "
                  f"({rate_attempt}/{RATE_LIMIT_RETRIES})", flush=True)
            time.sleep(delay)
            last = RuntimeError("rate limited")
            continue
        return response

    die(f"{url} 요청 실패: {last}")


# --- Files API ------------------------------------------------------------

def listdir(session, base, remote_path):
    """디렉터리 한 겹의 목록. 파일이거나 없으면 None.

    files/tree/ 는 1000개에서 잘리므로 쓰지 않습니다. files/path/ 는
    디렉터리에 대해 {이름: {'type': ..., 'size': ...}} 를 돌려줍니다.
    """
    response = request(session, "GET", f"{base}/files/path{remote_path}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def walk(session, base, remote_path, recursive=True):
    """원격 절대경로 파일 목록."""
    entries = listdir(session, base, remote_path)
    if entries is None:
        return []

    found = []
    for name, meta in sorted(entries.items()):
        if name in SKIP_NAMES or name.startswith("."):
            continue
        child = f"{remote_path.rstrip('/')}/{name}"
        if meta.get("type") == "directory":
            if recursive:
                found.extend(walk(session, base, child, recursive))
        elif not name.endswith(SKIP_SUFFIXES):
            found.append(child)
    return found


def download(session, base, remote_path, local_path):
    """바이너리 안전 다운로드. 없으면 None, 있으면 바이트 수."""
    response = request(session, "GET", f"{base}/files/path{remote_path}", stream=True)
    if response.status_code == 404:
        return None
    response.raise_for_status()

    local_path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with open(local_path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            handle.write(chunk)
            size += len(chunk)
    return size


def upload(session, base, local_path, remote_path):
    """200 = 덮어씀, 201 = 새로 만듦."""
    with open(local_path, "rb") as handle:
        response = request(
            session, "POST", f"{base}/files/path{remote_path}",
            files={"content": handle},
        )
    response.raise_for_status()
    return response.status_code


# --- Webapps API ----------------------------------------------------------

def list_webapps(session, base):
    response = request(session, "GET", f"{base}/webapps/")
    response.raise_for_status()
    return response.json()


def reload_webapp(session, base, domain):
    response = request(session, "POST", f"{base}/webapps/{domain}/reload/")
    if response.status_code == 404:
        die(
            f"웹앱을 찾을 수 없습니다: {domain}\n"
            "       --list-webapps 로 정확한 도메인을 확인하고 .env 의 PA_DOMAIN 에 넣으세요."
        )
    if response.status_code == 409:
        # 이미 리로드가 진행 중이거나 직전 리로드가 아직 정리되지 않은 상태.
        # 어차피 새 코드가 적재되므로 실패로 취급하지 않습니다.
        print("  · 리로드가 이미 진행 중입니다 (409). 새 코드는 곧 반영됩니다.")
        return {"status": "already-reloading"}
    response.raise_for_status()
    return response.json()


# --- 유틸 ------------------------------------------------------------------

def discover_project_dir(session, base):
    """manage.py 가 있는 원격 폴더를 찾습니다."""
    home = f"/home/{USERNAME}"
    candidates = [f"{home}/about_me", f"{home}/about-me", home]

    for name, meta in (listdir(session, base, home) or {}).items():
        if meta.get("type") == "directory" and name not in SKIP_NAMES:
            path = f"{home}/{name}"
            if path not in candidates:
                candidates.append(path)

    for path in candidates:
        listing = listdir(session, base, path)
        if listing and "manage.py" in listing:
            return path
    return None


def resolve_remote_dir(session, base, override=None):
    remote = override or REMOTE_DIR or discover_project_dir(session, base)
    if not remote:
        die(
            "원격 프로젝트 폴더를 찾지 못했습니다.\n"
            "       --list 로 확인한 뒤 .env 에 PA_REMOTE_DIR 을 설정하세요."
        )
    return remote.rstrip("/")


def human(num_bytes):
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
