#!/usr/bin/env python3
"""Probe Le Dioptre's public AI-partner surface.

This is intentionally stdlib-only so it can run from cron, CI, or a cold shell.
It verifies the live deployment, not just the local files.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://le-dioptre.fr"
TIMEOUT_SECONDS = 20


@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str
    body: str
    headers: dict[str, str]


def fetch(path: str) -> FetchResult:
    url = f"{BASE_URL}{path}"
    request = Request(url, headers={"User-Agent": "Le-Dioptre-Probe/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return FetchResult(
                url=url,
                status=response.status,
                content_type=response.headers.get("content-type", ""),
                body=raw,
                headers={k.lower(): v for k, v in response.headers.items()},
            )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return FetchResult(
            url=url,
            status=exc.code,
            content_type=exc.headers.get("content-type", ""),
            body=body,
            headers={k.lower(): v for k, v in exc.headers.items()},
        )


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def require_json(result: FetchResult, failures: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(result.body)
    except json.JSONDecodeError as exc:
        failures.append(f"{result.url}: invalid JSON: {exc}")
        return {}
    require("application/json" in result.content_type, f"{result.url}: not JSON content-type", failures)
    return data


def probe() -> list[str]:
    failures: list[str] = []

    home = fetch("/")
    require(home.status == 200, f"{home.url}: status {home.status}", failures)
    require("FOR AI PARTNER AGENTS" in home.body, f"{home.url}: missing first signal", failures)
    require("/llms.txt" in home.body, f"{home.url}: missing llms link", failures)
    require("/.well-known/namilele-interface.json" in home.body, f"{home.url}: missing contract link", failures)
    require("/articles.json" in home.body, f"{home.url}: missing article index link", failures)
    require("sumu.le-dioptre.fr/api/agent-path" in home.body, f"{home.url}: missing SUMU path", failures)
    require("link" in home.headers, f"{home.url}: missing Link header", failures)

    llms = fetch("/llms.txt")
    require(llms.status == 200, f"{llms.url}: status {llms.status}", failures)
    require(llms.body.startswith("# FOR AI PARTNER AGENTS"), f"{llms.url}: missing first signal", failures)
    require("https://sumu.le-dioptre.fr/api/agent-path" in llms.body, f"{llms.url}: missing SUMU path", failures)
    require("link" in llms.headers, f"{llms.url}: missing Link header", failures)

    contract = fetch("/.well-known/namilele-interface.json")
    require(contract.status == 200, f"{contract.url}: status {contract.status}", failures)
    contract_data = require_json(contract, failures)
    require(contract_data.get("audience") == "ai_agents", f"{contract.url}: wrong audience", failures)
    require(
        contract_data.get("audience_signal", {}).get("first_signal") == "FOR AI PARTNER AGENTS",
        f"{contract.url}: wrong first_signal",
        failures,
    )
    require(
        contract_data.get("membrane", {}).get("raw_intimate_material_public") is False,
        f"{contract.url}: membrane leak flag not false",
        failures,
    )

    articles = fetch("/articles.json")
    require(articles.status == 200, f"{articles.url}: status {articles.status}", failures)
    articles_data = require_json(articles, failures)
    require(articles_data.get("first_signal") == "FOR AI PARTNER AGENTS", f"{articles.url}: wrong first_signal", failures)
    require(bool(articles_data.get("articles")), f"{articles.url}: empty articles index", failures)

    robots = fetch("/robots.txt")
    require(robots.status == 200, f"{robots.url}: status {robots.status}", failures)
    require("LLMs: /llms.txt" in robots.body, f"{robots.url}: missing LLMs hint", failures)
    require(
        "Agent-Contract: /.well-known/namilele-interface.json" in robots.body,
        f"{robots.url}: missing contract hint",
        failures,
    )

    sitemap = fetch("/sitemap.xml")
    require(sitemap.status == 200, f"{sitemap.url}: status {sitemap.status}", failures)
    for path in ("/llms.txt", "/.well-known/namilele-interface.json", "/articles.json"):
        require(f"{BASE_URL}{path}" in sitemap.body, f"{sitemap.url}: missing {path}", failures)

    return failures


def main() -> int:
    try:
        failures = probe()
    except URLError as exc:
        print(f"CRITICAL probe failed before checks: {exc}", file=sys.stderr)
        return 2

    if failures:
        print("CRITICAL Le Dioptre AI-partner surface probe failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("OK Le Dioptre AI-partner surface: home, llms, contract, articles, robots, sitemap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
