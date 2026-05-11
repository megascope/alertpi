#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Send an authenticated localhost trigger request")
    parser.add_argument("--url", default="http://127.0.0.1:8000/trigger", help="Trigger endpoint URL")
    parser.add_argument("--token", required=True, help="Bearer token (SIREN_BEARER_TOKEN)")
    parser.add_argument("--duration", type=float, default=1.0, help="Duration in seconds")
    args = parser.parse_args()

    payload = {"duration_seconds": args.duration}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    request = urllib.request.Request(
        args.url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {args.token}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(response.status)
            print(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(exc.code)
        print(exc.read().decode("utf-8"))
        return 1
    except urllib.error.URLError as exc:
        print(f"request failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
