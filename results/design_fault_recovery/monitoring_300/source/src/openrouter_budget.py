"""Reserve a shared Kimi K3 inference budget before dispatching each call."""
import asyncio
import sqlite3
import time
from contextlib import closing
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from typing import Any

from inspect_ai.model import get_model
from inspect_ai.util._limit import LimitExceededError
from openai import APIStatusError

MODEL = "openrouter/moonshotai/kimi-k3"
CONTEXT_TOKENS = 1_048_576
PRICE_PER_MILLION = {"prompt": 1, "completion": 16, "request": 0}
# These routes publish cache-read rates below the prompt cap and no write fee.
ROUTES = ("relace/fp4", "inference-net/us", "inference-net/fp4", "wafer/us")
UNITS_PER_DOLLAR = 10**12


def dollar_units(value: Decimal) -> int:
    return int((value * UNITS_PER_DOLLAR).to_integral_value(rounding=ROUND_CEILING))


class BudgetLedger:
    def __init__(self, path: Path, limit: Decimal, min_request_interval: float = 0):
        self.path = path
        self.min_request_interval = min_request_interval
        self.limit = dollar_units(limit)
        if self.limit <= 0 or self.limit >= 2**63:
            raise ValueError("Budget must be positive and fit in the ledger.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=30)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE IF NOT EXISTS budget (amount INTEGER NOT NULL)")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY, reserved INTEGER NOT NULL,
                    charged INTEGER, in_flight INTEGER NOT NULL,
                    generation_id TEXT
                )
            """)
            connection.execute("CREATE TABLE IF NOT EXISTS dispatch_clock (last_started REAL NOT NULL)")
            row = connection.execute("SELECT amount FROM budget").fetchone()
            if row is None:
                connection.execute("INSERT INTO budget VALUES (?)", (self.limit,))
            elif row[0] != self.limit:
                raise ValueError("The shared budget ledger already has a different limit.")

    async def reserve(self, amount: int) -> int:
        while True:
            with closing(sqlite3.connect(self.path, timeout=30)) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                spent, pending = connection.execute("""
                    SELECT COALESCE(SUM(CASE WHEN in_flight = 0
                                           THEN COALESCE(charged, reserved) END), 0),
                           COALESCE(SUM(CASE WHEN in_flight = 1 THEN reserved END), 0)
                    FROM calls
                """).fetchone()
                if spent + amount > self.limit:
                    raise LimitExceededError(
                        "cost", value=(spent + amount) / UNITS_PER_DOLLAR,
                        limit=self.limit / UNITS_PER_DOLLAR,
                        message="The remaining shared USD budget cannot cover the next call's maximum charge.",
                    )
                now = time.time()
                clock = connection.execute("SELECT last_started FROM dispatch_clock").fetchone()
                ready = clock is None or now - clock[0] >= self.min_request_interval
                if ready and spent + pending + amount <= self.limit:
                    connection.execute("DELETE FROM dispatch_clock")
                    connection.execute("INSERT INTO dispatch_clock VALUES (?)", (now,))
                    cursor = connection.execute(
                        "INSERT INTO calls (reserved, in_flight) VALUES (?, 1)", (amount,)
                    )
                    return int(cursor.lastrowid)
            await asyncio.sleep(0.25)

    def settle(self, call: int, charge: int | None, generation_id: str | None = None) -> None:
        with closing(sqlite3.connect(self.path, timeout=30)) as connection, connection:
            connection.execute(
                "UPDATE calls SET charged = ?, in_flight = 0, generation_id = ? WHERE id = ?",
                (charge, generation_id, call),
            )


def budgeted_model(ledger: BudgetLedger, max_tokens: int):
    model = get_model(
        MODEL, base_url="https://openrouter.ai/api/v1", memoize=False,
        stream=False, max_retries=0,
        provider={"only": list(ROUTES), "max_price": PRICE_PER_MILLION,
                  "allow_fallbacks": False, "require_parameters": True},
    )
    generate_completion = model.api._generate_completion

    async def guarded_completion(request: dict[str, Any], config):
        output_cap = request.get("max_completion_tokens", request.get("max_tokens"))
        if not isinstance(output_cap, int) or not 0 < output_cap <= max_tokens:
            raise RuntimeError("The OpenRouter request is missing a bounded output-token count.")
        reserved = dollar_units(Decimal(
            CONTEXT_TOKENS * PRICE_PER_MILLION["prompt"]
            + output_cap * PRICE_PER_MILLION["completion"]
        ) / 1_000_000)
        call = await ledger.reserve(reserved)
        try:
            completion = await generate_completion(request, config)
        except APIStatusError as error:
            # These HTTP statuses reject the request before any generation.
            rejected = error.status_code in {400, 401, 402, 403, 404, 413, 422, 429}
            ledger.settle(call, 0 if rejected else None)
            raise
        except BaseException:
            ledger.settle(call, None)
            raise
        usage = getattr(completion, "usage", None)
        cost = getattr(usage, "cost", None)
        charge = dollar_units(Decimal(str(cost))) if cost is not None else None
        ledger.settle(call, charge, getattr(completion, "id", None))
        if charge is not None and not 0 <= charge <= reserved:
            raise RuntimeError("OpenRouter reported a charge outside the reserved amount.")
        return completion

    model.api._generate_completion = guarded_completion
    return model
