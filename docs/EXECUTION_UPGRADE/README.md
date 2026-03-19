# EXECUTION_UPGRADE

## 문서 목적
- 현재 Coin Lab의 전략/실행 코어를 버전업하기 위한 전용 문서 묶음이다.
- 전략 파라미터 나열 중심 구조에서 벗어나, 분석 로직, 전략 조합 로직, 실행 로직을 분리한 구조로 고도화하기 위한 기준 문서를 보관한다.
- 이 폴더의 문서들은 기존 운영 문서와 별개가 아니라, 실제 코드베이스 개편 작업과 직접 연결되는 실행 문서로 사용한다.

## 읽는 순서
1. [01_LAYERED_EXECUTION_UPGRADE_PLAN.md](./01_LAYERED_EXECUTION_UPGRADE_PLAN.md)
   현재 코드베이스 분석, 목표 아키텍처, 디렉토리 변경안, 7단계 실행 계획, 단계별 검증 기준을 포함한 메인 계획 문서.
2. [02_DOMAIN_OBJECT_SPEC.md](./02_DOMAIN_OBJECT_SPEC.md)
   detector, composer, execution policy가 공통으로 사용하는 구조 객체와 setup/plan 객체 규격.
3. [03_DETECTOR_SPEC.md](./03_DETECTOR_SPEC.md)
   detector 계층의 인터페이스, 구현 우선순위, fixture/검증 기준.
4. [04_EXECUTION_POLICY_SPEC.md](./04_EXECUTION_POLICY_SPEC.md)
   실행 정책 계층의 모듈 경계, 기존 필드 매핑, 테스트 기준.
5. [05_MIGRATION_CHECKLIST.md](./05_MIGRATION_CHECKLIST.md)
   단계별 실제 이관 체크리스트와 회귀 점검 기준.

## 문서 구성
- [01_LAYERED_EXECUTION_UPGRADE_PLAN.md](./01_LAYERED_EXECUTION_UPGRADE_PLAN.md)
  전체 계획과 마일스톤 기준 문서.
- [02_DOMAIN_OBJECT_SPEC.md](./02_DOMAIN_OBJECT_SPEC.md)
  도메인 객체와 객체 간 경계 정의.
- [03_DETECTOR_SPEC.md](./03_DETECTOR_SPEC.md)
  구조 탐지 계층 정의.
- [04_EXECUTION_POLICY_SPEC.md](./04_EXECUTION_POLICY_SPEC.md)
  실행 정책 계층 정의.
- [05_MIGRATION_CHECKLIST.md](./05_MIGRATION_CHECKLIST.md)
  실제 작업 진행 체크리스트.

## 사용 규칙
- 구현 시작 전에는 반드시 메인 계획 문서의 현재 단계 범위, 선행 작업, 검증 기준을 먼저 확인한다.
- 단계 진행 중 구조 변경이나 책임 변경이 생기면 이 폴더 문서를 같은 작업에서 함께 업데이트한다.
- 네트워크 흐름, 런타임 소유권, 캐시/세션/심볼 선택 흐름에 영향이 생기면 [../NETWORK_FLOW_PLAYBOOK.md](../NETWORK_FLOW_PLAYBOOK.md)도 함께 검토하고 필요 시 업데이트한다.
