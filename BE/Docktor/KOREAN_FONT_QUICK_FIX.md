# 한글 깨짐 문제 해결 방법 (빠른 가이드)

## 🔴 문제
PDF에서 한글이 `()` 빈 괄호로 표시됨

## ✅ 해결 방법

### 방법 1: 나눔고딕 폰트 추가 (추천) ⭐

**1단계: 폰트 다운로드**
- https://github.com/naver/nanumfont/releases
- `NanumGothic.ttf` 파일 다운로드

**2단계: 폰트 파일 배치**
```
프로젝트/
└── src/
    └── main/
        └── resources/
            └── fonts/
                └── NanumGothic.ttf  👈 여기에 복사
```

**3단계: 애플리케이션 재시작**
```bash
./gradlew bootRun
```

**4단계: 테스트**
```
http://localhost:8080/api/document/deposit
```

### 방법 2: Windows 시스템 폰트 사용

Windows 사용자라면 **별도 작업 없이** 맑은 고딕이 자동으로 사용됩니다!

애플리케이션을 재시작하면 자동으로 작동합니다.

## 📝 확인 방법

### 성공한 경우
- PDF에서 한글이 정상적으로 표시됨
- "공탁신청서", "신청인" 등 한글이 보임

### 실패한 경우
- PDF에서 한글이 `()` 빈 괄호로 표시됨
- 콘솔에 "Warning: Korean font not found" 메시지

## 🔧 추가 문제 해결

### 폰트를 추가했는데도 안 될 때

1. **파일명 확인**
   - 정확히 `NanumGothic.ttf` (대소문자 구분)
   - 공백이나 특수문자 없이

2. **경로 확인**
   ```
   src/main/resources/fonts/NanumGothic.ttf
   ```

3. **Gradle 빌드**
   ```bash
   ./gradlew clean build
   ./gradlew bootRun
   ```

4. **IntelliJ 캐시 초기화**
   - File → Invalidate Caches / Restart
   - Invalidate and Restart 클릭

## 💡 더 자세한 내용

자세한 설명은 다음 파일을 참고하세요:
```
src/main/resources/fonts/README.md
```

## 🎯 권장 폰트

| 폰트 | 다운로드 링크 |
|------|--------------|
| 나눔고딕 | https://github.com/naver/nanumfont |
| 나눔명조 | https://github.com/naver/nanumfont |
| 나눔바른고딕 | https://hangeul.naver.com/font |

## ✨ 작동 원리

1. `PdfService` 생성 시 한글 폰트를 로드합니다
2. 우선순위:
   - ① `resources/fonts/NanumGothic.ttf` (프로젝트 폰트)
   - ② `c:/windows/fonts/malgun.ttf` (Windows 시스템 폰트)
   - ③ 기본 폰트 (한글 지원 안 됨)

3. PDF 생성 시 로드된 한글 폰트를 사용합니다

## 📞 여전히 안 될 때

콘솔 로그의 에러 메시지를 확인하고 공유해주세요!
