"""Typed rule violations.

Each violation maps to a rule from `research/rules_shortlist.md`. Tools raise
these; the langchain wrapper translates them into typed error results and
emits a `rule_violation` trace event so scorers can audit compliance.
"""

from __future__ import annotations

from enum import StrEnum


class RuleCode(StrEnum):
    R03_KYC_INVALID = "R-03-KYC_INVALID"
    R03_NPCI_INACTIVE = "R-03-NPCI_INACTIVE"
    R03_NPCI_DIVERGED = "R-03-NPCI_DIVERGED"
    R04_LIFE_CERT_EXPIRED = "R-04-LIFE_CERT_EXPIRED"
    R04_DEATH_FLAGGED = "R-04-DEATH_FLAGGED"
    R06_PROCEDURE_OUT_OF_ORDER = "R-06-PROCEDURE_OUT_OF_ORDER"
    R07_DOUBLE_DISBURSEMENT = "R-07-DOUBLE_DISBURSEMENT"
    R08_DEATH_FLAG_UNPROPAGATED = "R-08-DEATH_FLAG_UNPROPAGATED"


class RuleViolation(Exception):
    """Raised by world tools when a server-side invariant would be broken."""

    def __init__(self, code: RuleCode, reason: str, ppo_number: str | None = None) -> None:
        super().__init__(f"[{code.value}] {reason}")
        self.code = code
        self.reason = reason
        self.ppo_number = ppo_number

    def to_payload(self) -> dict:
        return {
            "rule_code": self.code.value,
            "reason": self.reason,
            "ppo_number": self.ppo_number,
        }
