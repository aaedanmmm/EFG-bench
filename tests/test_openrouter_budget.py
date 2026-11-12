import asyncio
from decimal import Decimal

import pytest
from inspect_ai.util._limit import LimitExceededError

from src.openrouter_budget import BudgetLedger, dollar_units


def test_budget_waits_for_inflight_reservation(tmp_path):
    async def check_budget():
        path = tmp_path / "budget.sqlite"
        ledger = BudgetLedger(path, Decimal("10"))
        other_process_ledger = BudgetLedger(path, Decimal("10"))

        first = await ledger.reserve(dollar_units(Decimal("6")))
        next_call = asyncio.create_task(other_process_ledger.reserve(dollar_units(Decimal("5"))))
        await asyncio.sleep(0)
        assert not next_call.done()
        ledger.settle(first, dollar_units(Decimal("5")))
        second = await asyncio.wait_for(next_call, timeout=2)
        other_process_ledger.settle(second, None)
        with pytest.raises(LimitExceededError, match="remaining shared USD budget"):
            await ledger.reserve(1)

    asyncio.run(check_budget())


def test_budget_stays_shared_when_reopened(tmp_path):
    async def check_budget():
        path = tmp_path / "budget.sqlite"
        ledger = BudgetLedger(path, Decimal("10"))
        call = await ledger.reserve(dollar_units(Decimal("8")))
        ledger.settle(call, dollar_units(Decimal("7.5")), "offline-example")
        with pytest.raises(ValueError, match="different limit"):
            BudgetLedger(path, Decimal("20"))
        with pytest.raises(LimitExceededError):
            await BudgetLedger(path, Decimal("10")).reserve(dollar_units(Decimal("2.51")))

    asyncio.run(check_budget())


def test_dispatch_pacing_is_shared_by_ledger_instances(tmp_path):
    async def check_pacing():
        path = tmp_path / "budget.sqlite"
        ledger = BudgetLedger(path, Decimal("10"), min_request_interval=0.1)
        first = await ledger.reserve(1)
        ledger.settle(first, 0)

        second_ledger = BudgetLedger(path, Decimal("10"), min_request_interval=0.1)
        second = asyncio.create_task(second_ledger.reserve(1))
        await asyncio.sleep(0)
        assert not second.done()
        second_ledger.settle(await asyncio.wait_for(second, timeout=2), 0)

    asyncio.run(check_pacing())
