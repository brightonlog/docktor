# DVC 사용 가이드

## 목차
1. [DVC란?](#dvc란)
2. [초기 설정 (처음 한 번만)](#초기-설정-처음-한-번만)
3. [팀원 - 프로젝트 클론 후 데이터 다운로드](#팀원---프로젝트-클론-후-데이터-다운로드)
4. [데이터 업데이트 방법](#데이터-업데이트-방법)
5. [주요 명령어](#주요-명령어)
6. [문제 해결](#문제-해결)

---

## DVC란?

DVC (Data Version Control)는 대용량 데이터 파일을 Git처럼 버전 관리할 수 있게 해주는 도구입니다.

### 왜 DVC를 사용하나요?
- Git은 대용량 파일 관리에 적합하지 않음
- 데이터셋이 크면 Git 저장소 크기가 급격히 증가
- DVC는 실제 데이터는 별도 저장소에 보관하고, Git에는 메타데이터만 저장

### 현재 프로젝트 구조
```
S14P11E201/
├── AI/kyr/
│   ├── images/          # DVC로 관리 (실제 데이터)
│   ├── labels/          # DVC로 관리 (실제 데이터)
│   ├── normal_images/   # DVC로 관리 (실제 데이터)
│   ├── images.dvc       # Git으로 관리 (메타데이터)
│   ├── labels.dvc       # Git으로 관리 (메타데이터)
│   └── normal_images.dvc # Git으로 관리 (메타데이터)
└── ../dvc-storage/      # 로컬 DVC 원격 저장소
```

---

## 초기 설정 (처음 한 번만)

### 1. DVC 설치

```bash
pip install dvc
```

### 2. 설정 확인

프로젝트를 클론한 후 DVC 설정이 이미 되어 있는지 확인:

```bash
# .dvc 폴더 존재 여부 확인
ls -la .dvc
```

이미 설정되어 있다면 다음 단계로 이동합니다.

---

## 팀원 - 프로젝트 클론 후 데이터 다운로드

### 1. Git 저장소 클론

```bash
git clone <repository-url>
cd S14P11E201
```

### 2. DVC 원격 저장소 경로 확인

```bash
dvc remote list
```

출력 예시:
```
myremote	../../dvc-storage
```

### 3. 데이터 다운로드

```bash
dvc pull
```

이 명령어가 다음을 수행합니다:
- `.dvc` 파일을 읽어서 필요한 데이터 확인
- DVC 원격 저장소(`../dvc-storage`)에서 실제 데이터 다운로드
- `AI/kyr/images/`, `AI/kyr/labels/`, `AI/kyr/normal_images/` 복원

### 4. 데이터 확인

```bash
ls AI/kyr/images
ls AI/kyr/labels
ls AI/kyr/normal_images
```

---

## 데이터 업데이트 방법

### 새로운 데이터를 추가하거나 수정했을 때

#### 1. DVC로 데이터 추적 업데이트

```bash
# 변경된 폴더를 DVC에 다시 추가
dvc add AI/kyr/images
# 또는
dvc add AI/kyr/labels
# 또는
dvc add AI/kyr/normal_images
```

#### 2. Git에 메타데이터 커밋

```bash
# 변경된 .dvc 파일을 Git에 추가
git add AI/kyr/images.dvc AI/kyr/.gitignore
git commit -m "Update training dataset"
```

#### 3. DVC 원격 저장소에 데이터 푸시

```bash
dvc push
```

#### 4. Git 푸시

```bash
git push
```

### 전체 워크플로우 예시

```bash
# 1. 데이터 수정 (예: 새 이미지 추가)
cp new_images/* AI/kyr/images/

# 2. DVC 추적 업데이트
dvc add AI/kyr/images

# 3. Git에 커밋
git add AI/kyr/images.dvc AI/kyr/.gitignore
git commit -m "Add 100 new training images"

# 4. 데이터 푸시
dvc push

# 5. Git 푸시
git push
```

---

## 주요 명령어

### 데이터 관리

```bash
# 데이터 다운로드
dvc pull

# 특정 파일만 다운로드
dvc pull AI/kyr/images.dvc

# 데이터 업로드
dvc push

# 데이터 상태 확인
dvc status

# 데이터 추적 추가
dvc add <directory>
```

### Git과 함께 사용

```bash
# 최신 코드 + 데이터 가져오기
git pull
dvc pull

# 변경사항 푸시
git add .
git commit -m "message"
git push
dvc push
```

### 원격 저장소 관리

```bash
# 원격 저장소 목록 확인
dvc remote list

# 원격 저장소 추가
dvc remote add -d <name> <url>

# 원격 저장소 수정
dvc remote modify <name> url <new-url>
```

---

## 문제 해결

### Q1. `dvc pull` 시 "failed to pull data from the cloud" 에러

**원인**: DVC 원격 저장소 경로에 접근할 수 없음

**해결**:
```bash
# 원격 저장소 경로 확인
dvc remote list

# 경로가 올바른지 확인
# 로컬 저장소 경로: ../../dvc-storage
ls ../../dvc-storage
```

### Q2. 데이터가 Git에 추가되는 경우

**원인**: `.gitignore`가 제대로 설정되지 않음

**해결**:
```bash
# .gitignore 확인
cat AI/kyr/.gitignore

# 다음 내용이 있어야 함:
# /images
# /labels
# /normal_images

# Git 캐시 정리
git rm -r --cached AI/kyr/images
git rm -r --cached AI/kyr/labels
git rm -r --cached AI/kyr/normal_images
```

### Q3. `dvc pull`이 너무 느림

**원인**: 대용량 파일 다운로드

**해결**:
```bash
# 특정 파일만 다운로드
dvc pull AI/kyr/images.dvc

# 또는 병렬 다운로드 설정
dvc config cache.type symlink
```

### Q4. 실수로 데이터를 삭제했을 때

**해결**:
```bash
# DVC로 데이터 복원
dvc checkout

# 특정 파일만 복원
dvc checkout AI/kyr/images.dvc
```

### Q5. DVC 캐시 삭제 (디스크 공간 확보)

```bash
# DVC 캐시 위치 확인
dvc cache dir

# 사용하지 않는 캐시 삭제
dvc gc -w

# 모든 캐시 삭제 (주의!)
dvc gc -w -a -c
```

---

## 추가 정보

### 프로젝트 통계

- 추적 중인 파일: 35,785개
- 총 데이터 크기: 약 58GB
- DVC 원격 저장소: `../dvc-storage` (로컬)

### 유용한 팁

1. **자동 스테이징 활성화**: DVC 변경사항을 자동으로 Git에 스테이징
   ```bash
   dvc config core.autostage true
   ```

2. **데이터 변경 전 백업**: 중요한 데이터는 변경 전 백업
   ```bash
   cp -r AI/kyr/images AI/kyr/images_backup
   ```

3. **정기적인 푸시**: 데이터 변경 후 바로 `dvc push`로 원격에 백업

### 참고 자료

- [DVC 공식 문서](https://dvc.org/doc)
- [DVC 튜토리얼](https://dvc.org/doc/start)
- [DVC Git 연동](https://dvc.org/doc/use-cases/versioning-data-and-model-files)

---

## 연락처

문제가 발생하면 팀 채널에 문의해주세요!
