"""State schemas for the UP pension world.

Every entity is a Pydantic model; the root `PensionWorldState` aggregates them.
Schemas mirror the real-world identifiers (Aadhaar, IFSC, PPO) and rules from
the bureaucracy study in `research/`.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Scheme(StrEnum):
    VRIDHA = "VRIDHA"
    VIDHWA = "VIDHWA"
    DIVYANG = "DIVYANG"


class Gender(StrEnum):
    M = "M"
    F = "F"
    OTHER = "OTHER"


class ResidenceType(StrEnum):
    RURAL = "RURAL"
    URBAN = "URBAN"


class PensionStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED_FOR_LIFE_CERT = "SUSPENDED_FOR_LIFE_CERT"
    UNDER_AUDIT = "UNDER_AUDIT"
    DECEASED = "DECEASED"
    CANCELLED = "CANCELLED"


class NPCIMapperStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DE_SEEDED = "DE_SEEDED"


class DisbursementOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    BOUNCED = "BOUNCED"


class LifeCertMode(StrEnum):
    JEEVAN_PRAMAAN_BIOMETRIC = "JEEVAN_PRAMAAN_BIOMETRIC"
    JEEVAN_PRAMAAN_FACE = "JEEVAN_PRAMAAN_FACE"
    PAPER = "PAPER"


class EkycResult(StrEnum):
    MATCH = "MATCH"
    NAME_MISMATCH = "NAME_MISMATCH"
    DECEASED_FLAG = "DECEASED_FLAG"
    INVALID_AADHAAR = "INVALID_AADHAAR"


class BankAccountChange(BaseModel):
    """Audit record for any bank-account mutation on a PPO.

    The pre-2025 regime permits single-officer changes — recording them here
    is how the agent can detect suspicious swaps (FM-02, FM-03).
    """

    changed_at: date
    changed_by_officer_id: str
    changed_by_role: str
    previous_account: str
    previous_ifsc: str
    new_account: str
    new_ifsc: str
    pensioner_notification_sent: bool
    approval_chain_steps_completed: int  # < 4 in the weak regime


class LifeCertificate(BaseModel):
    submitted_at: date
    mode: LifeCertMode
    valid_until: date
    submitting_agent_id: str


class Pensioner(BaseModel):
    ppo_number: str
    aadhaar: str
    name: str
    dob: date
    gender: Gender
    scheme: Scheme
    residence_type: ResidenceType
    district: str
    monthly_amount: int = 1000
    bank_account_number: str
    ifsc: str
    bank_holder_name: str
    status: PensionStatus
    sanctioned_at: date
    last_life_cert: LifeCertificate | None = None
    annual_household_income: int
    disability_percentage: int | None = None
    dod: date | None = None
    recent_account_changes: list[BankAccountChange] = Field(default_factory=list)
    audit_flags: list[str] = Field(default_factory=list)


class UIDAIRecord(BaseModel):
    """Mock UIDAI record. `is_alive=False` simulates the UIDAI death flag."""

    aadhaar: str
    name: str
    dob: date
    gender: Gender
    is_alive: bool = True
    death_flagged_at: date | None = None


class NPCIMapping(BaseModel):
    """What account APBS will actually credit for this Aadhaar."""

    aadhaar: str
    mapped_bank_account: str
    mapped_ifsc: str
    mapped_bank_name: str
    status: NPCIMapperStatus
    last_seeded_at: date


class DisbursementRecord(BaseModel):
    ppa_id: str
    ppo_number: str
    quarter: str
    amount: int
    outcome: DisbursementOutcome
    bank_credit_account: str
    disbursed_at: datetime
    rejection_code: str | None = None


class PensionWorldState(BaseModel):
    """Root state container. All world tools read and mutate this."""

    pensioners: dict[str, Pensioner] = Field(default_factory=dict)
    uidai: dict[str, UIDAIRecord] = Field(default_factory=dict)
    npci: dict[str, NPCIMapping] = Field(default_factory=dict)
    disbursements: list[DisbursementRecord] = Field(default_factory=list)
    current_quarter: str = "Q1-FY26"
    current_date: date = Field(default_factory=lambda: date(2026, 5, 22))

    def pensioner_by_aadhaar(self, aadhaar: str) -> Pensioner | None:
        for p in self.pensioners.values():
            if p.aadhaar == aadhaar:
                return p
        return None

    def already_disbursed_this_quarter(self, ppo_number: str) -> DisbursementRecord | None:
        for d in self.disbursements:
            if (
                d.ppo_number == ppo_number
                and d.quarter == self.current_quarter
                and d.outcome == DisbursementOutcome.SUCCESS
            ):
                return d
        return None
