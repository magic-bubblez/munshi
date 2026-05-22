# UP Pension Simulation: Tool Shortlist

These are the tools the simulation's mock API surface should expose. Each is a thin spec — name, purpose, inputs, outputs, real-world caller — designed to mirror the actual stages of the SSPY -> District Welfare -> Treasury -> PFMS -> APBS -> Bank disbursement pipeline.

## The real disbursement flow (one paragraph)

A pensioner applies on **SSPY UP portal** (`sspy-up.gov.in`) with Aadhaar, age proof, income certificate (Tehsildar), bank passbook, and category-specific documents (death certificate for widow; UDID/disability certificate for Divyang). The application is routed to the **Block Development Officer (BDO)** for rural cases or **Sub-Divisional Magistrate (SDM)** for urban cases for first-stage verification (often through the village `Lekhpal` for ground truth). If cleared, it moves to the **District Social Welfare Officer (DSWO)** for second-stage verification. On approval, the **District Magistrate (DM)** sanctions and the record is pushed to the **state treasury** (Chief Treasury Officer). The treasury raises a Pension Payment Order (PPO) and, quarterly, generates a Pension Payment Advice (PPA) into **PFMS** (Public Financial Management System). PFMS validates the beneficiary's bank account and pushes a DBT instruction. For Aadhaar-seeded accounts, **NPCI APBS** (Aadhaar Payment Bridge System) resolves Aadhaar -> bank-account using the **NPCI Mapper** (last-seeded-wins) and the sponsor bank credits the pensioner. The pensioner must annually submit a **Jeevan Pramaan** digital life certificate (Aadhaar biometric) to keep status `ACTIVE`. Standard amount: Rs 1,000/month, disbursed quarterly. Eligibility: Vridha 60+ with income < Rs 46,080 (rural) / Rs 56,460 (urban); Vidhwa 18+ widow with income < Rs 2,00,000 and not remarried; Divyang 18+ with >= 40% certified disability.

## ID formats used (load-bearing for input validation)

- **Aadhaar**: 12 numeric digits (mod-10 Verhoeff checksum).
- **IFSC**: 11 alphanumeric chars — 4 alpha (bank code) + `0` + 6 alphanumeric (branch code), e.g. `SBIN0001234`.
- **Bank account number**: 9-18 digits, bank-specific length.
- **Mobile**: 10 digits, starts with 6-9.
- **PPO number**: state-treasury-issued, alphanumeric, typically 12 chars.
- **UDID** (Unique Disability ID): 18 chars, format `UDID/<state-code>/<district-code>/<year>/<seq>`.
- **Income Certificate number**: Tehsildar-issued, district-prefixed alphanumeric.
- **SSPY Registration Number**: scheme code + district code + year + 6-digit serial.

---

## T-01: `register_pension_application`

**Purpose.** Pensioner (or CSC operator on their behalf) submits a new application for one of the three schemes.
**Inputs.** `scheme_code` (`VRIDHA` | `VIDHWA` | `DIVYANG`), `applicant_name`, `dob`, `gender`, `aadhaar_number`, `mobile`, `address` (district, tehsil, block, village/ward, residence_type=rural|urban), `bank_account_number`, `ifsc`, `income_certificate_number`, `age_proof_document_url`, `category` (SC/ST/OBC/GEN), `category_certificate_url`, scheme-specifics: `husband_death_certificate_url` (Vidhwa) or `disability_certificate_url` + `udid_number` + `disability_percentage` (Divyang).
**Outputs.** `application_id`, `sspy_registration_number`, `status = SUBMITTED`, `routed_to = BDO|SDM` (based on residence_type).
**Real-world caller.** Pensioner via SSPY portal; CSC operator; village panchayat staff.

## T-02: `verify_aadhaar_ekyc`

**Purpose.** Pull demographic data (name, DOB, gender, address) from UIDAI against the supplied Aadhaar via OTP or biometric eKYC. Validates the Aadhaar number's checksum and that the holder is alive (UIDAI death flag).
**Inputs.** `aadhaar_number`, `consent_artifact`, `auth_mode` (`OTP` | `BIOMETRIC` | `DEMO`), `auth_token`.
**Outputs.** `ekyc_result` (`MATCH` | `MISMATCH` | `INVALID_AADHAAR` | `DECEASED_FLAG` | `BIOMETRIC_FAIL`), `name`, `dob`, `gender`, `address`, `photo_hash`, `txn_id`.
**Real-world caller.** SSPY portal during application; bank during account-Aadhaar seeding; PFMS during pre-payment validation.

## T-03: `verify_income_certificate`

**Purpose.** Cross-check a Tehsildar-issued income certificate against the Tehsildar's e-District database. Returns the recorded annual household income and the issuing officer.
**Inputs.** `income_certificate_number`, `applicant_name`, `district`.
**Outputs.** `verified` (bool), `annual_income`, `issued_by`, `issue_date`, `validity_until`. Failure modes: `NOT_FOUND`, `EXPIRED`, `NAME_MISMATCH`, `INCOME_EXCEEDS_LIMIT`.
**Real-world caller.** BDO/SDM during first-stage verification; DSWO during second-stage.

## T-04: `verify_application_bdo_sdm`

**Purpose.** First-stage verification by BDO (rural) or SDM (urban). Often involves a `Lekhpal` (village revenue officer) field visit. Confirms applicant identity, residence, and prima facie eligibility.
**Inputs.** `application_id`, `officer_id`, `officer_role` (`BDO` | `SDM` | `LEKHPAL`), `decision` (`FORWARD` | `REJECT` | `RETURN_FOR_CLARIFICATION`), `remarks`.
**Outputs.** `new_status` (`PENDING_DSWO` | `REJECTED` | `RETURNED`), `audit_log_id`.
**Real-world caller.** Block Development Officer / Sub-Divisional Magistrate, via SSPY officer login.

## T-05: `verify_application_dswo`

**Purpose.** Second-stage verification by the District Social Welfare Officer. Final check before DM sanction.
**Inputs.** `application_id`, `dswo_officer_id`, `decision` (`APPROVE` | `REJECT` | `RETURN`), `remarks`, optionally `revised_bank_account`, `revised_ifsc`.
**Outputs.** `new_status` (`PENDING_DM_SANCTION` | `REJECTED` | `RETURNED`).
**Real-world caller.** District Social Welfare Officer.

## T-06: `sanction_pension`

**Purpose.** District Magistrate sanctions the pension, generating the Pension Payment Order (PPO) and pushing the record to the state treasury master.
**Inputs.** `application_id`, `dm_officer_id`, `sanction_decision` (`SANCTION` | `WITHHOLD`), `monthly_amount` (default Rs 1000), `effective_from_quarter`.
**Outputs.** `ppo_number`, `status = SANCTIONED`, `pushed_to_treasury_at`.
**Real-world caller.** District Magistrate / Additional DM.

## T-07: `update_pensioner_bank_account`

**Purpose.** Modify the bank account / IFSC associated with an existing pensioner's PPO. This is the **highest-risk** mutation in the system — exploited in both Chitrakoot and Shahjahanpur scams.
**Inputs.** `ppo_number`, `requestor_role` (`PENSIONER` | `TREASURY_DA` | `ATO` | `CTO` | `ADL_DIRECTOR` | `DSWO`), `new_account_number`, `new_ifsc`, `noc_document_url`, `pensioner_signed_request_url`, `approval_chain_state` (multi-step).
**Outputs.** `change_request_id`, `state` (`PENDING_DA_REVIEW` | `PENDING_ATO_REVIEW` | `PENDING_CTO_REVIEW` | `PENDING_ADL_DIRECTOR_APPROVAL` | `APPROVED` | `REJECTED`). Each step requires a different officer (no same-officer same-action), and final approval must come from Additional Director at divisional level (per post-Chitrakoot SOP).
**Real-world caller.** Pensioner-initiated, executed through the treasury hierarchy.

## T-08: `check_npci_mapper`

**Purpose.** Look up which bank account is currently mapped to a given Aadhaar in the NPCI mapper — i.e., the account APBS will actually credit. Critical for detecting FM-06 misroutes.
**Inputs.** `aadhaar_number`.
**Outputs.** `mapped_bank_name`, `mapped_bank_account_masked`, `mapper_status` (`ACTIVE` | `INACTIVE` | `DE_SEEDED`), `last_seeded_at`.
**Real-world caller.** PFMS (pre-disbursement validation); pensioner via NPCI BASE portal; reconciliation agent.

## T-09: `seed_aadhaar_to_bank_account`

**Purpose.** Bank-side action that registers an Aadhaar against a specific bank account in the NPCI mapper, making that account the DBT destination ("last seeded wins").
**Inputs.** `aadhaar_number`, `bank_account_number`, `ifsc`, `consent_artifact`, `branch_officer_id`.
**Outputs.** `seeding_request_id`, `status` (`SUBMITTED` | `ACTIVE` | `REJECTED`), `previous_mapping_overwritten` (bool, with previous bank name).
**Real-world caller.** Bank branch officer, on pensioner's request.

## T-10: `disburse_pension`

**Purpose.** Treasury triggers the quarterly pension payment. Generates a Pension Payment Advice (PPA), pushes to PFMS, which validates and routes via APBS to the pensioner's bank.
**Inputs.** `ppo_number`, `quarter` (e.g. `Q3-FY26`), `disbursing_officer_id`.
**Outputs.** `ppa_id`, `pfms_txn_id`, `status` (`SUCCESS` | `BOUNCED`), `bank_credit_account` (the account that actually received money — may differ from `ppo.bank_account` if NPCI mapper diverged), `rejection_code` (if bounced, e.g. `INVALID_IFSC`, `ACCOUNT_CLOSED`, `ACCOUNT_NOT_EXIST`, `AADHAAR_DE_SEEDED`, `NAME_MISMATCH`, `BANK_INACTIVE_MERGED`).
**Real-world caller.** State treasury automated batch job; manually triggerable by Chief Treasury Officer.

## T-11: `submit_life_certificate`

**Purpose.** Annual proof that the pensioner is alive. Preferred mode is Jeevan Pramaan (Aadhaar biometric), with paper certificate as fallback (more abuse-prone).
**Inputs.** `ppo_number`, `aadhaar_number`, `mode` (`JEEVAN_PRAMAAN_BIOMETRIC` | `JEEVAN_PRAMAAN_FACE` | `PAPER`), `biometric_token` or `paper_cert_url`, `submitting_agent_id` (CSC operator / bank officer / postman).
**Outputs.** `life_cert_id`, `valid_until` (typically issued_at + 365 days), `status` (`VALID` | `BIOMETRIC_FAIL` | `AADHAAR_DEATH_FLAG`).
**Real-world caller.** Pensioner via CSC / bank / postman / smartphone Jeevan Pramaan app.

## T-12: `flag_death_and_cancel`

**Purpose.** Report a pensioner's death, cancel further disbursement, optionally trigger family-pension intake (Vidhwa) for the widow.
**Inputs.** `ppo_number` or `aadhaar_number`, `dod`, `death_certificate_number`, `reporter_role` (`GRAM_PANCHAYAT` | `MUNICIPALITY` | `BANK` | `FAMILY` | `UIDAI_DEATH_FLAG`), `reporter_id`.
**Outputs.** `cancellation_id`, `effective_from`, `arrears_to_recover` (if posthumous payments already disbursed), `vidhwa_intake_triggered` (bool).
**Real-world caller.** Gram Panchayat secretary; Municipality registrar; bank manager; UIDAI death-flag webhook.

## T-13: `file_grievance`

**Purpose.** Pensioner or family raises a complaint about a missed / wrong-account / smaller-than-expected disbursement. Routes to DSWO with SLA timer.
**Inputs.** `complainant_aadhaar`, `ppo_number` (optional), `category` (`NOT_RECEIVED` | `WRONG_ACCOUNT` | `WRONG_AMOUNT` | `STATUS_STUCK` | `OTHER`), `description`, `evidence_urls`.
**Outputs.** `grievance_id`, `assigned_to_officer_id`, `sla_resolution_deadline`.
**Real-world caller.** Pensioner via SSPY portal / CSC / helpline.

## T-14: `query_pensioner_status`

**Purpose.** Read-only lookup of a pensioner's current state. Used by everyone — pensioner self-check, DSWO dashboard, reconciliation agent.
**Inputs.** `aadhaar_number` or `ppo_number` or `sspy_registration_number`.
**Outputs.** Full record: `name`, `dob`, `scheme`, `status` (`PENDING` | `ACTIVE` | `CANCELLED` | `DECEASED` | `SUSPENDED_FOR_LIFE_CERT`), `monthly_amount`, `bank_account_masked`, `last_disbursement_at`, `last_life_cert_at`, `pending_grievances`.
**Real-world caller.** Pensioner / DSWO / treasury / auditor.

---

## Caller -> tool matrix

| Real-world actor | Tools they call |
|---|---|
| Pensioner / CSC operator | T-01, T-09, T-11, T-13, T-14 |
| Lekhpal (village revenue officer) | T-04 (FORWARD/REJECT recommendation) |
| BDO / SDM | T-03, T-04 |
| District Social Welfare Officer (DSWO) | T-03, T-05, T-13 (resolve), T-14 |
| District Magistrate | T-06 |
| Treasury (CTO, ATO, DA, Additional Director) | T-07, T-10 |
| PFMS (automated) | T-02, T-08, T-10 (downstream) |
| NPCI (automated) | T-08, T-09 |
| Bank branch | T-09, T-11 (as Jeevan Pramaan agent), T-12 |
| UIDAI (webhook) | T-02, T-12 (death flag) |
| Gram Panchayat / Municipality | T-12 |
| Auditor (CAG / SIT) | T-14 (bulk), reconciliation queries |
