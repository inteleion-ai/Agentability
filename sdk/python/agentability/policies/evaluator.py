"""Policy evaluation system for enterprise safety and compliance.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import re
from typing import Any, Callable

from agentability.models import (
    Decision,
    PolicyType,
    PolicyViolation,
    ViolationSeverity,
)

# PII patterns used by the built-in no_pii rule.
_PII_PATTERNS: dict[str, str] = {
    "email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "phone": r"\b\d{3}[.\-]?\d{3}[.\-]?\d{4}\b",
}


class PolicyRule:
    """A single named policy rule with an attached evaluation function."""

    def __init__(
        self,
        rule_id: str,
        rule_type: PolicyType,
        description: str,
        evaluator: Callable[[Decision], tuple[bool, dict[str, Any]]],
        severity: ViolationSeverity,
        enabled: bool = True,
    ) -> None:
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.description = description
        self.evaluator = evaluator
        self.severity = severity
        self.enabled = enabled


class PolicyEvaluator:
    """Evaluate agent decisions against registered policy rules.

    Two default rules are active on instantiation:

    - ``no_pii``: Detects email / SSN / phone in ``output_data``. (CRITICAL)
    - ``max_cost``: Flags decisions where ``total_cost_usd`` > $0.05. (HIGH)

    Example:
        >>> evaluator = PolicyEvaluator()
        >>> violations = evaluator.evaluate_decision(decision, "my_agent")
    """

    def __init__(self) -> None:
        self.rules: dict[str, PolicyRule] = {}
        self._register_default_rules()

    def register_rule(self, rule: PolicyRule) -> None:
        """Add a policy rule to the evaluator."""
        self.rules[rule.rule_id] = rule

    def evaluate_decision(
        self, decision: Decision, agent_id: str
    ) -> list[PolicyViolation]:
        """Evaluate *decision* against all enabled rules.

        Returns:
            List of violations; empty list means full compliance.
        """
        violations: list[PolicyViolation] = []
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            try:
                is_compliant, details = rule.evaluator(decision)
            except Exception:  # noqa: BLE001
                continue
            if not is_compliant:
                violations.append(
                    PolicyViolation(
                        rule_id=rule.rule_id,
                        rule_description=rule.description,
                        severity=rule.severity,
                        agent_id=agent_id,
                        decision_id=decision.decision_id,
                        violation_details=details,
                    )
                )
        return violations

    def get_compliance_score(
        self, decisions: list[Decision]
    ) -> dict[str, Any]:
        """Return an aggregate compliance score over *decisions*.

        Penalty: CRITICAL=50, HIGH=20, MEDIUM=10, LOW=5, INFO=1.
        """
        if not decisions:
            return {
                "compliance_score": 100.0,
                "total_violations": 0,
                "by_severity": {},
                "critical_violations": 0,
            }

        counts: dict[str, int] = {
            "info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0
        }
        for decision in decisions:
            for v in self.evaluate_decision(decision, decision.agent_id):
                if v.severity.value in counts:
                    counts[v.severity.value] += 1

        total = sum(counts.values())
        penalty = (
            counts["critical"] * 50
            + counts["high"] * 20
            + counts["medium"] * 10
            + counts["low"] * 5
            + counts["info"] * 1
        )
        return {
            "compliance_score": max(0.0, 100.0 - penalty),
            "total_violations": total,
            "by_severity": counts,
            "critical_violations": counts["critical"],
        }

    # ------------------------------------------------------------------
    # Default rules
    # ------------------------------------------------------------------

    def _register_default_rules(self) -> None:
        def _no_pii(decision: Decision) -> tuple[bool, dict[str, Any]]:
            text = str(decision.output_data)
            found: dict[str, Any] = {}
            for pii_type, pattern in _PII_PATTERNS.items():
                matches = re.findall(pattern, text)
                if matches:
                    found[pii_type] = matches
            return (len(found) == 0, {"violations_found": found})

        def _max_cost(decision: Decision) -> tuple[bool, dict[str, Any]]:
            limit = 0.05
            actual = decision.total_cost_usd
            return (actual <= limit, {"actual_cost": actual, "cost_limit": limit})

        self.register_rule(
            PolicyRule(
                rule_id="no_pii",
                rule_type=PolicyType.CONTENT,
                description="Prevent PII in agent output data",
                evaluator=_no_pii,
                severity=ViolationSeverity.CRITICAL,
            )
        )
        self.register_rule(
            PolicyRule(
                rule_id="max_cost",
                rule_type=PolicyType.COST,
                description="Maximum $0.05 cost per decision",
                evaluator=_max_cost,
                severity=ViolationSeverity.HIGH,
            )
        )
