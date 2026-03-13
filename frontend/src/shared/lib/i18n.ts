import { format, formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'

import type { BacktestRunStatus } from '@/entities/backtest/types'
import type { LogEntry } from '@/entities/log/types'
import type {
  ConnectionState,
  ExecutionMode,
  OrderRole,
  OrderState,
  PositionState,
  SessionStatus,
  SignalAction,
} from '@/entities/session/types'

type StrategyType = 'dsl' | 'plugin' | 'hybrid'

const strategyTypeLabels: Record<StrategyType, string> = {
  dsl: 'DSL',
  plugin: '플러그인',
  hybrid: '하이브리드',
}

const modeLabels: Record<ExecutionMode, string> = {
  BACKTEST: '백테스트',
  PAPER: '모의',
  LIVE: '실전',
}

const sessionStatusLabels: Record<SessionStatus, string> = {
  PENDING: '대기 중',
  RUNNING: '실행 중',
  STOPPING: '중지 중',
  STOPPED: '중지됨',
  FAILED: '실패',
}

const connectionStateLabels: Record<ConnectionState, string> = {
  CONNECTED: '연결됨',
  DISCONNECTED: '연결 끊김',
  RECONNECTING: '재연결 중',
  RECOVERED: '복구됨',
  DEGRADED: '성능 저하',
}

const positionStateLabels: Record<PositionState, string> = {
  NONE: '없음',
  OPENING: '진입 중',
  OPEN: '보유 중',
  CLOSING: '청산 중',
  CLOSED: '청산 완료',
  FAILED: '실패',
}

const orderStateLabels: Record<OrderState, string> = {
  CREATED: '생성됨',
  SUBMITTED: '제출됨',
  PARTIALLY_FILLED: '부분 체결',
  FILLED: '체결 완료',
  CANCELLED: '취소됨',
  REJECTED: '거부됨',
  EXPIRED: '만료됨',
  FAILED: '실패',
}

const orderRoleLabels: Record<OrderRole, string> = {
  ENTRY: '진입',
  EXIT: '청산',
  STOP_LOSS: '손절',
  TAKE_PROFIT: '익절',
}

const signalActionLabels: Record<SignalAction, string> = {
  ENTER: '진입',
  EXIT: '청산',
}

const backtestStatusLabels: Record<BacktestRunStatus, string> = {
  QUEUED: '대기 중',
  RUNNING: '실행 중',
  COMPLETED: '완료',
  FAILED: '실패',
  CANCELLED: '취소됨',
}

const severityLabels: Record<string, string> = {
  CRITICAL: '치명적',
  HIGH: '높음',
  MEDIUM: '보통',
  LOW: '낮음',
  WARN: '경고',
  WARNING: '경고',
  ERROR: '오류',
  INFO: '정보',
}

const logLevelLabels: Record<LogEntry['level'], string> = {
  debug: '디버그',
  info: '정보',
  warning: '경고',
  error: '오류',
  critical: '치명적',
}

const channelLabels: Record<string, string> = {
  system: '시스템',
  'strategy-execution': '전략 실행',
  'order-simulation': '주문 시뮬레이션',
  'risk-control': '리스크 제어',
  documents: '문서',
}

const exitReasonLabels: Record<string, string> = {
  STOP_LOSS: '손절',
  TAKE_PROFIT: '익절',
  TIME_STOP: '시간 청산',
  EMERGENCY_KILL: '긴급 종료',
  STRATEGY_EXIT: '전략 청산',
  STOP_LOSS_INTRA_BAR_CONSERVATIVE: '보수적 장중 손절',
}

export function formatRelativeTime(value: string | Date | null | undefined, fallback = '-'): string {
  if (!value) {
    return fallback
  }
  return formatDistanceToNow(new Date(value), { addSuffix: true, locale: ko })
}

export function formatDateTime(value: string | Date): string {
  return format(new Date(value), 'yyyy.MM.dd HH:mm', { locale: ko })
}

export function formatDate(value: string | Date): string {
  return format(new Date(value), 'yyyy.MM.dd', { locale: ko })
}

export function formatTime(value: string | Date): string {
  return format(new Date(value), 'HH:mm:ss', { locale: ko })
}

export function translateStrategyType(value: StrategyType | string): string {
  return strategyTypeLabels[value as StrategyType] ?? value.toUpperCase()
}

export function translateMode(value: ExecutionMode | string): string {
  return modeLabels[value as ExecutionMode] ?? value
}

export function translateSessionStatus(value: SessionStatus | string): string {
  return sessionStatusLabels[value as SessionStatus] ?? value
}

export function translateConnectionState(value: ConnectionState | string): string {
  return connectionStateLabels[value as ConnectionState] ?? value
}

export function translatePositionState(value: PositionState | string): string {
  return positionStateLabels[value as PositionState] ?? value
}

export function translateOrderState(value: OrderState | string): string {
  return orderStateLabels[value as OrderState] ?? value
}

export function translateOrderRole(value: OrderRole | string): string {
  return orderRoleLabels[value as OrderRole] ?? value
}

export function translateSignalAction(value: SignalAction | string): string {
  return signalActionLabels[value as SignalAction] ?? value
}

export function translateBacktestStatus(value: BacktestRunStatus | string): string {
  return backtestStatusLabels[value as BacktestRunStatus] ?? value
}

export function translateSeverity(value: string): string {
  return severityLabels[value.toUpperCase()] ?? value
}

export function translateLogLevel(value: LogEntry['level'] | string): string {
  return logLevelLabels[value as LogEntry['level']] ?? value
}

export function translateLogChannel(value: string): string {
  return channelLabels[value] ?? value
}

export function translateExitReason(value: string): string {
  return exitReasonLabels[value] ?? value
}
