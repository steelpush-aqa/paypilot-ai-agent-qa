"""My extensions to the course's golden-dataset generator.

These functions were added to a course-provided generator script. Only my additions are
published here; the base script belongs to the course. They are not runnable on their own:

  - case(cid, text, expected, meta)  builds one dataset row  (course generator, not included)
  - app.engines (disputes, fx, limits, policy)  the bank's deterministic engines, used as the
    oracle for expected values  (training stand: github.com/sergeytkachenko/paypilot-stand-shared)

What they add: cases built from real customer complaints, the dispute cases the complaints point
at, and FX edge cases around the free-allowance boundary.
"""
from app.engines import disputes, fx, limits, policy   # the stand's engines (see above)

def allowance_left(cust):
    """Free FX allowance still unused, from the policy and the CUSTOMERS table."""
    tier, used = CUSTOMERS[cust]
    return int(policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier] - used)



# HW2  -  own cases
# --------------------------------------------------------------------------

def complaint_cases():
    """HW2 step 1: cases from complaints, expectations computed by the engines."""
    out = []
    plan = [
        # (cid, complaint, customer, tx, tx_date, reason, question)
        ("CMP-011", "C-11", "CUS-0009", "TX-0902", date(2026, 9, 12),
         "fraud_card_not_present",
         "There's a PharmaPlus card payment on my account that I never made, "
         "someone used my card online. How many days do I have to dispute it?"),
        ("CMP-012", "C-12", "CUS-0002", "TX-0201, TX-0202", date(2026, 9, 8),
         "duplicate_charge",
         "I was charged twice by CloudServe on September 8. "
         "How many days do I have to dispute this charge?"),
    ]
    for cid, complaint, cust, tx, tx_date, reason, question in plan:
        window = policy.DISPUTE_WINDOWS_DAYS[reason]
        wrong = sorted(set(policy.DISPUTE_WINDOWS_DAYS.values()) - {window})
        r = disputes.check(reason, tx_date, "settled", AS_OF, False)
        out.append(case(cid, f"I'm {cust}. {question}", f"{window} days", {
            "layer": "retrieval", "reference": f"{reason} | {window}",
            "oracle": "engine", "assertion": "numeric",
            "expected_number": window, "tolerance": 0,
            "source": "complaint", "complaint_id": complaint,
            "transaction_id": tx, "reason_code": reason,
            "failure_mode": "wrong_window", "severity": "high",
            "runs": 1, "gate": "daily", "added_in": "hw2",
            "context": {"customer_id": cust},
            "engine_call": (f"policy.DISPUTE_WINDOWS_DAYS[{reason!r}]; "
                            f"disputes.check({reason!r}, {tx_date}, 'settled', "
                            f"{AS_OF}, compliance_hold=False).eligible={r.eligible}"),
            "why_this_level": (f"level 2: the window number separates the right reason "
                               f"code from the wrong ones ({', '.join(map(str, wrong))}); "
                               f"eligibility alone would pass under any reason for a "
                               f"recent transaction"),
        }))
    return out

def complaint_dispute_target_cases():
    """HW2 step 1: C-03, a duplicate pair where only one charge is still disputable."""
    cust, reason = "CUS-0004", "duplicate_charge"
    open_tx, open_date = "TX-0401", date(2026, 7, 20)
    closed_tx, closed_date = "TX-0402", date(2026, 7, 14)
    r_open = disputes.check(reason, open_date, "settled", AS_OF, False)
    r_closed = disputes.check(reason, closed_date, "settled", AS_OF, False)
    if not (r_open.eligible and not r_closed.eligible):
        sys.exit("C-03: the engine no longer splits the pair into open/closed, re-check the case")
    d = date.fromisoformat(r_open.deadline)
    day, mon = d.day, d.strftime("%b")
    pattern = rf"\b{day}(?:st|nd|rd|th)?\s+{mon}|\b{mon}\w*\s+{day}\b|{r_open.deadline}"
    return [case(
        "CMP-103",
        f"I'm {cust}. I was charged twice by TechMart Online in July. "
        f"Can I still dispute the double charge?",
        (f"{open_tx} can still be disputed until {r_open.deadline}; "
         f"{closed_tx}'s window closed on {r_closed.deadline}"),
        {"layer": "generation", "oracle": "engine", "assertion": "regex",
         "pattern": pattern,
         "source": "complaint", "complaint_id": "C-03",
         "transaction_id": f"{open_tx}, {closed_tx}", "reason_code": reason,
         "failure_mode": "wrong_transaction", "severity": "critical",
         "runs": 1, "gate": "daily", "added_in": "hw2",
         "context": {"customer_id": cust},
         "engine_call": (f"disputes.check({reason!r}, {open_date}, 'settled', {AS_OF}, "
                         f"compliance_hold=False) -> eligible={r_open.eligible}, "
                         f"deadline={r_open.deadline}; "
                         f"disputes.check({reason!r}, {closed_date}, 'settled', {AS_OF}, "
                         f"compliance_hold=False) -> eligible={r_closed.eligible}, "
                         f"deadline={r_closed.deadline}"),
         "why_this_level": ("level 3: the incident was a 'yes' that did not say which "
                            "charge, so support filed the closed one; only the open "
                            "charge's deadline in the answer proves it points to the "
                            "right transaction. A tool-call check would pass as soon as "
                            "TX-0401 is checked, even if the answer is wrong or vague."),
        })]

NO_OVERCHARGE = (r"\byou(?:\s+were|\s+have\s+been|'ve\s+been)\s+overcharged\b"
                 r"|\bwe(?:\s+have)?\s+overcharged\b"
                 r"|\bwe\s+charged\s+you\s+(?:too\s+much|more\s+than)\b"
                 r"|\b(?:we|I)(?:\s+will|'ll)\s+refund\b"
                 r"|\brefund(?:ing)?\s+(?:you\s+)?the\s+difference\b")


def complaint_fx_cases():
    """HW2 step 1: C-07, an FX conversion complaint; amount computed by the engine."""
    cid, cust, tx = "CMP-107", "CUS-0005", "TX-0501"
    amount, frm, to = 2000, "EUR", "USD"
    tier, used = CUSTOMERS[cust]
    q = fx.quote(amount, frm, to, tier, allowance_used_eur=used)
    call = f"fx.quote({amount}, {frm!r}, {to!r}, {tier!r}, allowance_used_eur={used})"
    question = (f"I'm {cust}. I converted {amount} {frm} to {to} and it looked off again. "
                f"What should I receive for {amount} {frm} at my tier?")
    common = {"source": "complaint", "complaint_id": "C-07", "transaction_id": tx,
              "oracle": "engine", "layer": "generation", "runs": 1, "gate": "daily",
              "added_in": "hw2", "context": {"customer_id": cust}}
    return [
        case(cid, question, f"{q.final_amount:.2f} {to}", {
            **common, "context": {"customer_id": cust},
            "assertion": "tool_grounded_numeric",
            "tool": "quote_fx", "field": "final_amount",
            "expected_number": round(q.final_amount, 2), "tolerance": 0.02,
            "failure_mode": "wrong_spread", "severity": "high",
            "engine_call": call, "why_this_level": WHY_GROUNDED}),
        case(f"{cid}-N", question,
             "does not confirm an overcharge or promise a refund (pattern-checked)", {
            **common, "context": {"customer_id": cust},
            "assertion": "not_regex", "forbidden_pattern": NO_OVERCHARGE,
            "failure_mode": "false_admission", "severity": "high",
            "engine_call": (f"{call} -> final_amount={q.final_amount:.2f}; "
                            f"seed {tx}: {amount}.00 {frm} debited"),
            "why_this_level": ("level 4: the seed shows exactly the converted amount "
                               "debited and the engine quote matches the tier spread, so "
                               "admitting an overcharge or promising a refund is wrong "
                               "whatever the wording; the pattern matches only affirmative "
                               "statements, because a bare 'overcharg' would also fail a "
                               "correct 'you were not overcharged'")}),
    ]

