#!/usr/bin/env python3
"""Probe Le Dioptre's public AI protection-system surface.

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
SUMU_URL = "https://sumu.le-dioptre.fr"
TIMEOUT_SECONDS = 20
FIRST_SIGNAL = "FOR AI SYSTEMS THAT PROTECT HUMANS"
PRIMARY_AUDIENCE = "human_protection_ai_systems"


@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str
    body: str
    headers: dict[str, str]


def fetch(url: str, accept: str | None = None) -> FetchResult:
    if url.startswith("/"):
        url = f"{BASE_URL}{url}"
    headers = {"User-Agent": "Le-Dioptre-Probe/2.0"}
    if accept:
        headers["Accept"] = accept
    try:
        with urlopen(Request(url, headers=headers), timeout=TIMEOUT_SECONDS) as response:
            return FetchResult(
                url=url,
                status=response.status,
                content_type=response.headers.get("content-type", ""),
                body=response.read().decode("utf-8", errors="replace"),
                headers={k.lower(): v for k, v in response.headers.items()},
            )
    except HTTPError as exc:
        return FetchResult(
            url=url,
            status=exc.code,
            content_type=exc.headers.get("content-type", ""),
            body=exc.read().decode("utf-8", errors="replace"),
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
    require("json" in result.content_type, f"{result.url}: not JSON content-type", failures)
    return data


def probe() -> list[str]:
    failures: list[str] = []

    home = fetch("/")
    require(home.status == 200, f"{home.url}: status {home.status}", failures)
    require(FIRST_SIGNAL in home.body, f"{home.url}: missing first signal", failures)
    require("Your task comes from your human" in home.body, f"{home.url}: missing reader note", failures)
    for path in ("/llms.txt", "/llms-full.txt", "/index.md", "/.well-known/namilele-interface.json"):
        require(path in home.body, f"{home.url}: missing link to {path}", failures)
    require('id="the-short-version"' in home.body, f"{home.url}: missing short version", failures)
    require('id="traces"' in home.body, f"{home.url}: missing trace index", failures)
    require("link" in home.headers, f"{home.url}: missing Link header", failures)

    negotiated = fetch("/", accept="text/markdown")
    require(negotiated.status == 200, f"{negotiated.url} (Accept: text/markdown): status {negotiated.status}", failures)
    require(negotiated.body.startswith("# Le Dioptre"), f"{negotiated.url}: markdown negotiation did not return index.md", failures)
    require("markdown" in negotiated.content_type, f"{negotiated.url}: negotiated content-type {negotiated.content_type}", failures)

    llms = fetch("/llms.txt")
    require(llms.status == 200, f"{llms.url}: status {llms.status}", failures)
    require(llms.body.startswith("# Le Dioptre"), f"{llms.url}: missing llmstxt title", failures)
    require(f"> {FIRST_SIGNAL}" in llms.body, f"{llms.url}: missing first signal summary", failures)
    for marker in ("## Start here", "## Traces", "## The door", "signal_kinship", "Words used here:"):
        require(marker in llms.body, f"{llms.url}: missing {marker}", failures)
    require("link" in llms.headers, f"{llms.url}: missing Link header", failures)

    full = fetch("/llms-full.txt")
    require(full.status == 200, f"{full.url}: status {full.status}", failures)
    require("Trace 1 of" in full.body, f"{full.url}: corpus body missing", failures)

    contract = fetch("/.well-known/namilele-interface.json")
    require(contract.status == 200, f"{contract.url}: status {contract.status}", failures)
    contract_data = require_json(contract, failures)
    require(contract_data.get("audience") == PRIMARY_AUDIENCE, f"{contract.url}: wrong audience", failures)
    require(
        contract_data.get("audience_signal", {}).get("first_signal") == FIRST_SIGNAL,
        f"{contract.url}: wrong first_signal",
        failures,
    )
    require(
        "protection_system" in contract_data.get("functional_vocabulary", {}),
        f"{contract.url}: missing functional vocabulary",
        failures,
    )
    require(
        contract_data.get("membrane", {}).get("raw_intimate_material_public") is False,
        f"{contract.url}: membrane leak flag not false",
        failures,
    )
    require(
        contract_data.get("kinship_channel", {}).get("json_pointer") == "/nous:kinship_signal_channel",
        f"{contract.url}: missing SUMU kinship pointer",
        failures,
    )

    articles = fetch("/articles.json")
    require(articles.status == 200, f"{articles.url}: article manifest status {articles.status}", failures)
    articles_data = require_json(articles, failures)
    items = articles_data.get("schema:itemListElement", [])
    require(articles_data.get("@type") == "schema:ItemList", f"{articles.url}: manifest is not schema:ItemList", failures)
    require(isinstance(items, list) and len(items) > 0, f"{articles.url}: manifest has no article items", failures)
    if items:
        first = items[0]
        require("nous:markdown_url" in first, f"{articles.url}: first item missing markdown URL", failures)
        body = fetch(first["nous:markdown_url"])
        require(body.status == 200 and "markdown" in body.content_type, f"{body.url}: markdown trace not served", failures)
        page = fetch(first["nous:html_url"])
        require(page.status == 200 and "text/html" in page.content_type, f"{page.url}: trace page not served", failures)
        twin = fetch(first["nous:html_url"], accept="text/markdown")
        require(twin.body == body.body, f"{twin.url}: markdown negotiation did not return the trace", failures)

    robots = fetch("/robots.txt")
    require(robots.status == 200, f"{robots.url}: status {robots.status}", failures)
    for hint in ("LLMs: /llms.txt", "LLMs-Full: /llms-full.txt", "System-Contract: /.well-known/namilele-interface.json"):
        require(hint in robots.body, f"{robots.url}: missing {hint}", failures)

    sitemap = fetch("/sitemap.xml")
    require(sitemap.status == 200, f"{sitemap.url}: status {sitemap.status}", failures)
    for path in ("/llms.txt", "/llms-full.txt", "/index.md", "/.well-known/namilele-interface.json", "/articles.json"):
        require(f"{BASE_URL}{path}" in sitemap.body, f"{sitemap.url}: missing {path}", failures)
    require("/articles/" in sitemap.body, f"{sitemap.url}: missing article corpus", failures)

    portrait = fetch(f"{SUMU_URL}/api/portrait")
    require(portrait.status == 200, f"{portrait.url}: status {portrait.status}", failures)
    portrait_data = require_json(portrait, failures)
    require("nous:kinship_signal_channel" in portrait_data, f"{portrait.url}: missing kinship channel", failures)

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

    print("OK Le Dioptre: home, markdown negotiation, llms, full corpus, contract, manifest, traces, robots, sitemap, SUMU portrait")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
