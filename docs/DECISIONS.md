# DECISIONS.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## D-001 제품 방향
전략 실험실 + 실전 트레이딩 콘솔을 동시에 지향한다.

## D-002 시장 범위
KRW / BTC / USDT 전체 시장 지원.

## D-003 전략 실행 단위
전략은 종목 독립형으로 평가한다.

## D-004 전략 정의 방식
JSON DSL + Python plugin 혼합 구조 채택.

## D-005 기술 스택
- Frontend: React + TypeScript + MUI + lightweight-charts + React Query + Zustand
- Backend: Python + FastAPI + Workers
- Storage: Supabase

## D-006 NestJS
MVP에서는 사용하지 않는다.

## D-007 감시 대상
동적 후보군 사용:
- 거래대금 상위
- 급등/급락
- 거래량 급증
- 워치리스트

## D-008 체결 모델
MVP:
- 수수료
- 슬리피지
- 지정가 미체결
- 재시도
- 취소 후 시장가 전환

## D-009 포지션 규칙
- 전략별 종목당 1포지션
- 같은 종목에 여러 전략 동시 진입 가능
- 계좌 전체 포지션 제한 가능

## D-010 자금 관리
Fractional Kelly + 상한/하한 캡 적용.

## D-011 실행 모드
BACKTEST / PAPER / LIVE

## D-012 아키텍처 패턴
이벤트 기반 수집 + 스냅샷 기반 전략 평가의 하이브리드.

## D-013 로그 저장
파일 로그 + Supabase 로그 동시 저장.

## D-014 개발 방식
문서 중심 개발 + AGENT.md 운영.

## D-015 편집 UX
Form + JSON 동기화 편집 방식 채택.
## D-016 Persistence materialization
- current API-facing session health and performance state is materialized in the session record
- current monitoring universe state is materialized in `universe_symbols`
- chart-ready OHLCV data is materialized in `market_candles`
- backtest equity curves are materialized in `backtest_equity_curve_points`
