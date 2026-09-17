# hermes-web-serply

A [Serply](https://serply.io) web search provider plugin for
[Hermes Agent](https://github.com/NousResearch/hermes-agent).

Registers `serply` as a `web_search` backend, so the agent answers from live Google
results instead of from memory. Search only: pair it with Firecrawl, Tavily or Exa if
you also want `web_extract`.

## Install

```bash
hermes plugins install web-serply
```

Or clone into your user plugin directory and enable it:

```bash
git clone https://github.com/serply-inc/hermes-web-serply ~/.hermes/plugins/web/serply
hermes plugins enable web-serply
```

## Configure

Get an API key at [serply.io](https://serply.io), then set it in your shell or in
`~/.hermes/.env`:

```bash
export SERPLY_API_KEY="your-key"
```

Select Serply as the search backend with `hermes tools`, or set it directly in
`~/.hermes/config.yaml`:

```yaml
web:
  search_backend: "serply"
```

`web.backend: "serply"` also works as the shared fallback when `search_backend` is
unset.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `SERPLY_API_KEY` | yes | API key, from [serply.io](https://serply.io) |
| `SERPLY_API_URL` | no | Base URL override, defaults to `https://api.serply.io` |

## Behaviour

- Calls `GET /v1/search` with `q` and `num`, authenticated with the `X-Api-Key` header.
- Requests at most 10 results. Serply caps a single response at 10 and ignores a
  larger `num`, so the plugin clamps rather than promising more than arrives.
- Returns the fixed Hermes envelope,
  `{"success": true, "data": {"web": [{"title", "url", "description", "position"}]}}`,
  with `position` being the rank among the rows returned.
- On failure returns `{"success": false, "error": ...}`, surfacing Serply's own
  `detail` message so an invalid or exhausted key explains itself to the model.
- Sends `User-Agent: hermes-agent` so Serply can attribute traffic to this
  integration.

## Scope

Serply also serves News (`tbm=nws`) and Google Scholar (`/v1/scholar`), but the Hermes
`WebSearchProvider` interface passes only `query` and `limit`, with no vertical to
route on. This plugin therefore serves Google web results. If that interface grows a
topic parameter, the other verticals are a small addition here.

## Pricing

Serply starts with 2,500 free credits and then uses prepaid packs; credits do not
expire. Current pricing is at [serply.io](https://serply.io), and the API is
documented at [serply.io/docs](https://serply.io/docs).

## Development

The plugin is three files: `plugin.yaml` (manifest), `provider.py`
(`SerplyWebSearchProvider`, a `WebSearchProvider` subclass) and `__init__.py`
(`register()`). It depends only on `httpx`, which Hermes already ships, so there is
no SDK to install.

See the Hermes
[web search provider plugin guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/web-search-provider-plugin.md)
for the provider contract.

## License

MIT, see [LICENSE](LICENSE).

---

Maintained by [Serply](https://serply.io).
