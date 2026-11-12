"""Fetch only billing and timing metadata for generation IDs in summary.json."""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
FIELDS = (
    "total_cost", "model", "provider_name", "created_at", "latency",
    "generation_time", "native_tokens_prompt", "native_tokens_cached",
    "native_tokens_completion", "native_tokens_reasoning",
)


def fetch(generation_id, key):
    url = "https://openrouter.ai/api/v1/generation?" + urlencode({"id": generation_id})
    request = Request(url, headers={"Authorization": "Bearer " + key})
    for delay in (1, 2, 4, 0):
        try:
            with urlopen(request, timeout=20) as response:
                data = json.load(response)["data"]
            return generation_id, {field: data.get(field) for field in FIELDS}
        except HTTPError as error:
            failure = f"HTTP {error.code}"
            if error.code not in (404, 429, 500, 502, 503, 524, 529):
                break
        except (TimeoutError, URLError) as error:
            failure = type(error).__name__
        time.sleep(delay)
    return generation_id, {"error": failure}


def main():
    load_dotenv(".env")
    key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPEN-ROUTER_API")
    if not key:
        raise SystemExit("OpenRouter API key missing.")
    summary = json.loads((ROOT / "summary.json").read_text())
    destination = ROOT / "generation_billing.json"
    billing = json.loads(destination.read_text()) if destination.exists() else {}
    ids = {
        generation_id for suite in summary["suites"].values()
        for sample in suite["attempts"] for generation_id in sample["generation_ids"]
    }
    missing = sorted(generation_id for generation_id in ids if
                     billing.get(generation_id, {}).get("total_cost") is None)
    with ThreadPoolExecutor(max_workers=4) as executor:
        billing.update(executor.map(lambda generation_id: fetch(generation_id, key), missing))
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(billing, indent=2, sort_keys=True) + "\n")
    temporary.replace(destination)
    available = sum(billing.get(generation_id, {}).get("total_cost") is not None for generation_id in ids)
    print(f"Generation billing available for {available}/{len(ids)} calls.")


if __name__ == "__main__":
    main()
