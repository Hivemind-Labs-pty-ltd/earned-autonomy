"""Engine objects validate against the normative JSON Schemas in spec/schema/ (rule EA-6.15).

Uses `jsonschema` when it is installed; otherwise a small validator covering the keywords these schemas use.
"""
import json
import re
from dataclasses import asdict
from pathlib import Path

import pytest
from test_conformance import busy_engine

from earned_autonomy import OutcomeEvent

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "spec" / "schema"
OUTCOME_FIELDS = {field for field in OutcomeEvent.__dataclass_fields__}


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text())


def _type_ok(value, expected) -> bool:
    kinds = expected if isinstance(expected, list) else [expected]
    checks = {"string": lambda v: isinstance(v, str), "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
              "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
              "boolean": lambda v: isinstance(v, bool), "array": lambda v: isinstance(v, list),
              "object": lambda v: isinstance(v, dict), "null": lambda v: v is None}
    return any(checks[kind](value) for kind in kinds)


def minimal_errors(value, schema, path="$") -> list[str]:
    """A small JSON Schema validator for the keywords used in spec/schema/."""
    errors = []
    if "anyOf" in schema:
        if not any(not minimal_errors(value, option, path) for option in schema["anyOf"]):
            errors.append(f"{path}: matches no anyOf option")
        return errors
    if "type" in schema and not _type_ok(value, schema["type"]):
        return [f"{path}: expected {schema['type']}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{path}: {value!r} doesn't match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: not above exclusiveMinimum")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: not below exclusiveMaximum")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: too many items")
        prefix = schema.get("prefixItems", [])
        for index, item in enumerate(value):
            if index < len(prefix):
                errors += minimal_errors(item, prefix[index], f"{path}[{index}]")
            elif "items" in schema:
                errors += minimal_errors(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}: missing {name}")
        properties = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        for name, item in value.items():
            if name in properties:
                errors += minimal_errors(item, properties[name], f"{path}.{name}")
                continue
            matched = [p for p in patterns if re.search(p, name)]
            for p in matched:
                errors += minimal_errors(item, patterns[p], f"{path}.{name}")
            if matched:
                continue
            extra = schema.get("additionalProperties", True)
            if extra is False:
                errors.append(f"{path}: unexpected property {name}")
            elif isinstance(extra, dict):
                errors += minimal_errors(item, extra, f"{path}.{name}")
    return errors


def errors_for(value, schema) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return minimal_errors(value, schema)
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(map(str, error.path))}: {error.message}" for error in validator.iter_errors(value)]


@pytest.fixture(scope="module")
def trust_engine():
    return busy_engine(seed=7, n=1200)


@pytest.mark.covers("EA-6.15")
def test_engine_objects_validate_against_the_schemas(trust_engine):
    entries = list(trust_engine.record.entries())
    decisions = [entry.body for entry in entries if entry.type == "decision"]
    assert decisions
    decision_schema = load("decision")
    decision_fields = set(decision_schema["properties"])
    for body in decisions:
        core = {key: value for key, value in body.items() if key in decision_fields}
        assert not errors_for(core, decision_schema), errors_for(core, decision_schema)

    outcome_schema = load("outcome-event")
    outcomes = [entry.body for entry in entries if entry.type == "outcome"]
    assert outcomes
    for body in outcomes:
        assert set(body) == OUTCOME_FIELDS
        assert not errors_for(body, outcome_schema), errors_for(body, outcome_schema)

    state = trust_engine.live_state()
    state_schema = load("trust-state")
    assert state["states"]
    for snapshot in list(state["states"].values()) + list(state["reviewers"].values()):
        assert not errors_for(snapshot, state_schema), errors_for(snapshot, state_schema)

    policy_errors = errors_for(trust_engine.policy.to_dict(), load("policy"))
    assert not policy_errors, policy_errors

    from helpers import act
    action = act("customer_service.status.update", write_tools=["send_update"])
    action_errors = errors_for(action.to_dict(), load("proposed-action"))
    assert not action_errors, action_errors


@pytest.mark.covers("EA-6.15", "EA-6.11")
def test_record_entries_validate_against_the_schema(trust_engine):
    schema = load("record-entry")
    entries = list(trust_engine.record.entries())
    assert len(entries) > 100
    for entry in entries:
        found = errors_for(asdict(entry), schema)
        assert not found, (entry.sequence, entry.type, found)
