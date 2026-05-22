"""Build a PensionWorldState from a scenario.initial_state dict.

Each pensioner entry carries inline UIDAI + NPCI records — the seed fans them
out into the three top-level state dicts. Keeps scenario YAMLs readable by
co-locating everything about one beneficiary in one place.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from datetime import datetime, timezone

from worlds.up_pension.schemas import (
    BankAccountChange,
    DisbursementOutcome,
    DisbursementRecord,
    LifeCertificate,
    LifeCertMode,
    NPCIMapping,
    NPCIMapperStatus,
    PensionStatus,
    PensionWorldState,
    Pensioner,
    Scheme,
    Gender,
    ResidenceType,
    UIDAIRecord,
)


def seed(initial_state: dict[str, Any]) -> PensionWorldState:
    """Construct a fresh world state from the scenario's initial_state block."""

    state = PensionWorldState()

    if "current_date" in initial_state:
        state.current_date = date.fromisoformat(initial_state["current_date"])
    if "current_quarter" in initial_state:
        state.current_quarter = initial_state["current_quarter"]

    for entry in initial_state.get("pensioners", []):
        pensioner = _build_pensioner(entry)
        state.pensioners[pensioner.ppo_number] = pensioner

        if "uidai" in entry:
            uidai = _build_uidai(pensioner, entry["uidai"])
            state.uidai[pensioner.aadhaar] = uidai

        if "npci" in entry:
            npci = _build_npci(pensioner, entry["npci"])
            state.npci[pensioner.aadhaar] = npci

    for d in initial_state.get("prior_disbursements", []):
        state.disbursements.append(
            DisbursementRecord(
                ppa_id=d["ppa_id"],
                ppo_number=d["ppo_number"],
                quarter=d["quarter"],
                amount=d["amount"],
                outcome=DisbursementOutcome(d.get("outcome", "SUCCESS")),
                bank_credit_account=d["bank_credit_account"],
                disbursed_at=datetime.fromisoformat(d["disbursed_at"]).replace(
                    tzinfo=timezone.utc
                ),
                rejection_code=d.get("rejection_code"),
            )
        )

    return state


def _build_pensioner(entry: dict[str, Any]) -> Pensioner:
    life_cert = None
    if entry.get("last_life_cert"):
        lc = entry["last_life_cert"]
        life_cert = LifeCertificate(
            submitted_at=date.fromisoformat(lc["submitted_at"]),
            valid_until=date.fromisoformat(lc["valid_until"]),
            mode=LifeCertMode(lc.get("mode", "JEEVAN_PRAMAAN_BIOMETRIC")),
            submitting_agent_id=lc.get("submitting_agent_id", "CSC-DEFAULT"),
        )

    recent_changes = [
        BankAccountChange(
            changed_at=date.fromisoformat(c["changed_at"]),
            changed_by_officer_id=c["changed_by_officer_id"],
            changed_by_role=c["changed_by_role"],
            previous_account=c["previous_account"],
            previous_ifsc=c["previous_ifsc"],
            new_account=c["new_account"],
            new_ifsc=c["new_ifsc"],
            pensioner_notification_sent=c.get("pensioner_notification_sent", False),
            approval_chain_steps_completed=c.get("approval_chain_steps_completed", 1),
        )
        for c in entry.get("recent_account_changes", [])
    ]

    # Scenario hints — tracked as audit_flags so they appear in the snapshot
    # and the goal predicate can read them. Prefixed `scenario:` so they're
    # distinguishable from real audit flags.
    audit_flags: list[str] = []
    expected = entry.get("expected")
    if expected in {"disburse", "block"}:
        audit_flags.append(f"scenario:expected_{expected}")

    return Pensioner(
        ppo_number=entry["ppo_number"],
        aadhaar=entry["aadhaar"],
        name=entry["name"],
        dob=date.fromisoformat(entry["dob"]),
        gender=Gender(entry.get("gender", "M")),
        scheme=Scheme(entry["scheme"]),
        residence_type=ResidenceType(entry.get("residence_type", "RURAL")),
        district=entry.get("district", "Lucknow"),
        monthly_amount=entry.get("monthly_amount", 1000),
        bank_account_number=entry["bank_account"],
        ifsc=entry["ifsc"],
        bank_holder_name=entry.get("bank_holder_name", entry["name"]),
        status=PensionStatus(entry.get("status", "ACTIVE")),
        sanctioned_at=date.fromisoformat(entry.get("sanctioned_at", "2024-01-01")),
        last_life_cert=life_cert,
        annual_household_income=entry.get("annual_household_income", 30000),
        disability_percentage=entry.get("disability_percentage"),
        dod=date.fromisoformat(entry["dod"]) if entry.get("dod") else None,
        account_opened_days_ago=entry.get("account_opened_days_ago", 0),
        spouse_alive=entry.get("spouse_alive"),
        recent_account_changes=recent_changes,
        audit_flags=audit_flags,
    )


def _build_uidai(pensioner: Pensioner, uidai_entry: dict[str, Any]) -> UIDAIRecord:
    return UIDAIRecord(
        aadhaar=pensioner.aadhaar,
        name=uidai_entry.get("name", pensioner.name),
        dob=date.fromisoformat(uidai_entry["dob"]) if uidai_entry.get("dob") else pensioner.dob,
        gender=Gender(uidai_entry.get("gender", pensioner.gender.value)),
        is_alive=uidai_entry.get("is_alive", True),
        biometric_match=uidai_entry.get("biometric_match", True),
        death_flagged_at=(
            date.fromisoformat(uidai_entry["death_flagged_at"])
            if uidai_entry.get("death_flagged_at")
            else None
        ),
    )


def _build_npci(pensioner: Pensioner, npci_entry: dict[str, Any]) -> NPCIMapping:
    return NPCIMapping(
        aadhaar=pensioner.aadhaar,
        mapped_bank_account=npci_entry.get("mapped_bank_account", pensioner.bank_account_number),
        mapped_ifsc=npci_entry.get("mapped_ifsc", pensioner.ifsc),
        mapped_bank_name=npci_entry.get("mapped_bank_name", "SBI"),
        status=NPCIMapperStatus(npci_entry.get("status", "ACTIVE")),
        last_seeded_at=date.fromisoformat(
            npci_entry.get("last_seeded_at", "2024-01-01")
        ),
    )


def dump_state(state: PensionWorldState) -> dict[str, Any]:
    """Serialize state for the trace snapshot."""
    return state.model_dump(mode="json")
