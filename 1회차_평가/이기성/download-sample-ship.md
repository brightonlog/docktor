# 샘플 선박 3D 모델 다운로드 가이드

## 빠른 테스트용 샘플 모델

### Option 1: Sketchfab 무료 모델 (추천)

#### 1. 간단한 화물선
```
URL: https://sketchfab.com/3d-models/cargo-ship-dbf9ff1dc59e4a2e9bb3fcff8c644e7c
다운로드: "Download 3D Model" 버튼 클릭 → GLB 선택
```

#### 2. 컨테이너 선박
```
URL: https://sketchfab.com/3d-models/container-ship-c7db8d9b5ee84d65be8e9b55f8e9d9b0
다운로드: GLB 포맷 선택
```

#### 3. 작은 화물선 (Low Poly)
```
검색: "cargo ship low poly free" on Sketchfab
필터: Downloadable + Free
포맷: GLB
```

### Option 2: 공식 샘플 모델

Khronos Group의 공식 glTF 샘플 모델 사용:

```
1. 방문: https://github.com/KhronosGroup/glTF-Sample-Models/tree/master/2.0

2. 아무 모델이나 선택 (예: DamagedHelmet, Fox 등)

3. glTF-Binary 폴더에서 .glb 파일 다운로드

4. ship.glb로 이름 변경
```

## 다운로드 후 설치

### Windows
```powershell
# 다운로드한 파일을 ship.glb로 이름 변경
# 아래 경로에 복사
C:\SSAFY\common-AI\ship-viewer\public\models\ship.glb
```

### 확인
1. 브라우저에서 http://localhost:3000 접속
2. "Use 3D Model File" 체크
3. 모델이 로드됨

## 직접 검색하기

### Sketchfab 검색 키워드
```
- "cargo ship free"
- "container ship"
- "vessel low poly"
- "ship game ready"
- "industrial ship"
```

### 필터 설정
```
☑️ Downloadable
☑️ Animated (선택)
☑️ Rigged (선택)
💰 Price: Free only
📦 Format: GLB
```

## 라이센스 확인

무료 모델 사용 시 주의사항:
- ✅ CC BY: 출처 표시 필요
- ✅ CC0: 자유 사용
- ❌ Editorial: 상업적 사용 불가
- ⚠️ 프로젝트 목적에 맞는 라이센스 확인

## 직접 다운로드 링크 (테스트용)

### 1. Khronos Sample - Duck
```bash
# 간단한 테스트용
curl -o public/models/ship.glb https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/Duck/glTF-Binary/Duck.glb
```

### 2. Khronos Sample - Avocado
```bash
curl -o public/models/ship.glb https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/Avocado/glTF-Binary/Avocado.glb
```

(실제 선박 모델은 Sketchfab에서 다운로드하세요)

## 포맷 확인

다운로드한 파일이 올바른지 확인:
```bash
# 파일 확장자 확인
# .glb 또는 .gltf여야 함

# Windows
dir public\models\ship.glb
```

## 문제 해결

### "Failed to load model" 에러
- 파일 경로가 정확한지 확인: `public/models/ship.glb`
- 파일이 손상되지 않았는지 확인
- 다른 모델로 테스트

### 모델이 화면에 안 보임
- 스케일 조정 (0.1 ~ 3.0)
- 카메라 거리 조정
- 모델이 원점에 있는지 확인

## 추천 워크플로우

1. **Sketchfab**에서 "cargo ship free" 검색
2. 마음에 드는 모델 선택
3. "Download 3D Model" 클릭
4. GLB 포맷 선택
5. `public/models/ship.glb`로 저장
6. 브라우저 새로고침
7. "Use 3D Model File" 체크

완료!
