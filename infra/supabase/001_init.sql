-- Coin Lab Supabase Migration 001_init.sql
-- Generated: 2026-03-12

-- 1. strategies
CREATE TABLE strategies (
    id text PRIMARY KEY,
    strategy_key text UNIQUE NOT NULL,
    name text NOT NULL,
    strategy_type text NOT NULL CHECK (strategy_type IN ('dsl', 'plugin', 'hybrid')),
    description text,
    is_active boolean NOT NULL DEFAULT true,
    latest_version_id text, -- FK added later to avoid circular dependency
    labels_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    latest_version_no integer,
    last_7d_return_pct numeric(20, 10),
    last_7d_win_rate numeric(20, 10),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_strategies_is_active ON strategies(is_active);
CREATE INDEX idx_strategies_updated_at_desc ON strategies(updated_at DESC);

-- 2. strategy_versions
CREATE TABLE strategy_versions (
    id text PRIMARY KEY,
    strategy_id text NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    version_no integer NOT NULL,
    schema_version text NOT NULL,
    config_json jsonb NOT NULL,
    config_hash text NOT NULL,
    labels jsonb NOT NULL DEFAULT '[]'::jsonb,
    notes text,
    is_validated boolean NOT NULL DEFAULT false,
    validation_summary jsonb,
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(strategy_id, version_no),
    UNIQUE(strategy_id, config_hash)
);

-- Now add the FK to strategies
ALTER TABLE strategies ADD CONSTRAINT fk_strategies_latest_version FOREIGN KEY (latest_version_id) REFERENCES strategy_versions(id) ON DELETE SET NULL;

-- 3. sessions
CREATE TABLE sessions (
    id text PRIMARY KEY,
    mode text NOT NULL CHECK (mode IN ('BACKTEST', 'PAPER', 'LIVE')),
    status text NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'STOPPING', 'STOPPED', 'FAILED')),
    strategy_version_id text NOT NULL REFERENCES strategy_versions(id) ON DELETE RESTRICT,
    symbol_scope_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    risk_overrides_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    config_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    performance_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    health_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    trace_id text NOT NULL,
    started_at timestamptz,
    ended_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_mode_status ON sessions(mode, status);
CREATE INDEX idx_sessions_started_at_desc ON sessions(started_at DESC);
CREATE INDEX idx_sessions_trace_id ON sessions(trace_id);

-- 4. signals
CREATE TABLE signals (
    id text PRIMARY KEY,
    session_id text NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    strategy_version_id text NOT NULL REFERENCES strategy_versions(id) ON DELETE RESTRICT,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    signal_action text NOT NULL CHECK (signal_action IN ('ENTER', 'EXIT', 'SCALE_IN', 'REDUCE', 'BLOCK')),
    confidence numeric(10, 6),
    reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
    explain_json jsonb,
    blocked boolean NOT NULL DEFAULT false,
    signal_price numeric(30, 10),
    snapshot_time timestamptz NOT NULL,
    dedupe_key text UNIQUE NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_signals_session_symbol_time ON signals(session_id, symbol, snapshot_time);
CREATE INDEX idx_signals_strategy_version_time ON signals(strategy_version_id, snapshot_time);

-- 5. positions
CREATE TABLE positions (
    id text PRIMARY KEY,
    session_id text NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    strategy_version_id text NOT NULL REFERENCES strategy_versions(id) ON DELETE RESTRICT,
    symbol text NOT NULL,
    position_state text NOT NULL CHECK (position_state IN ('NONE', 'OPENING', 'OPEN', 'CLOSING', 'CLOSED', 'FAILED')),
    side text NOT NULL DEFAULT 'LONG',
    entry_time timestamptz,
    exit_time timestamptz,
    avg_entry_price numeric(30, 10),
    avg_exit_price numeric(30, 10),
    quantity numeric(30, 10) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    invested_amount numeric(30, 10) NOT NULL DEFAULT 0,
    realized_pnl numeric(30, 10) NOT NULL DEFAULT 0,
    realized_pnl_pct numeric(20, 10) NOT NULL DEFAULT 0,
    stop_loss_price numeric(30, 10),
    take_profit_price numeric(30, 10),
    trailing_stop_price numeric(30, 10),
    closed_reason text,
    current_price numeric(30, 10),
    unrealized_pnl numeric(30, 10) NOT NULL DEFAULT 0,
    unrealized_pnl_pct numeric(20, 10) NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_positions_session_state ON positions(session_id, position_state);
CREATE INDEX idx_positions_symbol_state ON positions(symbol, position_state);
CREATE UNIQUE INDEX idx_positions_unique_open ON positions (session_id, strategy_version_id, symbol) 
WHERE position_state IN ('OPENING', 'OPEN', 'CLOSING');

-- 6. orders
CREATE TABLE orders (
    id text PRIMARY KEY,
    position_id text REFERENCES positions(id) ON DELETE SET NULL,
    session_id text NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    strategy_version_id text NOT NULL REFERENCES strategy_versions(id) ON DELETE RESTRICT,
    symbol text NOT NULL,
    order_role text NOT NULL CHECK (order_role IN ('ENTRY', 'EXIT', 'PARTIAL_EXIT', 'PROTECTIVE_STOP', 'TAKE_PROFIT', 'FALLBACK_MARKET')),
    order_type text NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT')),
    order_state text NOT NULL CHECK (order_state IN ('CREATED', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED', 'FAILED')),
    requested_price numeric(30, 10),
    executed_price numeric(30, 10),
    requested_qty numeric(30, 10) NOT NULL CHECK (requested_qty > 0),
    executed_qty numeric(30, 10) NOT NULL DEFAULT 0 CHECK (executed_qty >= 0),
    fee_amount numeric(30, 10) NOT NULL DEFAULT 0,
    slippage_bps numeric(20, 10) NOT NULL DEFAULT 0,
    retry_count integer NOT NULL DEFAULT 0,
    external_order_id text,
    idempotency_key text UNIQUE NOT NULL,
    submitted_at timestamptz,
    filled_at timestamptz,
    cancelled_at timestamptz,
    failure_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_session_symbol_time ON orders(session_id, symbol, created_at);
CREATE INDEX idx_orders_state ON orders(order_state);
CREATE INDEX idx_orders_external_order_id ON orders(external_order_id);

-- 7. backtest_runs
CREATE TABLE backtest_runs (
    id text PRIMARY KEY,
    strategy_version_id text NOT NULL REFERENCES strategy_versions(id) ON DELETE RESTRICT,
    symbols_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    timeframes_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    date_from timestamptz NOT NULL,
    date_to timestamptz NOT NULL CHECK (date_from < date_to),
    initial_capital numeric(30, 10) NOT NULL,
    execution_overrides_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL,
    metrics_json jsonb,
    trace_id text NOT NULL,
    queued_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_backtest_runs_strategy_version ON backtest_runs(strategy_version_id);
CREATE INDEX idx_backtest_runs_status ON backtest_runs(status);
CREATE INDEX idx_backtest_runs_completed_at_desc ON backtest_runs(completed_at DESC);

-- 8. backtest_trades
CREATE TABLE backtest_trades (
    id text PRIMARY KEY,
    backtest_run_id text NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    symbol text NOT NULL,
    entry_time timestamptz NOT NULL,
    exit_time timestamptz NOT NULL,
    entry_price numeric(30, 10) NOT NULL,
    exit_price numeric(30, 10) NOT NULL,
    qty numeric(30, 10) NOT NULL,
    pnl numeric(30, 10) NOT NULL,
    pnl_pct numeric(20, 10) NOT NULL,
    fee_amount numeric(30, 10) NOT NULL DEFAULT 0,
    slippage_amount numeric(30, 10) NOT NULL DEFAULT 0,
    exit_reason text NOT NULL
);

CREATE INDEX idx_backtest_trades_run_id ON backtest_trades(backtest_run_id);
CREATE INDEX idx_backtest_trades_symbol ON backtest_trades(symbol);

-- 9. backtest_equity_curve_points
CREATE TABLE backtest_equity_curve_points (
    id bigserial PRIMARY KEY,
    backtest_run_id text NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    time timestamptz NOT NULL,
    equity numeric(30, 10) NOT NULL,
    drawdown_pct numeric(20, 10) NOT NULL
);

CREATE INDEX idx_backtest_equity_run_time ON backtest_equity_curve_points(backtest_run_id, time);

-- 10. risk_events
CREATE TABLE risk_events (
    id text PRIMARY KEY,
    session_id text NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    strategy_version_id text REFERENCES strategy_versions(id) ON DELETE RESTRICT,
    symbol text,
    event_code text NOT NULL,
    severity text NOT NULL,
    payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    message text NOT NULL DEFAULT '',
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_risk_events_session_time ON risk_events(session_id, occurred_at);
CREATE INDEX idx_risk_events_code ON risk_events(event_code);

-- 11. universe_symbols
CREATE TABLE universe_symbols (
    id bigserial PRIMARY KEY,
    symbol text NOT NULL,
    turnover_24h_krw numeric(30, 10),
    surge_score numeric(10, 6),
    selected boolean NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 12. market_candles
CREATE TABLE market_candles (
    id bigserial PRIMARY KEY,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    time timestamptz NOT NULL,
    open numeric(30, 10) NOT NULL,
    high numeric(30, 10) NOT NULL,
    low numeric(30, 10) NOT NULL,
    close numeric(30, 10) NOT NULL,
    volume numeric(30, 10) NOT NULL,
    UNIQUE(symbol, timeframe, time)
);

CREATE INDEX idx_market_candles_symbol_timeframe_time ON market_candles(symbol, timeframe, time DESC);

-- 13. Log tables
CREATE TABLE system_logs (
    id bigserial PRIMARY KEY,
    level text NOT NULL,
    trace_id text,
    session_id text,
    strategy_version_id text,
    symbol text,
    event_type text NOT NULL,
    message text NOT NULL,
    payload_json jsonb,
    logged_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE strategy_execution_logs (
    id bigserial PRIMARY KEY,
    level text NOT NULL,
    trace_id text,
    session_id text,
    strategy_version_id text,
    symbol text,
    event_type text NOT NULL,
    message text NOT NULL,
    payload_json jsonb,
    logged_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE order_simulation_logs (
    id bigserial PRIMARY KEY,
    level text NOT NULL,
    trace_id text,
    session_id text,
    strategy_version_id text,
    symbol text,
    event_type text NOT NULL,
    message text NOT NULL,
    payload_json jsonb,
    logged_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE risk_control_logs (
    id bigserial PRIMARY KEY,
    level text NOT NULL,
    trace_id text,
    session_id text,
    strategy_version_id text,
    symbol text,
    event_type text NOT NULL,
    message text NOT NULL,
    payload_json jsonb,
    logged_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE document_change_logs (
    id bigserial PRIMARY KEY,
    level text NOT NULL,
    trace_id text,
    session_id text,
    strategy_version_id text,
    symbol text,
    event_type text NOT NULL,
    message text NOT NULL,
    payload_json jsonb,
    logged_at timestamptz NOT NULL DEFAULT now()
);

-- Common indexes for logs
CREATE INDEX idx_system_logs_session_time ON system_logs(session_id, logged_at);
CREATE INDEX idx_strategy_logs_session_time ON strategy_execution_logs(session_id, logged_at);
CREATE INDEX idx_order_logs_session_time ON order_simulation_logs(session_id, logged_at);
CREATE INDEX idx_risk_logs_session_time ON risk_control_logs(session_id, logged_at);
CREATE INDEX idx_doc_logs_session_time ON document_change_logs(session_id, logged_at);
