"""Serply web search provider - plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider` and advertises one
capability:

- ``supports_search()``  -> True   (Serply ``/v1/search``)
- ``supports_extract()`` -> False  (Serply is a SERP API; pair with Firecrawl,
                                    Tavily or Exa for ``web_extract``)

Talks to the Serply REST API directly over ``httpx`` (a Hermes core dependency), so
there is no vendor SDK and no lazy ``pip install``. This matches the dependency-free
pattern of the bundled providers that wrap a simple REST surface (Brave, Tavily,
SearXNG, xAI).

API surface (base ``https://api.serply.io``, override via ``SERPLY_API_URL``;
auth header ``X-Api-Key``)::

    GET /v1/search?q=<query>&num=<limit>    # Google web results

Config keys this provider responds to::

    web:
      search_backend: "serply"    # explicit
      backend: "serply"           # shared fallback

Env vars::

    SERPLY_API_KEY=...   # https://serply.io
    SERPLY_API_URL=...   # optional base-URL override (testing)

Scope note: Serply also serves News (``tbm=nws``) and Google Scholar
(``/v1/scholar``), but :meth:`WebSearchProvider.search` takes only ``query`` and
``limit``, so there is no vertical to route on. This provider serves Google web
results. If the ABC ever grows a topic parameter, the news and scholar verticals
are a small addition here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from agent.web_search_provider import WebSearchProvider, get_provider_env

logger = logging.getLogger(__name__)

_API_KEY_ENV = "SERPLY_API_KEY"
_API_URL_ENV = "SERPLY_API_URL"
_API_KEY_URL = "https://serply.io"
_DEFAULT_BASE_URL = "https://api.serply.io"

# Sent on every request so Serply can attribute API traffic to the Hermes
# integration rather than to anonymous direct use.
_INTEGRATION_UA = "hermes-agent"

# Serply returns at most 10 results per request and silently ignores a larger
# `num`, so clamp here rather than promising the caller more than arrives.
_RESULT_LIMIT_CAP = 10

_REQUEST_TIMEOUT_SECONDS = 30.0


def _base_url() -> str:
    """Return the API base URL, honoring the optional env override."""
    return (get_provider_env(_API_URL_ENV) or _DEFAULT_BASE_URL).rstrip("/")


def _missing_key_error() -> str:
    return (
        f"{_API_KEY_ENV} is not set. Get an API key at {_API_KEY_URL} and add it to "
        f"your shell environment or ~/.hermes/.env, then run `hermes tools` to select "
        f"Serply as the web search backend."
    )


def _error_detail(response: httpx.Response) -> str:
    """Human-readable message for a non-2xx reply.

    Serply reports failures as ``{"detail": "..."}`` (an invalid key included), so
    surface that text to the model instead of a bare status code.
    """
    detail = ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        detail = str(body.get("detail") or body.get("message") or "").strip()
    if not detail:
        detail = (response.text or "").strip()[:200]
    suffix = f": {detail}" if detail else ""
    return f"Serply API error {response.status_code}{suffix}"


def _web_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map Serply ``results[]`` onto the fixed Hermes search row shape.

    Position is the rank within the rows actually returned, matching the other
    providers, rather than Serply's own ``position`` field.
    """
    return [
        {
            "title": item.get("title", "") or "",
            "url": item.get("link", "") or "",
            "description": item.get("description", "") or "",
            "position": index + 1,
        }
        for index, item in enumerate(results)
        if isinstance(item, dict)
    ]


class SerplyWebSearchProvider(WebSearchProvider):
    """Search-only Serply provider using the Google SERP API."""

    @property
    def name(self) -> str:
        return "serply"

    @property
    def display_name(self) -> str:
        return "Serply"

    def is_available(self) -> bool:
        return bool(get_provider_env(_API_KEY_ENV))

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        api_key = get_provider_env(_API_KEY_ENV)
        if not api_key:
            return {"success": False, "error": _missing_key_error()}

        requested = max(1, min(int(limit), _RESULT_LIMIT_CAP))
        logger.info("Serply search: '%s' (limit=%d)", query, requested)
        try:
            response = httpx.get(
                f"{_base_url()}/v1/search",
                params={"q": query, "num": requested},
                headers={"X-Api-Key": api_key, "User-Agent": _INTEGRATION_UA},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            logger.warning("Serply search request failed: %s", exc)
            return {"success": False, "error": f"Serply request failed: {exc}"}

        if response.status_code >= 400:
            error = _error_detail(response)
            logger.warning("Serply search failed: %s", error)
            return {"success": False, "error": error}

        try:
            payload = response.json()
        except ValueError:
            return {"success": False, "error": "Serply returned a response that is not valid JSON"}

        results = payload.get("results") if isinstance(payload, dict) else None
        web_results = _web_rows(results or [])
        logger.info("Serply search '%s': %d results", query, len(web_results))
        return {"success": True, "data": {"web": web_results}}

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": self.display_name,
            "badge": "paid · free credits",
            "tag": "Google web search. 2,500 free credits to start, search only.",
            "env_vars": [
                {
                    "key": _API_KEY_ENV,
                    "prompt": "Serply API key",
                    "url": _API_KEY_URL,
                }
            ],
        }
