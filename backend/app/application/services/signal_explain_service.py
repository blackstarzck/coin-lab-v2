from __future__ import annotations

from copy import deepcopy
from typing import cast

from ...domain.entities.session import Signal

ExplainScalar = float | int | bool | str | None
ExplainItem = dict[str, ExplainScalar]
JsonObject = dict[str, object]

LEGACY_VALUE_TEXT = "legacy signal - value not persisted"
LEGACY_NOTE = "This signal was created before explain payload persistence. EMA/breakout values were not stored."


class SignalExplainService:
    def enrich_signal(self, signal: Signal, strategy_config: dict[str, object]) -> Signal:
        payload = signal.explain_payload if isinstance(signal.explain_payload, dict) else None
        if payload is not None and not self._requires_legacy_enrichment(payload, signal.reason_codes):
            return signal

        enriched = deepcopy(signal)
        enriched.explain_payload = self._build_legacy_payload(enriched, strategy_config)
        return enriched

    def _build_legacy_payload(self, signal: Signal, strategy_config: dict[str, object]) -> dict[str, object]:
        config = self._as_dict(strategy_config)
        action_node = self._as_dict(config.get("exit")) if signal.action == "EXIT" else self._as_dict(config.get("entry"))
        explain_path = "exit" if signal.action == "EXIT" else "entry"
        described = self._collect_condition_explain(action_node, explain_path, signal) if action_node else {
            "facts": [],
            "parameters": [],
            "conditions": [],
        }
        reason_codes = self._dedupe_strings(signal.reason_codes)
        facts = self._dedupe_items(
            ([self._item("signal_price", signal.signal_price)] if signal.signal_price is not None else [])
            + cast(list[ExplainItem], described["facts"])
        )
        parameters = self._dedupe_items(cast(list[ExplainItem], described["parameters"]))
        matched_conditions = [] if signal.blocked else (
            cast(list[str], described["conditions"]) if described["conditions"] else reason_codes
        )

        return {
            "snapshot_key": f"{signal.symbol}|{signal.timeframe}|{signal.snapshot_time.isoformat()}",
            "decision": "BLOCKED" if signal.blocked else signal.action,
            "reason_codes": reason_codes,
            "facts": facts,
            "parameters": parameters,
            "matched_conditions": self._dedupe_strings(matched_conditions),
            "failed_conditions": [],
            "risk_blocks": reason_codes if signal.blocked else [],
            "legacy_payload": True,
            "legacy_note": LEGACY_NOTE,
        }

    def _requires_legacy_enrichment(self, payload: dict[str, object], signal_reason_codes: list[str]) -> bool:
        if payload.get("legacy_payload") is True:
            return False

        matched_conditions = self._as_string_list(payload.get("matched_conditions"))
        failed_conditions = self._as_string_list(payload.get("failed_conditions"))
        parameters = self._as_item_list(payload.get("parameters"))
        facts = self._as_item_list(payload.get("facts"))
        reason_codes = self._as_string_list(payload.get("reason_codes")) or self._dedupe_strings(signal_reason_codes)
        only_legacy_reasons = bool(reason_codes) and all(code.startswith("MVP_STUB_") for code in reason_codes)
        non_signal_price_facts = [fact for fact in facts if str(fact.get("label", "")) != "signal_price"]

        return only_legacy_reasons and not matched_conditions and not failed_conditions and not parameters and not non_signal_price_facts

    def _collect_condition_explain(self, node: JsonObject, path: str, signal: Signal) -> dict[str, list[object]]:
        logic = self._as_string(node.get("logic")).lower()
        if logic in {"all", "any"}:
            aggregated = {"facts": [], "parameters": [], "conditions": []}
            for index, child in enumerate(self._as_list(node.get("conditions"))):
                child_result = self._collect_condition_explain(self._as_dict(child), f"{path}.conditions[{index}]", signal)
                aggregated["facts"].extend(child_result["facts"])
                aggregated["parameters"].extend(child_result["parameters"])
                aggregated["conditions"].extend(child_result["conditions"])
            return aggregated

        if logic == "not":
            described = self._collect_condition_explain(self._as_dict(node.get("condition")), f"{path}.condition", signal)
            return {
                "facts": described["facts"],
                "parameters": described["parameters"],
                "conditions": [f"{path}: NOT ({condition})" for condition in cast(list[str], described["conditions"])],
            }

        leaf_type = self._as_string(node.get("type"))
        if leaf_type in {"indicator_compare", "threshold_compare"}:
            left = self._collect_source_explain(self._as_dict(node.get("left")), f"{path}.left", signal)
            right = self._collect_source_explain(self._as_dict(node.get("right")), f"{path}.right", signal)
            return {
                "facts": [*left["facts"], *right["facts"]],
                "parameters": [*left["parameters"], *right["parameters"]],
                "conditions": [f"{path}: {self._format_source_summary(self._as_dict(node.get('left')))} {self._as_string(node.get('operator'), '>')} {self._format_source_summary(self._as_dict(node.get('right')))}"],
            }

        if leaf_type in {"cross_over", "cross_under"}:
            left = self._collect_source_explain(self._as_dict(node.get("left")), f"{path}.left", signal)
            right = self._collect_source_explain(self._as_dict(node.get("right")), f"{path}.right", signal)
            parameters = [*left["parameters"], *right["parameters"]]
            if isinstance(node.get("lookback_bars"), (int, float)):
                parameters.append(self._item(f"{path}.lookback_bars", int(node["lookback_bars"])))
            direction = "crosses above" if leaf_type == "cross_over" else "crosses below"
            return {
                "facts": [*left["facts"], *right["facts"]],
                "parameters": parameters,
                "conditions": [f"{path}: {self._format_source_summary(self._as_dict(node.get('left')))} {direction} {self._format_source_summary(self._as_dict(node.get('right')))}"],
            }

        if leaf_type == "price_breakout":
            source = self._collect_source_explain(self._as_dict(node.get("source")), f"{path}.source", signal)
            reference = self._collect_source_explain(self._as_dict(node.get("reference")), f"{path}.reference", signal)
            return {
                "facts": [*source["facts"], *reference["facts"]],
                "parameters": [*source["parameters"], *reference["parameters"]],
                "conditions": [f"{path}: {self._format_source_summary(self._as_dict(node.get('source')))} {self._as_string(node.get('operator'), '>')} {self._format_source_summary(self._as_dict(node.get('reference')))}"],
            }

        if leaf_type == "volume_spike":
            source = self._collect_source_explain(self._as_dict(node.get("source")), f"{path}.source", signal)
            facts = [*source["facts"]]
            parameters = [*source["parameters"]]
            if isinstance(node.get("threshold"), (int, float)):
                facts.append(self._item(f"{path}.threshold", float(node["threshold"])))
                parameters.append(self._item(f"{path}.threshold", float(node["threshold"])))
            return {
                "facts": facts,
                "parameters": parameters,
                "conditions": [f"{path}: {self._format_source_summary(self._as_dict(node.get('source')))} {self._as_string(node.get('operator'), '>=')} {node.get('threshold', '-')}"],
            }

        if leaf_type == "rsi_range":
            source = self._collect_source_explain(self._as_dict(node.get("source")), f"{path}.source", signal)
            parameters = [*source["parameters"]]
            if isinstance(node.get("min"), (int, float)):
                parameters.append(self._item(f"{path}.min", float(node["min"])))
            if isinstance(node.get("max"), (int, float)):
                parameters.append(self._item(f"{path}.max", float(node["max"])))
            return {
                "facts": source["facts"],
                "parameters": parameters,
                "conditions": [f"{path}: {self._format_source_summary(self._as_dict(node.get('source')))} in [{node.get('min', '-')}, {node.get('max', '-')}]"],
            }

        if leaf_type == "candle_pattern":
            parameters: list[ExplainItem] = []
            if isinstance(node.get("pattern"), str):
                parameters.append(self._item(f"{path}.pattern", str(node["pattern"])))
            if isinstance(node.get("timeframe"), str):
                parameters.append(self._item(f"{path}.timeframe", str(node["timeframe"])))
            return {
                "facts": [],
                "parameters": parameters,
                "conditions": [f"{path}: candle_pattern({self._as_string(node.get('pattern'), 'pattern')})"],
            }

        if leaf_type == "regime_match":
            parameters: list[ExplainItem] = []
            if isinstance(node.get("regime"), str):
                parameters.append(self._item(f"{path}.regime", str(node["regime"])))
            return {
                "facts": [],
                "parameters": parameters,
                "conditions": [f"{path}: regime_match({self._as_string(node.get('regime'), 'regime')})"],
            }

        return {
            "facts": [],
            "parameters": [],
            "conditions": [f"{path}: {leaf_type}"] if leaf_type else [],
        }

    def _collect_source_explain(self, ref: JsonObject, path: str, signal: Signal) -> dict[str, list[ExplainItem]]:
        kind = self._as_string(ref.get("kind")).lower()
        if not kind:
            return {"facts": [], "parameters": []}

        parameters: list[ExplainItem] = [self._item(f"{path}.kind", kind)]
        if isinstance(ref.get("timeframe"), str):
            parameters.append(self._item(f"{path}.timeframe", str(ref["timeframe"])))

        if kind == "price":
            field = self._as_string(ref.get("field"), "close")
            parameters.append(self._item(f"{path}.field", field))
            value: ExplainScalar = signal.signal_price if field == "close" and signal.signal_price is not None else LEGACY_VALUE_TEXT
            return {
                "facts": [self._item(self._build_source_label(ref), value)],
                "parameters": parameters,
            }

        if kind in {"indicator", "derived"}:
            name = self._as_string(ref.get("name"))
            if name:
                parameters.append(self._item(f"{path}.name", name))
            for key, value in self._as_dict(ref.get("params")).items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    parameters.append(self._item(f"{path}.params.{key}", cast(ExplainScalar, value)))
            return {
                "facts": [self._item(self._build_source_label(ref), LEGACY_VALUE_TEXT)],
                "parameters": parameters,
            }

        if kind == "constant":
            value = cast(ExplainScalar, ref.get("value"))
            parameters.append(self._item(f"{path}.value", value))
            return {
                "facts": [self._item(self._build_source_label(ref), value)],
                "parameters": parameters,
            }

        return {"facts": [], "parameters": parameters}

    def _build_source_label(self, ref: JsonObject) -> str:
        kind = self._as_string(ref.get("kind")).lower()
        if kind == "indicator":
            name = self._as_string(ref.get("name"), "indicator").lower()
            length = self._as_dict(ref.get("params")).get("length")
            return f"{name}{int(length)}" if isinstance(length, (int, float)) else name
        if kind == "derived":
            name = self._as_string(ref.get("name"), "derived").lower()
            lookback = self._as_dict(ref.get("params")).get("lookback")
            return f"{name}{int(lookback)}" if isinstance(lookback, (int, float)) else name
        if kind == "price":
            return self._as_string(ref.get("field"), "price").lower()
        if kind == "constant":
            return "constant"
        return "value"

    def _format_source_summary(self, ref: JsonObject) -> str:
        kind = self._as_string(ref.get("kind")).lower()
        if not kind:
            return "value"
        if kind == "price":
            return f"price.{self._as_string(ref.get('field'), 'close')}"
        if kind == "indicator":
            params = self._as_dict(ref.get("params"))
            length = params.get("length")
            name = self._as_string(ref.get("name"), "indicator")
            return f"{name}({int(length)})" if isinstance(length, (int, float)) else name
        if kind == "derived":
            params = self._as_dict(ref.get("params"))
            lookback = params.get("lookback")
            name = self._as_string(ref.get("name"), "derived")
            exclude_current = ", exclude_current=true" if params.get("exclude_current") is True else ""
            return f"{name}({int(lookback)}{exclude_current})" if isinstance(lookback, (int, float)) else name
        if kind == "constant":
            return f"constant({ref.get('value', '-')})"
        return kind

    def _item(self, label: str, value: ExplainScalar) -> ExplainItem:
        return {"label": label, "value": value}

    def _dedupe_items(self, items: list[ExplainItem]) -> list[ExplainItem]:
        seen: set[tuple[str, str]] = set()
        ordered: list[ExplainItem] = []
        for item in items:
            label = str(item.get("label", ""))
            value = item.get("value")
            key = (label, repr(value))
            if not label or key in seen:
                continue
            seen.add(key)
            ordered.append({"label": label, "value": cast(ExplainScalar, value)})
        return ordered

    def _dedupe_strings(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    def _as_dict(self, value: object) -> JsonObject:
        return cast(JsonObject, value) if isinstance(value, dict) else {}

    def _as_list(self, value: object) -> list[object]:
        return cast(list[object], value) if isinstance(value, list) else []

    def _as_string(self, value: object, fallback: str = "") -> str:
        return value if isinstance(value, str) else fallback

    def _as_string_list(self, value: object) -> list[str]:
        return [item for item in self._as_list(value) if isinstance(item, str)]

    def _as_item_list(self, value: object) -> list[ExplainItem]:
        return [cast(ExplainItem, item) for item in self._as_list(value) if isinstance(item, dict)]
