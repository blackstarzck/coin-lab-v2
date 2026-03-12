# ARCHITECTURE.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## 상위 구조
1. Frontend App
2. FastAPI API Server
3. Market Ingest Worker
4. Strategy Runtime Worker
5. Execution Adapter
6. Backtest Worker
7. Persistence Layer

## 1. Frontend App
책임:
- 실시간 모니터링
- 전략 목록/상세/편집
- 백테스트 실행/비교
- 로그/상태 표시
금지:
- 전략 평가 로직 직접 수행
- 체결 계산 직접 수행

## 2. API Server
책임:
- 전략 CRUD
- 세션 시작/중지
- 백테스트 요청 접수
- 결과/로그 조회
- 실시간 상태 스트림 제공

## 3. Market Ingest Worker
책임:
- 업비트 WebSocket 연결
- raw event 수신 및 정규화
- 캔들/체결/지표 입력 생성
- candidate universe 갱신
핵심:
- 재연결
- dedupe
- 백프레셔 제어

## 4. Strategy Runtime Worker
책임:
- snapshot 수신
- 전략 평가
- signal 생성
- 포지션/리스크 체크
- order intent 생성

## 5. Execution Adapter
- BacktestExecutionAdapter
- PaperExecutionAdapter
- LiveExecutionAdapter

## 6. Backtest Worker
- 과거 데이터 로드
- 전략 런 실행
- 거래 목록 생성
- 성능 리포트 생성

## 7. Persistence Layer
- Supabase: 전략/버전/세션/로그/결과
- 로컬 저장소: 고빈도 시장 데이터 캐시

## 핵심 원칙
- raw -> normalized event -> snapshot -> evaluate -> execute
- Upbit raw payload를 도메인 로직에 직접 사용하지 않음
- event_time / received_time / processed_time 분리
- 계산 가능한 파생값은 중복 저장 최소화
