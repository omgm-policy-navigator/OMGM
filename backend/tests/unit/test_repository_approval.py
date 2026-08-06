import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.eligibility.repository import get_active_policy_with_rules, list_active_policies_for_category


class ScalarResult:
    def __init__(self, items=(), one=None):
        self.items = list(items)
        self.one = one

    def scalars(self):
        return self

    def all(self):
        return self.items

    def scalar_one_or_none(self):
        return self.one


def rule(status: str):
    return SimpleNamespace(approval_status=status)


def test_policy_without_approved_rules_is_not_listed() -> None:
    policy = SimpleNamespace(rules=[rule("DRAFT"), rule("REJECTED")])
    db = AsyncMock()
    db.execute.return_value = ScalarResult(items=[policy])

    result = asyncio.run(list_active_policies_for_category(db, "housing"))

    assert result == []


def test_policy_without_approved_rules_is_not_returned() -> None:
    policy = SimpleNamespace(rules=[rule("DRAFT")])
    db = AsyncMock()
    db.execute.return_value = ScalarResult(one=policy)

    result = asyncio.run(get_active_policy_with_rules(db, "policy_1"))

    assert result is None


def test_only_approved_rules_reach_evaluation() -> None:
    approved = rule("APPROVED")
    policy = SimpleNamespace(rules=[rule("DRAFT"), approved])
    db = AsyncMock()
    db.execute.return_value = ScalarResult(items=[policy])

    result = asyncio.run(list_active_policies_for_category(db, "housing"))

    assert result == [policy]
    assert policy.rules == [approved]
