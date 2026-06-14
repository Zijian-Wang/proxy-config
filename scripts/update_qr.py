#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "shadowrocket-qr.png"


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def raw_url_from_remote() -> str:
    remote = run_git(["remote", "get-url", "origin"])
    branch = run_git(["branch", "--show-current"]) or "main"
    if remote.startswith("git@github.com:"):
        repo = remote.removeprefix("git@github.com:").removesuffix(".git")
    elif remote.startswith("https://github.com/"):
        repo = remote.removeprefix("https://github.com/").removesuffix(".git")
    else:
        raise ValueError(f"unsupported origin remote: {remote}")
    return f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/shadowrocket.conf"


def download_qr(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=360x360&format=png&data={quote(url, safe='')}"
    )
    request = Request(qr_url, headers={"User-Agent": "proxy-config-qr/1.0"})
    with urlopen(request, timeout=30) as response:
        data = response.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("downloaded QR response was not a PNG")
    output.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Raw shadowrocket.conf URL")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    url = args.url or raw_url_from_remote()
    download_qr(url, args.output)
    print(f"wrote {args.output}")
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
