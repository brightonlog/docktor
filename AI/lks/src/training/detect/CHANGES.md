# Training Module Changes

원격 서버 환경 최적화를 위한 변경사항

## 변경 일자

2026-01-25

## 변경 이유

원격 리눅스 서버 환경에서 localhost로 배포된 MLOps 서비스(MLflow UI, Prometheus, Grafana)에 접근할 수 없는 문제 해결

## 주요 변경사항

### 1. MLflow 파일 기반 저장으로 전환

**Before:**
```python
MLFLOW_TRACKING_URI = 'http://localhost:5000'
```

**After:**
```python
MLFLOW_TRACKING_URI = str(PROJECT_ROOT / 'mlruns')  # 파일 기반 저장
ENABLE_PROMETHEUS = False  # Prometheus exporter 비활성화
```

**영향:**
- MLflow UI 없이도 모든 실험 데이터가 `mlruns/` 디렉토리에 저장됨
- 메트릭, 파라미터, 아티팩트 모두 파일로 접근 가능
- 필요시 SSH 포트 포워딩으로 로컬에서 UI 확인 가능

### 2. run_training.sh 스크립트 간소화

**제거된 기능:**
- Docker Compose MLOps 서비스 시작
- Prometheus exporter 백그라운드 실행
- 서비스 대기 시간

**유지된 기능:**
- 데이터셋 검증
- 모델 학습 실행
- 결과 저장

**Before (4단계):**
1. MLOps 서비스 시작
2. 데이터셋 확인
3. Prometheus exporter 시작
4. 모델 학습

**After (2단계):**
1. 데이터셋 확인
2. 모델 학습

### 3. 문서 업데이트

**새로 추가된 문서:**
- `SETUP.md`: 원격 서버 환경 설정 가이드
- `CHANGES.md`: 이 파일

**업데이트된 문서:**
- `README.md`:
  - 파일 기반 MLflow 사용법 추가
  - Prometheus/Grafana 섹션 비활성화 표시
  - 원격 서버에서 결과 확인 방법 추가
  - Quick Start 섹션 추가
  - 결함 클래스 정보 수정 (5개 → 10개)

### 4. 파일별 변경 내역

#### src/config/training_config.py
```diff
# MLOps Config
- MLFLOW_TRACKING_URI = 'http://localhost:5000'
+ MLFLOW_TRACKING_URI = str(PROJECT_ROOT / 'mlruns')  # 파일 기반 저장
+ ENABLE_PROMETHEUS = False  # Prometheus exporter 비활성화
```

#### src/training/run_training.sh
- Docker compose 관련 코드 제거
- Prometheus exporter 시작 코드 제거
- Cleanup 함수 제거
- 완료 메시지를 파일 기반으로 수정

#### src/training/README.md
- 개요에 원격 서버 환경 명시 추가
- Quick Start 섹션 추가
- Prometheus exporter 섹션 비활성화 표시
- "원격 서버에서 결과 확인하기" 섹션 추가
- MLOps 통합 → 실험 추적 및 모니터링으로 섹션명 변경
- 파일 기반 메트릭 확인 방법 추가
- 결함 클래스 정보 업데이트

## 작동 방식

### 이전 방식 (MLOps UI 기반)

```
학습 시작
  ↓
Docker Compose로 MLflow/Prometheus/Grafana 시작
  ↓
Prometheus exporter 백그라운드 실행
  ↓
학습 실행 (메트릭을 HTTP로 MLflow로 전송)
  ↓
웹 브라우저로 UI 접속하여 확인
```

### 현재 방식 (파일 기반)

```
학습 시작
  ↓
학습 실행 (메트릭을 로컬 파일로 저장)
  ↓
mlruns/ 및 runs/ 디렉토리에 결과 저장
  ↓
파일 시스템에서 직접 확인 또는 SSH로 다운로드
```

## 사용자 영향

### 장점

1. **설정 간소화**: Docker, MLOps 서비스 불필요
2. **서버 독립적**: localhost 접근 불필요
3. **빠른 시작**: 서비스 대기 시간 없음
4. **파일 접근성**: 모든 결과가 파일로 저장되어 접근 용이
5. **리소스 절약**: 추가 서비스 실행 불필요

### 단점

1. **UI 없음**: 웹 기반 대시보드 직접 접근 불가
2. **실시간 시각화 제한**: Grafana 대시보드 사용 불가

### 대안

- **MLflow UI 필요시**: SSH 포트 포워딩 + `mlflow ui` 명령어
- **실시간 모니터링**: `tail -f results.csv` + `watch nvidia-smi`
- **시각화**: 학습 완료 후 생성된 PNG 파일 다운로드

## 호환성

### 영향 없음

- YOLOv8 학습 로직
- 데이터셋 준비 프로세스
- 모델 평가 기능
- 메트릭 수집 및 저장
- 모델 체크포인트

### 변경 필요

- MLOps UI 의존 워크플로우
- Prometheus/Grafana 대시보드
- 실시간 웹 모니터링 스크립트

## 롤백 방법

이전 방식으로 되돌리려면:

1. `src/config/training_config.py` 수정:
```python
MLFLOW_TRACKING_URI = 'http://localhost:5000'
ENABLE_PROMETHEUS = True
```

2. `docker-compose.mlops.yml` 실행:
```bash
docker-compose -f docker-compose.mlops.yml up -d
```

3. `run_training.sh`의 이전 버전 복구 (git history 참조)

## 테스트 필요 항목

- [ ] 데이터셋 준비 실행
- [ ] 학습 스크립트 실행
- [ ] MLflow 로그 파일 생성 확인
- [ ] 메트릭 CSV 생성 확인
- [ ] 모델 weights 저장 확인
- [ ] 평가 스크립트 실행

## 추가 개선 가능사항

1. **자동 백업**: 학습 완료 후 자동으로 결과 압축 및 백업
2. **이메일 알림**: 학습 완료 시 이메일 전송
3. **Slack 통합**: 학습 진행 상황을 Slack으로 전송
4. **TensorBoard**: MLflow 대신 TensorBoard 사용 고려
5. **WandB 통합**: Weights & Biases 클라우드 서비스 통합

## 관련 이슈

없음 (초기 설정)

## 작성자

Claude Code
