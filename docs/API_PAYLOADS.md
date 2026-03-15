# API_PAYLOADS.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 1. 목적
이 문서는 핵심 API의 request/response payload와 validation rule을 고정한다.  
`API_SPEC.md`가 endpoint 목록이라면, 이 문서는 실제 구현용 계약 명세다.

참조:
- 엔드포인트 목록: [API_SPEC.md](./API_SPEC.md)
- 에러 코드와 에러 형식: [ERROR_CODE_SPEC.md](./ERROR_CODE_SPEC.md)
- 충돌 정리 기준: [PRE_IMPLEMENTATION_CONFLICTS.md](./PRE_IMPLEMENTATION_CONFLICTS.md)

---

## 2. 공통 규칙

### 2.1 시간 포맷
- ISO 8601 UTC
- 예: `2026-03-10T00:15:00Z`

### 2.2 공통 응답 envelope
```json
{
  "success": true,
  "data": {},
  "meta": {},
  "trace_id": "trc_01HR...",
  "timestamp": "2026-03-11T12:00:00.000Z"
}
```

---

## 16. Monitoring summary

### GET `/api/v1/monitoring/summary`

#### Note
- This response is a populated-session example.
- On a fresh boot before any user-started session, `running_session_count` may be `0`.
- Default strategies can exist even when there are no running sessions yet.

#### Response
```json
{
  "success": true,
  "trace_id": "trc_014",
  "data": {
    "status_bar": {
      "running_session_count": 2,
      "paper_session_count": 1,
      "live_session_count": 1,
      "failed_session_count": 0,
      "degraded_session_count": 1,
      "active_symbol_count": 5
    },
    "strategy_cards": [
      {
        "strategy_id": "stg_001",
        "strategy_key": "btc_breakout",
        "strategy_name": "BTC Breakout",
        "strategy_type": "dsl",
        "latest_version_id": "stv_003",
        "latest_version_no": 3,
        "is_active": true,
        "is_validated": true,
        "active_session_count": 2,
        "last_7d_return_pct": 4.21,
        "last_signal_at": "2026-03-10T03:05:00Z"
      }
    ],
    "universe_summary": {
      "active_symbol_count": 5,
      "watchlist_symbol_count": 1,
      "with_open_position_count": 2,
      "with_recent_signal_count": 3,
      "symbols": [
        {
          "symbol": "KRW-BTC",
          "turnover_24h_krw": 152300000000,
          "surge_score": 0.93,
          "selected": true,
          "active_compare_session_count": 2,
          "has_open_position": true,
          "has_recent_signal": true,
          "risk_blocked": false
        }
      ]
    },
    "risk_overview": {
      "active_alert_count": 1,
      "blocked_signal_count_1h": 2,
      "daily_loss_limit_session_count": 0,
      "max_drawdown_session_count": 0,
      "items": [
        {
          "session_id": "ses_002",
          "severity": "WARN",
          "code": "DATA_SYMBOL_DEGRADED",
          "message": "ETH feed lag exceeds threshold",
          "created_at": "2026-03-10T03:04:20Z"
        }
      ]
    },
    "recent_signals": [
      {
        "id": "sig_001",
        "session_id": "ses_001",
        "strategy_version_id": "stv_003",
        "symbol": "KRW-BTC",
        "action": "ENTER",
        "signal_price": 143500000,
        "confidence": 0.78,
        "blocked": false,
        "reason_codes": ["EMA_BULLISH", "HH20_BREAKOUT"],
        "snapshot_time": "2026-03-10T03:05:00Z"
      }
    ]
  }
}
```

---

## 17. Session orders

### GET `/api/v1/sessions/{sessionId}/orders?symbol=KRW-BTC&page=1&page_size=50`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_015",
  "data": [
    {
      "id": "ord_001",
      "session_id": "ses_001",
      "strategy_version_id": "stv_003",
      "symbol": "KRW-BTC",
      "order_role": "ENTRY",
      "order_type": "LIMIT",
      "order_state": "FILLED",
      "requested_price": 143400000,
      "executed_price": 143500000,
      "requested_qty": 0.0025,
      "executed_qty": 0.0025,
      "retry_count": 0,
      "submitted_at": "2026-03-10T03:05:05Z",
      "filled_at": "2026-03-10T03:05:10Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total": 1,
    "has_next": false
  }
}
```

---

## 18. Session risk events

### GET `/api/v1/sessions/{sessionId}/risk-events?limit=100`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_016",
  "data": [
    {
      "id": "rsk_001",
      "session_id": "ses_002",
      "strategy_version_id": "stv_004",
      "severity": "WARN",
      "code": "DATA_SYMBOL_DEGRADED",
      "symbol": "KRW-ETH",
      "message": "ETH feed lag exceeds threshold",
      "payload_preview": {
        "late_event_count_5m": 6
      },
      "created_at": "2026-03-10T03:04:20Z"
    }
  ]
}
```

---

## 19. Session performance

### GET `/api/v1/sessions/{sessionId}/performance`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_017",
  "data": {
    "realized_pnl": 12000,
    "realized_pnl_pct": 1.2,
    "unrealized_pnl": -1800,
    "unrealized_pnl_pct": -0.18,
    "trade_count": 14,
    "win_rate_pct": 57.14,
    "max_drawdown_pct": -3.2
  }
}
```

---

## 20. Session manual reevaluate

### POST `/api/v1/sessions/{sessionId}/reevaluate`

#### Request
```json
{
  "symbols": ["KRW-BTC"]
}
```

#### Response
```json
{
  "success": true,
  "trace_id": "trc_017b",
  "data": {
    "accepted": true,
    "session_id": "ses_001",
    "requested_symbols": ["KRW-BTC"],
    "evaluated_symbols": ["KRW-BTC"],
    "skipped": []
  }
}
```

#### Note
- `symbols`를 비우면 현재 세션의 `active_symbols` 전체를 수동 재평가한다.
- 수동 재평가의 실행 로그는 `strategy-execution` 채널에 `trigger=ON_MANUAL_REEVALUATE`로 기록된다.
- stale snapshot 또는 degraded 상태면 `EVALUATION_SKIPPED`가 남고 실제 실행은 차단된다.

---

## 21. Backtest list

### GET `/api/v1/backtests?page=1&page_size=20`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_018",
  "data": [
    {
      "id": "btr_001",
      "status": "COMPLETED",
      "strategy_version_id": "stv_003",
      "symbols": ["KRW-BTC", "KRW-ETH"],
      "timeframes": ["5m"],
      "date_from": "2025-12-01T00:00:00Z",
      "date_to": "2026-03-01T00:00:00Z",
      "total_return_pct": 12.45,
      "trade_count": 28,
      "created_at": "2026-03-10T02:15:00Z",
      "completed_at": "2026-03-10T02:18:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "has_next": false
  }
}
```

---

## 22. Backtest performance

### GET `/api/v1/backtests/{runId}/performance`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_019",
  "data": {
    "total_return_pct": 12.45,
    "max_drawdown_pct": -4.2,
    "win_rate_pct": 57.14,
    "profit_factor": 1.62,
    "trade_count": 28,
    "avg_hold_minutes": 84.3,
    "sharpe_ratio": 1.18
  }
}
```

---

## 22. Backtest equity curve

### GET `/api/v1/backtests/{runId}/equity-curve`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_020",
  "data": [
    {
      "time": "2025-12-01T00:00:00Z",
      "equity": 1000000,
      "drawdown_pct": 0
    },
    {
      "time": "2026-01-15T00:00:00Z",
      "equity": 1078000,
      "drawdown_pct": -1.4
    },
    {
      "time": "2026-03-01T00:00:00Z",
      "equity": 1124500,
      "drawdown_pct": -4.2
    }
  ]
}
```

---

## 23. Backtest compare

### POST `/api/v1/backtests/{runId}/compare`

#### Request
```json
{
  "against_run_ids": ["btr_002", "btr_003"]
}
```

#### Response
```json
{
  "success": true,
  "trace_id": "trc_021",
  "data": {
    "base_run_id": "btr_001",
    "compared_runs": [
      {
        "run_id": "btr_002",
        "total_return_pct": 8.12,
        "max_drawdown_pct": -3.5,
        "win_rate_pct": 52.38,
        "profit_factor": 1.31,
        "trade_count": 21
      }
    ]
  }
}
```

### 2.3 공통 에러 envelope
```json
{
  "success": false,
  "error_code": "DSL_INVALID_ENUM",
  "message": "Unknown execution.entry_order_type",
  "details": {
    "field": "execution.entry_order_type",
    "allowed_values": ["market", "limit"]
  },
  "trace_id": "trc_01HR...",
  "timestamp": "2026-03-11T12:00:00.000Z"
}
```

### 2.4 pagination
```json
{
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 57,
    "has_next": true
  }
}
```

아래 예시들은 핵심 필드에 집중하기 위해 반복되는 envelope 필드를 일부 생략할 수 있다.  
생략되더라도 실제 구현 계약은 항상 2.2, 2.3, 2.4 규칙을 따른다.

---

## 3. 전략 생성

### POST `/api/v1/strategies`

#### Request
```json
{
  "strategy_key": "btc_breakout",
  "name": "BTC Breakout",
  "strategy_type": "dsl",
  "description": "EMA + breakout strategy",
  "labels": ["trend", "breakout"]
}
```

#### Validation
- `strategy_key`: lowercase snake/kebab only, unique
- `name`: 1~120 chars
- `strategy_type`: `dsl | plugin | hybrid`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_001",
  "data": {
    "id": "stg_001",
    "strategy_key": "btc_breakout",
    "name": "BTC Breakout",
    "strategy_type": "dsl",
    "description": "EMA + breakout strategy",
    "is_active": true,
    "latest_version_id": null,
    "labels": ["trend", "breakout"],
    "created_at": "2026-03-10T00:00:00Z",
    "updated_at": "2026-03-10T00:00:00Z"
  }
}
```

---

## 4. 전략 목록 조회

### GET `/api/v1/strategies?page=1&page_size=20&is_active=true&label=trend`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_002",
  "data": [
    {
      "id": "stg_001",
      "strategy_key": "btc_breakout",
      "name": "BTC Breakout",
      "strategy_type": "dsl",
      "latest_version_id": "stv_003",
      "latest_version_no": 3,
      "is_active": true,
      "labels": ["trend", "breakout"],
      "last_7d_return_pct": 4.21,
      "last_7d_win_rate": 58.33,
      "updated_at": "2026-03-10T01:10:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "has_next": false
  }
}
```

---

## 5. 전략 버전 생성

### POST `/api/v1/strategies/{strategyId}/versions`

#### Request
```json
{
  "schema_version": "1.0.0",
  "config_json": {
    "id": "btc_breakout_v3",
    "name": "BTC Breakout V3",
    "type": "dsl",
    "schema_version": "1.0.0",
    "market": {
      "exchange": "UPBIT",
      "market_types": ["KRW"],
      "timeframes": ["5m"],
      "trade_basis": "candle"
    },
    "universe": {
      "mode": "dynamic",
      "sources": ["top_turnover"],
      "max_symbols": 10,
      "refresh_sec": 60,
      "filters": { "min_24h_turnover_krw": 1000000000, "exclude_symbols": [] }
    },
    "entry": {
      "logic": "all",
      "conditions": []
    },
    "position": {
      "max_open_positions_per_symbol": 1,
      "allow_scale_in": false,
      "size_mode": "fixed_percent",
      "size_value": 0.1,
      "size_caps": { "min_pct": 0.02, "max_pct": 0.1 },
      "max_concurrent_positions": 4
    },
    "exit": {
      "stop_loss_pct": 0.015,
      "take_profit_pct": 0.03
    },
    "risk": {
      "daily_loss_limit_pct": 0.03,
      "max_strategy_drawdown_pct": 0.1,
      "prevent_duplicate_entry": true,
      "max_order_retries": 2,
      "kill_switch_enabled": true
    },
    "execution": {
      "entry_order_type": "limit",
      "exit_order_type": "limit",
      "limit_timeout_sec": 15,
      "fallback_to_market": true,
      "slippage_model": "fixed_bps",
      "fee_model": "per_fill"
    },
    "backtest": {
      "initial_capital": 1000000,
      "fee_bps": 5,
      "slippage_bps": 3,
      "latency_ms": 200,
      "fill_assumption": "next_bar_open"
    },
    "labels": [],
    "notes": ""
  },
  "labels": ["trend", "breakout"],
  "notes": "RSI filter removed"
}
```

#### Response
```json
{
  "success": true,
  "trace_id": "trc_003",
  "data": {
    "id": "stv_003",
    "strategy_id": "stg_001",
    "version_no": 3,
    "schema_version": "1.0.0",
    "config_hash": "sha256:abc123...",
    "labels": ["trend", "breakout"],
    "notes": "RSI filter removed",
    "created_at": "2026-03-10T02:00:00Z"
  }
}
```

---

## 6. 전략 검증

### POST `/api/v1/strategy-versions/{versionId}/validate`

#### Request
```json
{
  "strict": true
}
```

#### Response - success
```json
{
  "success": true,
  "trace_id": "trc_004",
  "data": {
    "valid": true,
    "errors": [],
    "warnings": [
      {
        "code": "DSL_UNIVERSE_TOP_TURNOVER_ONLY",
        "message": "No watchlist fallback configured"
      }
    ]
  }
}
```

#### Response - failure
```json
{
  "success": false,
  "error_code": "DSL_INVALID_PARTIAL_TP_SUM",
  "message": "Partial take-profit ratios exceed 1.0",
  "details": {
    "field": "exit.partial_take_profits",
    "sum": 1.2
  },
  "trace_id": "trc_004",
  "timestamp": "2026-03-11T12:00:00.000Z"
}
```

---

## 7. 백테스트 실행

### POST `/api/v1/backtests/run`

#### Request
```json
{
  "strategy_version_id": "stv_003",
  "symbols": ["KRW-BTC", "KRW-ETH"],
  "timeframes": ["5m"],
  "date_from": "2025-12-01T00:00:00Z",
  "date_to": "2026-03-01T00:00:00Z",
  "execution_overrides": {
    "fee_bps": 5,
    "slippage_bps": 3,
    "fill_assumption": "next_bar_open"
  }
}
```

#### Validation
- `date_from < date_to`
- symbol list 1~50
- timeframes는 strategy.market.timeframes의 부분집합 또는 명시적 override 허용 범위 내
- override는 문서 허용 키만 가능

#### Response
```json
{
  "success": true,
  "trace_id": "trc_005",
  "data": {
    "run_id": "btr_001",
    "status": "QUEUED",
    "strategy_version_id": "stv_003",
    "symbols": ["KRW-BTC", "KRW-ETH"],
    "date_from": "2025-12-01T00:00:00Z",
    "date_to": "2026-03-01T00:00:00Z",
    "queued_at": "2026-03-10T02:15:00Z"
  }
}
```

---

## 8. 백테스트 상세 조회

### GET `/api/v1/backtests/{runId}`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_006",
  "data": {
    "id": "btr_001",
    "status": "COMPLETED",
    "strategy_version_id": "stv_003",
    "symbols": ["KRW-BTC", "KRW-ETH"],
    "timeframes": ["5m"],
    "date_from": "2025-12-01T00:00:00Z",
    "date_to": "2026-03-01T00:00:00Z",
    "initial_capital": 1000000,
    "metrics": {
      "total_return_pct": 12.45,
      "max_drawdown_pct": -4.2,
      "win_rate_pct": 57.14,
      "profit_factor": 1.62,
      "trade_count": 28,
      "avg_hold_minutes": 84.3,
      "sharpe_ratio": 1.18
    },
    "created_at": "2026-03-10T02:15:00Z",
    "completed_at": "2026-03-10T02:18:00Z"
  }
}
```

---

## 9. 백테스트 거래 목록

### GET `/api/v1/backtests/{runId}/trades?page=1&page_size=50`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_007",
  "data": [
    {
      "id": "btt_001",
      "symbol": "KRW-BTC",
      "entry_time": "2026-01-04T05:00:00Z",
      "exit_time": "2026-01-04T07:15:00Z",
      "entry_price": 143000000,
      "exit_price": 145500000,
      "qty": 0.003,
      "pnl": 6000,
      "pnl_pct": 1.4,
      "fee_amount": 430,
      "slippage_amount": 260,
      "exit_reason": "TAKE_PROFIT"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total": 28,
    "has_next": false
  }
}
```

---

## 10. 세션 시작

### POST `/api/v1/sessions`

#### Request - PAPER
```json
{
  "mode": "PAPER",
  "strategy_version_id": "stv_003",
  "symbol_scope": {
    "mode": "dynamic",
    "sources": ["top_turnover", "surge"],
    "max_symbols": 10
  },
  "risk_overrides": {
    "daily_loss_limit_pct": 0.03
  },
  "confirm_live": false,
  "acknowledge_risk": false
}
```

#### Request - LIVE
```json
{
  "mode": "LIVE",
  "strategy_version_id": "stv_003",
  "symbol_scope": {
    "mode": "dynamic",
    "sources": ["top_turnover"],
    "max_symbols": 10
  },
  "risk_overrides": {},
  "confirm_live": true,
  "acknowledge_risk": true,
  "order_test_passed": true
}
```

#### Validation
- `mode`: `BACKTEST | PAPER | LIVE`
- `COIN_LAB_LIVE_REQUIRE_ORDER_TEST=true` 이면 `order_test_passed=true` 필수
- LIVE면 `confirm_live=true` 및 `acknowledge_risk=true` 필수
- `strategy_version_id`는 단일 값이어야 함
- `strategy_version_id`는 validated 상태여야 함

#### Response
```json
{
  "success": true,
  "trace_id": "trc_008",
  "data": {
    "id": "ses_001",
    "strategy_version_id": "stv_003",
    "mode": "PAPER",
    "status": "RUNNING",
    "symbol_scope": {
      "mode": "dynamic",
      "sources": ["top_turnover", "surge"],
      "max_symbols": 10,
      "active_symbols": ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
    },
    "started_at": "2026-03-10T03:00:00Z",
    "ended_at": null
  }
}
```

---

## 11. 세션 상세 조회

### GET `/api/v1/sessions/{sessionId}`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_009",
  "data": {
    "id": "ses_001",
    "mode": "PAPER",
    "status": "RUNNING",
    "strategy_version_id": "stv_003",
    "symbol_scope": {
      "active_symbols": ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
    },
    "started_at": "2026-03-10T03:00:00Z",
    "performance": {
      "realized_pnl": 12000,
      "realized_pnl_pct": 1.2,
      "unrealized_pnl": -1800,
      "unrealized_pnl_pct": -0.18
    },
    "health": {
      "connection_state": "OPEN",
      "snapshot_consistency": "HEALTHY",
      "late_event_count_5m": 2
    }
  }
}
```

---

## 12. 실시간 신호 조회

### GET `/api/v1/sessions/{sessionId}/signals?symbol=KRW-BTC&limit=100`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_010",
  "data": [
    {
      "id": "sig_001",
      "strategy_version_id": "stv_003",
      "symbol": "KRW-BTC",
      "timeframe": "5m",
      "action": "ENTER",
      "signal_price": 143500000,
      "confidence": 0.78,
      "reason_codes": ["EMA_BULLISH", "HH20_BREAKOUT"],
      "snapshot_time": "2026-03-10T03:05:00Z",
      "blocked": false,
      "explain_payload": {
        "snapshot_key": "KRW-BTC|5m|2026-03-10T03:05:00Z",
        "decision": "ENTER",
        "reason_codes": ["INDICATOR_COMPARE_MATCH", "PRICE_BREAKOUT_20"],
        "facts": [
          { "label": "ema20", "value": 143210125.51 },
          { "label": "ema50", "value": 142804991.18 },
          { "label": "close", "value": 143500000 },
          { "label": "highest_high20", "value": 143000000 },
          { "label": "entry.conditions[0].left.params.length", "value": 20 },
          { "label": "entry.conditions[0].right.params.length", "value": 50 },
          { "label": "entry.conditions[1].reference.params.lookback", "value": 20 },
          { "label": "entry.conditions[1].reference.params.exclude_current", "value": true }
        ],
        "parameters": [
          { "label": "entry.conditions[0].left.params.length", "value": 20 },
          { "label": "entry.conditions[0].right.params.length", "value": 50 },
          { "label": "entry.conditions[1].reference.params.lookback", "value": 20 },
          { "label": "entry.conditions[1].reference.params.exclude_current", "value": true }
        ],
        "matched_conditions": ["entry.conditions[0]", "entry.conditions[1]"],
        "failed_conditions": [],
        "risk_blocks": []
      }
    }
  ]
}
```

메모:
- `parameters`는 전략 파라미터 메타데이터를 별도로 제공한다.
- `facts`에는 계산값과 함께 UI 노출용 parameter 항목이 함께 포함될 수 있다.

---

## 13. 실시간 포지션 조회

### GET `/api/v1/sessions/{sessionId}/positions`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_011",
  "data": [
    {
      "id": "pos_001",
      "strategy_version_id": "stv_003",
      "symbol": "KRW-BTC",
      "position_state": "OPEN",
      "side": "LONG",
      "entry_time": "2026-03-10T03:05:10Z",
      "avg_entry_price": 143500000,
      "quantity": 0.0025,
      "stop_loss_price": 141347500,
      "take_profit_price": 147805000,
      "unrealized_pnl": 2300,
      "unrealized_pnl_pct": 0.64
    }
  ]
}
```

---

## 14. 세션 중지/킬

### POST `/api/v1/sessions/{sessionId}/stop`
#### Request
```json
{
  "reason": "manual_stop"
}
```

### POST `/api/v1/sessions/{sessionId}/kill`
#### Request
```json
{
  "reason": "operator_emergency",
  "close_open_positions": true
}
```

#### Response
```json
{
  "success": true,
  "trace_id": "trc_012",
  "data": {
    "session_id": "ses_001",
    "previous_status": "RUNNING",
    "current_status": "STOPPING",
    "reason": "manual_stop"
  }
}
```

---

## 15. 로그 조회

### GET `/api/v1/logs/strategy-execution?session_id=ses_001&limit=100`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_013",
  "data": [
    {
      "id": "log_001",
      "channel": "strategy-execution",
      "level": "INFO",
      "session_id": "ses_001",
      "strategy_version_id": "stv_003",
      "symbol": "KRW-BTC",
      "event_type": "EVALUATION_COMPLETED",
      "message": "Strategy evaluation completed",
      "payload": {
        "trigger": "ON_CANDLE_CLOSE",
        "snapshot_time": "2026-03-10T03:05:00Z",
        "source_event_type": "CANDLE_CLOSE",
        "source_trace_ids": ["trc_src_001", "trc_src_002"],
        "closed_timeframes": ["5m"],
        "updated_timeframes": ["1m", "5m", "15m"],
        "decision": "SIGNAL_EMITTED",
        "accepted": true,
        "signal_state": "ACCEPTED",
        "reason_codes": ["EMA_BULLISH", "HH20_BREAKOUT"],
        "blocked_codes": []
      },
      "logged_at": "2026-03-10T03:05:00Z"
    }
  ]
}
```

Typical `strategy-execution` events:
- `EVALUATION_STARTED`
- `EVALUATION_SKIPPED`
- `SIGNAL_EMITTED`
- `EVALUATION_COMPLETED`

### Additional log channels
- `GET /api/v1/logs/system`
- `GET /api/v1/logs/order-simulation?session_id=ses_001&limit=100`
- `GET /api/v1/logs/risk-control?session_id=ses_001&limit=100`

All log channels reuse the same log-entry envelope and only differ by `channel`.

---

## 24. Universe current

### GET `/api/v1/universe/current`

#### Response
```json
{
  "success": true,
  "trace_id": "trc_022",
  "data": [
    {
      "symbol": "KRW-BTC",
      "turnover_24h_krw": 152300000000,
      "surge_score": 0.93,
      "selected": true,
      "active_compare_session_count": 2,
      "has_open_position": true,
      "has_recent_signal": true,
      "risk_blocked": false
    }
  ]
}
```

---

## 25. Universe preview

### POST `/api/v1/universe/preview`

#### Request
```json
{
  "symbol_scope": {
    "mode": "dynamic",
    "sources": ["top_turnover", "surge"],
    "max_symbols": 4
  }
}
```

#### Response
```json
{
  "success": true,
  "trace_id": "trc_023",
  "data": {
    "symbols": ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP"],
    "count": 4
  }
}
```

---

## 26. Monitoring websocket snapshot

### WS `/ws/monitoring`

#### Message
```json
{
  "type": "monitoring_snapshot",
  "trace_id": "trc_024",
  "timestamp": "2026-03-11T16:30:00.000Z",
  "data": {
    "status_bar": {
      "running_session_count": 2,
      "paper_session_count": 1,
      "live_session_count": 1,
      "failed_session_count": 0,
      "degraded_session_count": 1,
      "active_symbol_count": 5
    }
  }
}
```

#### Heartbeat
```json
{
  "type": "heartbeat",
  "trace_id": "trc_024",
  "timestamp": "2026-03-11T16:30:05.000Z"
}
```

---

## 27. Chart websocket snapshot

### WS `/ws/charts/{symbol}?timeframe=5m&limit=200`

#### Snapshot message
```json
{
  "type": "chart_snapshot",
  "trace_id": "trc_025",
  "symbol": "KRW-BTC",
  "timeframe": "5m",
  "points": [
    {
      "time": "2026-03-11T15:55:00Z",
      "open": 143120000,
      "high": 143500000,
      "low": 143000000,
      "close": 143420000,
      "volume": 12.34
    }
  ]
}
```

#### Incremental update
```json
{
  "type": "chart_point",
  "trace_id": "trc_025",
  "symbol": "KRW-BTC",
  "timeframe": "5m",
  "point": {
    "time": "2026-03-11T16:00:00Z",
    "open": 143420000,
    "high": 143700000,
    "low": 143300000,
    "close": 143520000,
    "volume": 15.21
  }
}
```

---

## 28. Price websocket snapshot

### WS `/ws/prices?symbols=KRW-BTC,KRW-ETH`

#### Snapshot message
```json
{
  "type": "price_snapshot",
  "trace_id": "trc_026",
  "symbols": [
    {
      "symbol": "KRW-BTC",
      "price": 143520000,
      "timestamp": "2026-03-11T16:30:00.000Z"
    },
    {
      "symbol": "KRW-ETH",
      "price": 4230000,
      "timestamp": "2026-03-11T16:30:00.000Z"
    }
  ]
}
```

#### Incremental update
```json
{
  "type": "price_update",
  "trace_id": "trc_026",
  "symbol": "KRW-BTC",
  "price": 143540000,
  "timestamp": "2026-03-11T16:30:01.000Z"
}
```

#### Heartbeat
```json
{
  "type": "heartbeat",
  "trace_id": "trc_026",
  "timestamp": "2026-03-11T16:30:05.000Z"
}
```

#### Note
- The client should subscribe only to the active-symbol set for the selected monitoring session.
- Monitoring PnL rows can be derived client-side by combining this live price stream with `GET /api/v1/sessions/{sessionId}/positions`.

---

## 29. First-run and session-start semantics

### Fresh boot
- fresh boot does not auto-start PAPER or LIVE sessions
- default strategies and versions can already exist even when there are `0` running sessions
- monitoring payload examples in this document are populated-session examples, not guaranteed first-boot snapshots

### Session start contract
- `POST /api/v1/sessions` is the activation boundary for PAPER/LIVE execution
- when validation succeeds and runtime startup succeeds, the newly created session is expected to be returned as `RUNNING`
- `GET /api/v1/sessions/{sessionId}` immediately after a successful create call should also show `RUNNING`
- seeded/default strategies are launch candidates, not proof that execution is already running

### What RUNNING means
- `RUNNING` means the session is active and subscribed for runtime processing
- it does not guarantee that a signal, order, or position will be created immediately
- signals/orders/positions appear only when market snapshots satisfy the selected strategy
