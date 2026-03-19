from __future__ import annotations

from collections.abc import Iterable
from typing import TypeGuard, cast

from ...core import error_codes
from ..strategy_runtime import StrategyComposerRegistry
from .strategy_plugin_registry import StrategyPluginRegistry


class StrategyValidator:
    MAX_CONDITION_DEPTH: int = 10

    REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
        "id",
        "name",
        "type",
        "schema_version",
        "market",
        "universe",
        "entry",
        "position",
        "exit",
        "risk",
        "execution",
        "backtest",
    )
    OPTIONAL_TOP_LEVEL_FIELDS: tuple[str, ...] = (
        "description",
        "enabled",
        "reentry",
        "labels",
        "notes",
        "hybrid",
        "execution_modules",
        "plugin_id",
        "plugin_version",
        "plugin_config",
    )
    LEAF_TYPES: tuple[str, ...] = (
        "indicator_compare",
        "threshold_compare",
        "cross_over",
        "cross_under",
        "price_breakout",
        "volume_spike",
        "rsi_range",
        "candle_pattern",
        "regime_match",
    )
    OPERATORS: tuple[str, ...] = (">", ">=", "<", "<=", "==", "!=")
    SOURCE_KINDS: tuple[str, ...] = ("price", "indicator", "derived", "constant")
    REGIMES: tuple[str, ...] = ("trend_up", "trend_down", "range", "high_volatility", "low_volatility")

    def __init__(
        self,
        plugin_registry: StrategyPluginRegistry | None = None,
        composer_registry: StrategyComposerRegistry | None = None,
    ) -> None:
        self.plugin_registry = plugin_registry or StrategyPluginRegistry()
        self.composer_registry = composer_registry or StrategyComposerRegistry()

    def validate(self, config_json: dict[str, object], strict: bool) -> dict[str, object]:
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        allowed_top_level = set(self.REQUIRED_TOP_LEVEL_FIELDS).union(self.OPTIONAL_TOP_LEVEL_FIELDS)
        for key in config_json:
            if key not in allowed_top_level:
                self._add_issue(
                    errors,
                    error_codes.DSL_UNKNOWN_TOP_LEVEL_KEY,
                    f"알 수 없는 최상위 키 '{key}'입니다.",
                    f"$.{key}",
                )
        for field_name in self.REQUIRED_TOP_LEVEL_FIELDS:
            if field_name not in config_json:
                self._add_issue(
                    errors,
                    error_codes.DSL_MISSING_REQUIRED_FIELD,
                    f"필수 필드 '{field_name}'가 없습니다.",
                    f"$.{field_name}",
                )

        strategy_type = self._validate_enum(
            config_json.get("type"),
            ("dsl", "plugin", "hybrid"),
            "$.type",
            errors,
        )

        market = self._as_dict(config_json.get("market"))
        universe = self._as_dict(config_json.get("universe"))
        position = self._as_dict(config_json.get("position"))
        exit_cfg = self._as_dict(config_json.get("exit"))
        risk = self._as_dict(config_json.get("risk"))
        execution = self._as_dict(config_json.get("execution"))
        backtest = self._as_dict(config_json.get("backtest"))
        entry = self._as_dict(config_json.get("entry"))
        reentry = self._as_dict(config_json.get("reentry"))
        hybrid = self._as_dict(config_json.get("hybrid"))
        execution_modules = config_json.get("execution_modules")
        plugin_id = config_json.get("plugin_id")
        plugin_version = config_json.get("plugin_version")
        plugin_config = config_json.get("plugin_config")

        _ = self._validate_enum(market.get("exchange"), ("UPBIT",), "$.market.exchange", errors)
        _ = self._validate_enum(market.get("trade_basis"), ("candle", "tick", "hybrid"), "$.market.trade_basis", errors)
        if "trigger" in market:
            _ = self._validate_enum(
                market.get("trigger"),
                ("ON_TICK_BATCH", "ON_CANDLE_CLOSE", "ON_CANDLE_UPDATE", "ON_MANUAL_REEVALUATE"),
                "$.market.trigger",
                errors,
            )
        timeframes = self._ensure_list(market.get("timeframes"))
        if self._has_duplicates(timeframes):
            self._add_issue(
                errors,
                error_codes.DSL_INVALID_THRESHOLD_RANGE,
                "market.timeframes에는 중복 값이 있으면 안 됩니다.",
                "$.market.timeframes",
            )

        universe_mode = self._validate_enum(universe.get("mode"), ("dynamic", "static"), "$.universe.mode", errors)
        sources = self._ensure_list(universe.get("sources"))
        if universe_mode == "dynamic":
            for index, source in enumerate(sources):
                _ = self._validate_enum(
                    source,
                    ("top_turnover", "top_volume", "surge", "drop", "watchlist"),
                    f"$.universe.sources[{index}]",
                    errors,
                )
        if universe_mode == "static":
            symbols = self._ensure_list(universe.get("symbols"))
            if len(symbols) == 0:
                self._add_issue(
                    errors,
                    error_codes.DSL_VALIDATION_FAILED,
                    "static 유니버스에는 최소 1개 이상의 심볼이 필요합니다.",
                    "$.universe.symbols",
                )
            if self._has_duplicates(symbols):
                self._add_issue(
                    errors,
                    error_codes.DSL_INVALID_THRESHOLD_RANGE,
                    "universe.symbols에는 중복 심볼이 있으면 안 됩니다.",
                    "$.universe.symbols",
                )

        size_mode = self._validate_enum(
            position.get("size_mode"),
            ("fixed_amount", "fixed_percent", "fractional_kelly", "risk_per_trade"),
            "$.position.size_mode",
            errors,
        )
        if "size_value" in position:
            self._validate_positive(position.get("size_value"), "$.position.size_value", errors)
        if size_mode == "fractional_kelly":
            size_value = position.get("size_value")
            if not self._is_number(size_value) or not (0 < float(size_value) <= 1):
                self._add_issue(
                    errors,
                    error_codes.DSL_INVALID_THRESHOLD_RANGE,
                    "fractional_kelly의 size_value는 0 < 값 <= 1 조건을 만족해야 합니다.",
                    "$.position.size_value",
                )

        size_caps = self._as_dict(position.get("size_caps"))
        min_pct = size_caps.get("min_pct")
        max_pct = size_caps.get("max_pct")
        if "min_pct" in size_caps:
            self._validate_unit_range(min_pct, "$.position.size_caps.min_pct", errors)
        if "max_pct" in size_caps:
            self._validate_unit_range(max_pct, "$.position.size_caps.max_pct", errors)
        if self._is_number(min_pct) and self._is_number(max_pct) and float(min_pct) > float(max_pct):
            self._add_issue(
                errors,
                error_codes.DSL_INVALID_THRESHOLD_RANGE,
                "position.size_caps.min_pct는 max_pct 이하여야 합니다.",
                "$.position.size_caps",
            )

        if "stop_loss_pct" in exit_cfg:
            self._validate_positive(exit_cfg.get("stop_loss_pct"), "$.exit.stop_loss_pct", errors)
        if "take_profit_pct" in exit_cfg:
            self._validate_positive(exit_cfg.get("take_profit_pct"), "$.exit.take_profit_pct", errors)
        if "trailing_stop_pct" in exit_cfg:
            self._validate_positive(exit_cfg.get("trailing_stop_pct"), "$.exit.trailing_stop_pct", errors)
        if "time_stop_bars" in exit_cfg:
            self._validate_positive_int(exit_cfg.get("time_stop_bars"), "$.exit.time_stop_bars", errors)
        partial_tps = self._ensure_list(exit_cfg.get("partial_take_profits"))
        total_close_ratio = 0.0
        for index, partial in enumerate(partial_tps):
            partial_map = self._as_dict(partial)
            close_ratio = partial_map.get("close_ratio")
            if self._is_number(close_ratio):
                total_close_ratio += float(close_ratio)
            else:
                self._add_issue(
                    errors,
                    error_codes.DSL_INVALID_PARTIAL_TP_SUM,
                    "partial_take_profits.close_ratio는 숫자여야 합니다.",
                    f"$.exit.partial_take_profits[{index}].close_ratio",
                )
        if total_close_ratio > 1.0:
            self._add_issue(
                errors,
                error_codes.DSL_INVALID_PARTIAL_TP_SUM,
                "partial_take_profits.close_ratio의 합계는 1.0 이하여야 합니다.",
                "$.exit.partial_take_profits",
            )

        if "daily_loss_limit_pct" in risk:
            self._validate_unit_range(risk.get("daily_loss_limit_pct"), "$.risk.daily_loss_limit_pct", errors)
        if "max_strategy_drawdown_pct" in risk:
            self._validate_unit_range(risk.get("max_strategy_drawdown_pct"), "$.risk.max_strategy_drawdown_pct", errors)

        if "entry_order_type" in execution:
            _ = self._validate_enum(execution.get("entry_order_type"), ("market", "limit"), "$.execution.entry_order_type", errors)
        if "exit_order_type" in execution:
            _ = self._validate_enum(execution.get("exit_order_type"), ("market", "limit"), "$.execution.exit_order_type", errors)
        if "slippage_model" in execution:
            _ = self._validate_enum(
                execution.get("slippage_model"),
                ("none", "fixed_bps", "volatility_scaled"),
                "$.execution.slippage_model",
                errors,
            )
        if "fee_model" in execution:
            _ = self._validate_enum(execution.get("fee_model"), ("per_fill", "per_order"), "$.execution.fee_model", errors)

        if "initial_capital" in backtest:
            self._validate_positive(backtest.get("initial_capital"), "$.backtest.initial_capital", errors)
        if "fee_bps" in backtest:
            self._validate_non_negative(backtest.get("fee_bps"), "$.backtest.fee_bps", errors)
        if "slippage_bps" in backtest:
            self._validate_non_negative(backtest.get("slippage_bps"), "$.backtest.slippage_bps", errors)
        if "fill_assumption" in backtest:
            _ = self._validate_enum(
                backtest.get("fill_assumption"),
                ("best_bid_ask", "mid", "next_tick", "next_bar_open"),
                "$.backtest.fill_assumption",
                errors,
            )

        timeframe_set = {str(timeframe) for timeframe in timeframes if isinstance(timeframe, str)}
        if strategy_type == "dsl":
            self._validate_condition_block(entry, "$.entry", 1, timeframe_set, errors)
        if reentry:
            if "cooldown_bars" in reentry:
                self._validate_non_negative_int(reentry.get("cooldown_bars"), "$.reentry.cooldown_bars", errors)
            reset_condition = self._as_dict(reentry.get("reset_condition"))
            if reset_condition:
                self._validate_condition_block(reset_condition, "$.reentry.reset_condition", 1, timeframe_set, errors)
        if strategy_type in {"dsl", "hybrid"} and isinstance(exit_cfg.get("logic"), str):
            self._validate_condition_block(exit_cfg, "$.exit", 1, timeframe_set, errors)

        if strategy_type == "dsl":
            for key in ("entry", "exit"):
                section = self._as_dict(config_json.get(key))
                if self._contains_plugin_markers(section):
                    self._add_issue(
                        errors,
                        error_codes.DSL_PLUGIN_AND_DSL_CONFLICT,
                        f"type이 'dsl'일 때는 {key}를 플러그인에 위임할 수 없습니다.",
                        f"$.{key}",
                    )
                if key == "entry" and not section:
                    self._add_issue(
                        errors,
                        error_codes.DSL_PLUGIN_AND_DSL_CONFLICT,
                        "type이 'dsl'일 때 entry는 비어 있을 수 없습니다.",
                        "$.entry",
                    )
        if strategy_type == "plugin":
            if not isinstance(plugin_id, str) or not plugin_id.strip():
                self._add_issue(
                    errors,
                    error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                    "type이 'plugin'일 때 plugin_id는 비어 있을 수 없습니다.",
                    "$.plugin_id",
                )
            if plugin_version is not None and (not isinstance(plugin_version, str) or not plugin_version.strip()):
                self._add_issue(
                    errors,
                    error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                    "plugin_version은 비어 있지 않은 문자열이어야 합니다.",
                    "$.plugin_version",
                )
            if plugin_config is not None and not isinstance(plugin_config, dict):
                self._add_issue(
                    errors,
                    error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                    "plugin_config는 객체여야 합니다.",
                    "$.plugin_config",
                )
            if isinstance(plugin_id, str) and plugin_id.strip():
                plugin = self.plugin_registry.get(plugin_id.strip())
                if plugin is None:
                    self._add_issue(
                        errors,
                        error_codes.DSL_PLUGIN_LOAD_FAILED,
                        f"등록되지 않은 plugin_id '{plugin_id}'입니다.",
                        "$.plugin_id",
                    )
                else:
                    if isinstance(plugin_version, str) and plugin_version.strip() and plugin_version.strip() != plugin.plugin_version:
                        self._add_issue(
                            errors,
                            error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                            f"plugin_version '{plugin_version}'이 등록 버전 '{plugin.plugin_version}'과 일치하지 않습니다.",
                            "$.plugin_version",
                        )
                    if plugin_config is None or isinstance(plugin_config, dict):
                        try:
                            plugin.validate(self._as_dict(plugin_config))
                        except ValueError as exc:
                            self._add_issue(
                                errors,
                                error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                                f"plugin_config 검증 실패: {exc}",
                                "$.plugin_config",
                            )
            self._add_issue(
                warnings,
                error_codes.DSL_PLUGIN_AND_DSL_CONFLICT,
                "전략 타입이 'plugin'이면 entry/exit DSL 블록은 무시됩니다.",
                "$.entry",
            )

        if strategy_type == "hybrid":
            composer_id = hybrid.get("composer_id")
            composer_config = hybrid.get("composer_config")
            if not isinstance(composer_id, str) or not composer_id.strip():
                self._add_issue(
                    errors,
                    error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                    "hybrid.composer_id must be a non-empty string.",
                    "$.hybrid.composer_id",
                )
            if composer_config is not None and not isinstance(composer_config, dict):
                self._add_issue(
                    errors,
                    error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                    "hybrid.composer_config must be an object.",
                    "$.hybrid.composer_config",
                )
            if execution_modules is not None and not isinstance(execution_modules, dict):
                self._add_issue(
                    errors,
                    error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                    "execution_modules must be an object.",
                    "$.execution_modules",
                )
            if isinstance(composer_id, str) and composer_id.strip():
                composer = self.composer_registry.get(composer_id.strip())
                if composer is None:
                    self._add_issue(
                        errors,
                        error_codes.DSL_PLUGIN_LOAD_FAILED,
                        f"Unknown hybrid composer '{composer_id}'.",
                        "$.hybrid.composer_id",
                    )
                elif composer_config is None or isinstance(composer_config, dict):
                    try:
                        composer.validate(self._as_dict(composer_config))
                    except ValueError as exc:
                        self._add_issue(
                            errors,
                            error_codes.DSL_PLUGIN_CONTRACT_INVALID,
                            f"hybrid.composer_config validation failed: {exc}",
                            "$.hybrid.composer_config",
                        )
            if entry:
                self._add_issue(
                    warnings,
                    error_codes.DSL_PLUGIN_AND_DSL_CONFLICT,
                    "type 'hybrid' ignores the top-level entry DSL block and uses hybrid.composer_id.",
                    "$.entry",
                )

        if strict:
            if universe_mode == "dynamic" and "watchlist" not in sources:
                self._add_issue(
                    warnings,
                    "DSL_UNIVERSE_TOP_TURNOVER_ONLY",
                    "universe.sources에 watchlist 소스가 설정되어 있지 않습니다.",
                    "$.universe.sources",
                )
            if reentry.get("allow") is False:
                self._add_issue(
                    warnings,
                    "DSL_REENTRY_DISABLED",
                    "reentry.allow이 false입니다.",
                    "$.reentry.allow",
                )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _validate_condition_block(
        self,
        node: dict[str, object],
        path: str,
        depth: int,
        timeframes: set[str],
        errors: list[dict[str, str]],
    ) -> None:
        if depth > self.MAX_CONDITION_DEPTH:
            self._add_issue(
                errors,
                error_codes.DSL_INVALID_CONDITION_DEPTH,
                f"조건식 깊이가 최대 허용치 {self.MAX_CONDITION_DEPTH}를 초과했습니다.",
                path,
            )
            return
        logic = node.get("logic")
        if isinstance(logic, str):
            if logic in {"all", "any"}:
                raw_conditions = node.get("conditions")
                if not isinstance(raw_conditions, list):
                    self._add_issue(errors, error_codes.DSL_VALIDATION_FAILED, "conditions는 배열이어야 합니다.", f"{path}.conditions")
                    return
                conditions = cast(list[object], raw_conditions)
                if len(conditions) == 0:
                    self._add_issue(
                        errors,
                        error_codes.DSL_EMPTY_CONDITIONS,
                        "conditions는 비어 있을 수 없습니다.",
                        f"{path}.conditions",
                    )
                    return
                for index, condition in enumerate(conditions):
                    condition_map = self._as_dict(condition)
                    if condition_map:
                        self._validate_condition_block(condition_map, f"{path}.conditions[{index}]", depth + 1, timeframes, errors)
                    else:
                        self._add_issue(
                            errors,
                            error_codes.DSL_VALIDATION_FAILED,
                            "조건식은 객체여야 합니다.",
                            f"{path}.conditions[{index}]",
                        )
                return
            if logic == "not":
                child = self._as_dict(node.get("condition"))
                if child:
                    self._validate_condition_block(child, f"{path}.condition", depth + 1, timeframes, errors)
                else:
                    self._add_issue(
                        errors,
                        error_codes.DSL_VALIDATION_FAILED,
                        "'not'은 단일 조건 객체를 필요로 합니다.",
                        f"{path}.condition",
                    )
                return
            self._add_issue(errors, error_codes.DSL_VALIDATION_FAILED, f"알 수 없는 논리 블록 '{logic}'입니다.", f"{path}.logic")
            return

        leaf_type = node.get("type")
        if not isinstance(leaf_type, str) or leaf_type not in self.LEAF_TYPES:
            self._add_issue(
                errors,
                error_codes.DSL_UNKNOWN_OPERATOR,
                f"알 수 없는 리프 조건 타입 '{leaf_type}'입니다.",
                f"{path}.type",
            )
            return

        operator = node.get("operator")
        if operator is not None and (not isinstance(operator, str) or operator not in self.OPERATORS):
            self._add_issue(
                errors,
                error_codes.DSL_UNKNOWN_OPERATOR,
                f"알 수 없는 연산자 '{operator}'입니다.",
                f"{path}.operator",
            )

        if leaf_type == "indicator_compare":
            self._validate_source_ref(node.get("left"), f"{path}.left", errors)
            self._validate_source_ref(node.get("right"), f"{path}.right", errors)
        elif leaf_type == "threshold_compare":
            self._validate_source_ref(node.get("left"), f"{path}.left", errors)
            self._validate_source_ref(node.get("right"), f"{path}.right", errors)
        elif leaf_type in {"cross_over", "cross_under"}:
            self._validate_source_ref(node.get("left"), f"{path}.left", errors)
            self._validate_source_ref(node.get("right"), f"{path}.right", errors)
        elif leaf_type == "price_breakout":
            self._validate_source_ref(node.get("source"), f"{path}.source", errors)
            self._validate_source_ref(node.get("reference"), f"{path}.reference", errors)
        elif leaf_type == "volume_spike":
            self._validate_source_ref(node.get("source"), f"{path}.source", errors)
        elif leaf_type == "rsi_range":
            self._validate_source_ref(node.get("source"), f"{path}.source", errors)
            min_value = node.get("min")
            max_value = node.get("max")
            if not self._is_number(min_value) or not self._is_number(max_value):
                self._add_issue(
                    errors,
                    error_codes.DSL_INVALID_THRESHOLD_RANGE,
                    "rsi_range.min과 rsi_range.max는 숫자여야 합니다.",
                    path,
                )
            else:
                min_float = float(min_value)
                max_float = float(max_value)
                if min_float > max_float or min_float < 0 or max_float > 100:
                    self._add_issue(
                        errors,
                        error_codes.DSL_INVALID_THRESHOLD_RANGE,
                        "rsi_range는 0 <= min <= max <= 100 조건을 만족해야 합니다.",
                        path,
                    )
        elif leaf_type == "candle_pattern":
            timeframe = node.get("timeframe")
            if isinstance(timeframe, str) and timeframe not in timeframes:
                self._add_issue(
                    errors,
                    error_codes.DSL_INVALID_TIMEFRAME_REFERENCE,
                    f"candle_pattern.timeframe '{timeframe}'이 market.timeframes에 없습니다.",
                    f"{path}.timeframe",
                )
        elif leaf_type == "regime_match":
            _ = self._validate_enum(node.get("regime"), self.REGIMES, f"{path}.regime", errors)

        self._validate_timeframe_refs(node, path, timeframes, errors)

    def _validate_timeframe_refs(
        self,
        value: object,
        path: str,
        timeframes: set[str],
        errors: list[dict[str, str]],
    ) -> None:
        if isinstance(value, dict):
            value_map = self._as_dict(cast(object, value))
            compare_to = value_map.get("compare_to")
            if isinstance(compare_to, str) and compare_to not in timeframes:
                self._add_issue(
                    errors,
                    error_codes.DSL_INVALID_TIMEFRAME_REFERENCE,
                    f"compare_to '{compare_to}'가 market.timeframes에 없습니다.",
                    f"{path}.compare_to",
                )
            for key, child in value_map.items():
                self._validate_timeframe_refs(child, f"{path}.{key}", timeframes, errors)
        elif isinstance(value, list):
            list_items = self._ensure_list(cast(object, value))
            for index, child in enumerate(list_items):
                self._validate_timeframe_refs(child, f"{path}[{index}]", timeframes, errors)

    def _validate_source_ref(self, value: object, path: str, errors: list[dict[str, str]]) -> None:
        if not isinstance(value, dict):
            self._add_issue(errors, error_codes.DSL_INVALID_SOURCE_REF, "SourceRef는 객체여야 합니다.", path)
            return
        source_ref = self._as_dict(cast(object, value))
        kind = source_ref.get("kind")
        if not isinstance(kind, str) or kind not in self.SOURCE_KINDS:
            self._add_issue(errors, error_codes.DSL_INVALID_SOURCE_REF, f"유효하지 않은 SourceRef kind '{kind}'입니다.", f"{path}.kind")
            return
        if kind == "price" and not isinstance(source_ref.get("field"), str):
            self._add_issue(errors, error_codes.DSL_INVALID_SOURCE_REF, "price SourceRef에는 'field'가 필요합니다.", f"{path}.field")
        if kind == "indicator" and not isinstance(source_ref.get("name"), str):
            self._add_issue(errors, error_codes.DSL_INVALID_SOURCE_REF, "indicator SourceRef에는 'name'이 필요합니다.", f"{path}.name")
        if kind == "constant" and "value" not in source_ref:
            self._add_issue(errors, error_codes.DSL_INVALID_SOURCE_REF, "constant SourceRef에는 'value'가 필요합니다.", f"{path}.value")

    def _validate_positive(self, value: object, path: str, errors: list[dict[str, str]]) -> None:
        if not self._is_number(value) or float(value) <= 0:
            self._add_issue(errors, error_codes.DSL_INVALID_THRESHOLD_RANGE, "값은 0보다 커야 합니다.", path)

    def _validate_non_negative(self, value: object, path: str, errors: list[dict[str, str]]) -> None:
        if not self._is_number(value) or float(value) < 0:
            self._add_issue(errors, error_codes.DSL_INVALID_THRESHOLD_RANGE, "값은 0 이상이어야 합니다.", path)

    def _validate_positive_int(self, value: object, path: str, errors: list[dict[str, str]]) -> None:
        if not isinstance(value, int) or value <= 0:
            self._add_issue(errors, error_codes.DSL_INVALID_THRESHOLD_RANGE, "값은 양의 정수여야 합니다.", path)

    def _validate_non_negative_int(self, value: object, path: str, errors: list[dict[str, str]]) -> None:
        if not isinstance(value, int) or value < 0:
            self._add_issue(errors, error_codes.DSL_INVALID_THRESHOLD_RANGE, "값은 0 이상의 정수여야 합니다.", path)

    def _validate_unit_range(self, value: object, path: str, errors: list[dict[str, str]]) -> None:
        if not self._is_number(value):
            self._add_issue(errors, error_codes.DSL_INVALID_THRESHOLD_RANGE, "값은 숫자여야 합니다.", path)
            return
        float_value = float(value)
        if float_value < 0 or float_value > 1:
            self._add_issue(errors, error_codes.DSL_INVALID_THRESHOLD_RANGE, "값은 [0, 1] 범위여야 합니다.", path)

    def _validate_enum(
        self,
        value: object,
        allowed: Iterable[str],
        path: str,
        errors: list[dict[str, str]],
    ) -> str | None:
        allowed_values = tuple(allowed)
        if not isinstance(value, str) or value not in allowed_values:
            self._add_issue(
                errors,
                error_codes.DSL_INVALID_ENUM,
                f"{path}의 enum 값이 올바르지 않습니다. 허용 값: {', '.join(allowed_values)}.",
                path,
            )
            return None
        return value

    def _add_issue(self, target: list[dict[str, str]], code: str, message: str, path: str) -> None:
        target.append({"code": code, "message": message, "path": path})

    def _ensure_list(self, value: object) -> list[object]:
        if isinstance(value, list):
            return cast(list[object], value)
        return []

    def _as_dict(self, value: object) -> dict[str, object]:
        if isinstance(value, dict):
            return cast(dict[str, object], value)
        return {}

    def _is_number(self, value: object) -> TypeGuard[int | float]:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _has_duplicates(self, values: list[object]) -> bool:
        normalized: list[object] = []
        for value in values:
            if isinstance(value, (str, int, float)):
                normalized.append(value)
            else:
                normalized.append(repr(value))
        return len(normalized) != len(set(normalized))

    def _contains_plugin_markers(self, section: dict[str, object]) -> bool:
        plugin_keys = {"plugin", "plugin_id", "plugin_ref", "plugin_name", "use_plugin", "delegate"}
        return any(key in section for key in plugin_keys)
