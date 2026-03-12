# ERROR_CODE_SPEC.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Purpose
This document standardizes all externally visible and internally significant error codes used by the project.

## Error response shape
All API errors must follow this shape:

```json
{
  "success": false,
  "error_code": "DSL_VALIDATION_FAILED",
  "message": "Strategy DSL validation failed",
  "trace_id": "trc_01HXYZ...",
  "timestamp": "2026-03-11T12:00:00.000Z",
  "details": {
    "path": "entry.rules[0].operator"
  }
}
```

## Error code categories
- `REQ_*` request validation
- `DSL_*` strategy DSL and plugin validation
- `EXEC_*` execution engine
- `RISK_*` risk controls
- `EVT_*` event ingestion and sequencing
- `DATA_*` data freshness and availability
- `LIVE_*` live trading safeguards
- `SYS_*` infrastructure/system

## Request / API codes
| Code | Meaning | Retryable |
|---|---|---|
| `REQ_INVALID_PAYLOAD` | Request body shape invalid | No |
| `REQ_MISSING_FIELD` | Required field missing | No |
| `REQ_INVALID_ENUM` | Invalid enum value | No |
| `REQ_CONFLICT` | Resource version conflict | No |
| `REQ_NOT_FOUND` | Resource not found | No |
| `REQ_UNAUTHORIZED_MODE` | Action not allowed in current mode | No |

## DSL codes
| Code | Meaning | Retryable |
|---|---|---|
| `DSL_VALIDATION_FAILED` | DSL schema or semantic validation failed | No |
| `DSL_UNKNOWN_OPERATOR` | Operator not defined in DSL spec | No |
| `DSL_INVALID_TIMEFRAME_REF` | Invalid cross-timeframe reference | No |
| `DSL_PLUGIN_LOAD_FAILED` | Plugin import or registration failed | No |
| `DSL_PLUGIN_CONTRACT_INVALID` | Plugin missing required methods | No |

## Execution codes
| Code | Meaning | Retryable |
|---|---|---|
| `EXEC_SNAPSHOT_STALE` | Snapshot too old for safe evaluation | Yes |
| `EXEC_DUPLICATE_SIGNAL_IGNORED` | Duplicate signal was ignored | No |
| `EXEC_ORDER_SUBMISSION_FAILED` | Order adapter submission failed | Yes |
| `EXEC_LIMIT_NOT_FILLED_TIMEOUT` | Limit order timed out unfilled | Depends |
| `EXEC_FALLBACK_MARKET_FAILED` | Fallback market order failed | Yes |
| `EXEC_POSITION_STATE_INVALID` | Position state transition invalid | No |

## Risk codes
| Code | Meaning | Retryable |
|---|---|---|
| `RISK_MAX_DRAWDOWN_REACHED` | Session drawdown threshold reached | No |
| `RISK_DAILY_LOSS_LIMIT_REACHED` | Daily loss cap reached | No |
| `RISK_DUPLICATE_POSITION_BLOCKED` | Duplicate position blocked | No |
| `RISK_MAX_CONCURRENT_POSITIONS_REACHED` | Position cap reached | No |
| `RISK_EMERGENCY_STOP_ACTIVE` | Emergency stop enabled | No |
| `RISK_POSITION_SIZE_REJECTED` | Calculated position size outside allowed bounds | No |

## Event/Data codes
| Code | Meaning | Retryable |
|---|---|---|
| `EVT_DUPLICATE_DROPPED` | Duplicate event dropped | No |
| `EVT_OUT_OF_ORDER_DROPPED` | Event arrived outside reorder window | No |
| `EVT_GAP_RECOVERY_INCOMPLETE` | Reconnect gap recovery incomplete | Yes |
| `DATA_REQUIRED_TIMEFRAME_MISSING` | Required candle/timeframe unavailable | Yes |
| `DATA_INDICATOR_BUILD_FAILED` | Indicator computation failed | Yes |
| `DATA_SYMBOL_DEGRADED` | Symbol data quality degraded | Yes |

## Live mode codes
| Code | Meaning | Retryable |
|---|---|---|
| `LIVE_CONFIRMATION_REQUIRED` | User confirmation missing for live action | No |
| `LIVE_API_KEY_MISSING` | Live credentials not configured | No |
| `LIVE_ORDER_REJECTED_BY_EXCHANGE` | Exchange rejected order | Depends |
| `LIVE_MODE_SWITCH_BLOCKED` | Live mode switch blocked by policy | No |

## System codes
| Code | Meaning | Retryable |
|---|---|---|
| `SYS_DB_WRITE_FAILED` | Database write failed | Yes |
| `SYS_QUEUE_OVERFLOW` | Internal queue overflow | Yes |
| `SYS_WS_DISCONNECTED` | Websocket disconnected | Yes |
| `SYS_TIMEOUT` | Timed operation exceeded timeout | Yes |
| `SYS_UNHANDLED_EXCEPTION` | Unexpected server exception | Maybe |

## HTTP mapping
| HTTP Status | Codes |
|---|---|
| 400 | `REQ_*`, `DSL_*` |
| 404 | `REQ_NOT_FOUND` |
| 409 | `REQ_CONFLICT` |
| 422 | semantic validation failures when request shape is valid but content invalid |
| 429 | retry/rate limit/system pressure cases |
| 500 | `SYS_*` |
| 503 | `SYS_WS_DISCONNECTED`, degraded live dependencies |

## UI behavior mapping
- Non-retryable validation errors: inline field error or blocking toast
- Retryable execution/data/system errors: banner + retry state
- Risk rejections: warning badge + persistent event log entry
- Live mode failures: modal + explicit user acknowledgment

## Logging requirements
Every error occurrence must log:
- `error_code`
- `trace_id`
- `component`
- `symbol` if applicable
- `strategy_id` if applicable
- retryability flag

## Reserved codes
These prefixes are reserved and must not be used ad hoc:
- `AUTH_*` (future authentication expansion)
- `BILLING_*` (not in scope)
- `MIG_*` (migration tooling only)
