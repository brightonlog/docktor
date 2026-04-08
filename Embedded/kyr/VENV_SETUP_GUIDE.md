# 🐍 Python 가상환경 설정 가이드 (Jetson Orin Nano)

Jetson에서 Python 가상환경을 사용하여 프로젝트를 실행하는 방법입니다.

---

## 🎯 왜 가상환경을 사용하나요?

### 장점
- ✅ **패키지 격리**: 프로젝트별 패키지 관리
- ✅ **의존성 관리**: 버전 충돌 방지
- ✅ **깔끔한 환경**: 시스템 Python 영향 없음

### Jetson의 특이사항
- ⚠️ OpenCV는 **시스템 패키지**로 설치되어 있음
- ⚠️ 가상환경에서 시스템 OpenCV를 **참조**해야 함
- ⚠️ `--system-site-packages` 옵션 필수!

---

## 🚀 빠른 설정 (자동)

### 1단계: 설정 스크립트 실행

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr
./setup_venv.sh
```

이 스크립트는 자동으로:
- 가상환경 생성 (`--system-site-packages` 옵션 포함)
- pip 업그레이드
- 필수 패키지 설치 (Flask, ultralytics, torch 등)
- OpenCV 확인

### 2단계: 가상환경 활성화

```bash
source venv/bin/activate
```
프롬프트가 `(venv)` 로 시작하면 성공!

### 3단계: 검사 시스템 실행

```bash
cd inspection
./run_manual_inspection.sh
# 또는
./run_inspection.sh
```

**실행 스크립트가 자동으로 가상환경을 활성화합니다!**

---

## 🔧 수동 설정 (상세)

자동 스크립트를 사용하지 않고 직접 설정하려면:

### 1. 가상환경 생성

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr

# --system-site-packages 옵션 필수!
python3 -m venv venv --system-site-packages
```

**중요**: `--system-site-packages` 옵션이 없으면 OpenCV를 찾을 수 없습니다!

### 2. 가상환경 활성화

```bash
source venv/bin/activate
```

### 3. pip 업그레이드

```bash
pip install --upgrade pip
```

### 4. 패키지 설치

```bash
# 웹 서버
pip install flask

# AI/ML
pip install ultralytics torch torchvision numpy

# 모터 제어 (자동 모드용)
pip install adafruit-circuitpython-pca9685
```

### 5. OpenCV 확인

```bash
python3 -c "import cv2; print(cv2.__version__)"
```

정상 출력:
```
4.5.4  (또는 다른 버전)
```

---

## 🔍 트러블슈팅

### ❌ ImportError: No module named 'cv2'

**원인**: 가상환경이 시스템 패키지를 참조하지 못함

**해결책 1**: 가상환경 재생성 (추천)

```bash
# 기존 가상환경 삭제
rm -rf venv

# --system-site-packages 옵션으로 재생성
python3 -m venv venv --system-site-packages
source venv/bin/activate
```

**해결책 2**: 시스템 OpenCV 경로 확인

```bash
# 시스템 Python에서 OpenCV 경로 확인
python3 -c "import cv2; print(cv2.__file__)"

# 출력 예: /usr/lib/python3/dist-packages/cv2/...
```

가상환경의 `site-packages`에 심볼릭 링크 생성:

```bash
# 가상환경 활성화 후
ln -s /usr/lib/python3/dist-packages/cv2 \
      $VIRTUAL_ENV/lib/python3.*/site-packages/
```

---

### ❌ python3-venv가 없다는 에러

**해결책**: python3-venv 설치

```bash
sudo apt-get update
sudo apt-get install python3-venv
```

---

### ❌ Adafruit PCA9685 import 실패

**원인**: I2C 권한 또는 하드웨어 문제

**해결책**:

```bash
# I2C 장치 확인
sudo i2cdetect -y -r 1

# 권한 추가
sudo usermod -aG i2c $USER
# 재로그인 필요

# 또는 수동 모드 사용 (모터 불필요)
cd inspection
./run_manual_inspection.sh
```

---

### ⚠️ torch/torchvision 설치 느림

**원인**: Jetson에서 torch 빌드에 시간이 오래 걸림

**해결책**: 인내심을 가지고 기다리거나, NVIDIA가 제공하는 사전 빌드 버전 사용

```bash
# PyTorch for Jetson (사전 빌드)
# https://forums.developer.nvidia.com/t/pytorch-for-jetson/
```

---

## 📝 가상환경 사용법

### 활성화

```bash
source venv/bin/activate
```

또는 짧게:

```bash
. venv/bin/activate
```

### 비활성화

```bash
deactivate
```

### 가상환경 확인

```bash
# 현재 활성화된 가상환경 경로
echo $VIRTUAL_ENV

# 설치된 패키지 목록
pip list
```

### 패키지 추가 설치

```bash
# 가상환경 활성화 후
pip install <package_name>
```

---

## 🎛️ 프로젝트 실행 방법

### 방법 1: 실행 스크립트 사용 (추천!)

실행 스크립트가 **자동으로 가상환경을 활성화**합니다.

```bash
cd inspection
./run_manual_inspection.sh   # 수동 모드
# 또는
./run_inspection.sh          # 자동 모드
```

### 방법 2: 수동으로 활성화 후 실행

```bash
# 1. 가상환경 활성화
source venv/bin/activate

# 2. 검사 시스템 실행
cd inspection
python3 orincar_inspection_manual.py
```

### 방법 3: 가상환경 없이 실행

시스템 Python으로 직접 실행:

```bash
cd inspection
python3 orincar_inspection_manual.py
```

**주의**: 시스템 전역에 패키지가 설치되어 있어야 합니다.

---

## 🔄 가상환경 vs 시스템 Python

| 항목 | 가상환경 | 시스템 Python |
|------|----------|--------------|
| **패키지 격리** | ✅ 격리됨 | ❌ 전역 공유 |
| **의존성 관리** | ✅ 프로젝트별 | ❌ 시스템 전체 |
| **OpenCV** | ✅ 시스템 참조 | ✅ 직접 사용 |
| **설정 복잡도** | ⚠️ 초기 설정 필요 | ✅ 바로 사용 |
| **권장** | ⭐⭐⭐ 개발/실습 | ⭐⭐ 빠른 테스트 |

---

## 📊 폴더 구조

```
kyr/
├── venv/                      # 가상환경 폴더 (자동 생성)
│   ├── bin/
│   │   ├── activate          # 활성화 스크립트
│   │   └── python3           # 가상환경 Python
│   ├── lib/
│   │   └── python3.*/
│   │       └── site-packages/  # 패키지 설치 위치
│   └── pyvenv.cfg
│
├── setup_venv.sh              # 가상환경 자동 설정 스크립트
├── inspection/
│   ├── run_manual_inspection.sh  # 수동 모드 (자동 venv 활성화)
│   └── run_inspection.sh         # 자동 모드 (자동 venv 활성화)
└── ...
```

---

## 💡 팁

### 1. .gitignore에 venv 추가

```bash
echo "venv/" >> .gitignore
```

가상환경 폴더는 Git에 커밋하지 않습니다.

### 2. requirements.txt 생성

```bash
# 가상환경 활성화 후
pip freeze > requirements.txt
```

다른 환경에서 복원:

```bash
pip install -r requirements.txt
```

### 3. 여러 프로젝트에서 사용

각 프로젝트마다 별도의 가상환경을 만들 수 있습니다:

```bash
python3 -m venv ~/project1/venv --system-site-packages
python3 -m venv ~/project2/venv --system-site-packages
```

### 4. 가상환경 이름 변경

기본 이름이 `venv`가 싫다면:

```bash
python3 -m venv my_custom_env --system-site-packages
source my_custom_env/bin/activate
```

### 5. Python 버전 확인

```bash
# 시스템 Python
python3 --version

# 가상환경 Python (활성화 후)
python --version
```

---

## 📋 체크리스트

가상환경 설정 완료 확인:

- [ ] `./setup_venv.sh` 실행 완료
- [ ] `source venv/bin/activate` 성공
- [ ] `python3 -c "import cv2; print(cv2.__version__)"` 정상 출력
- [ ] `pip list` 에서 flask, ultralytics 확인
- [ ] `cd inspection && ./run_manual_inspection.sh` 실행 성공
- [ ] 웹 브라우저에서 `http://<IP>:5003` 접속 성공

---

## 🆘 추가 도움말

### 공식 문서

- Python venv: https://docs.python.org/3/library/venv.html
- pip 사용법: https://pip.pypa.io/en/stable/user_guide/

### 관련 문서

- [README.md](README.md) - 프로젝트 메인
- [docs/QUICK_START.md](docs/QUICK_START.md) - 빠른 시작
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 폴더 구조

---

## 🎉 요약

```bash
# 1. 가상환경 설정 (한 번만)
./setup_venv.sh

# 2. 검사 시스템 실행 (실행 스크립트가 자동으로 venv 활성화)
cd inspection
./run_manual_inspection.sh

# 완료! 🎊
```

**가상환경을 사용하면 깔끔하게 패키지를 관리할 수 있습니다!**
