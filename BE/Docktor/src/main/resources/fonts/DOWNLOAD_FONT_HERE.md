# 한글 폰트 다운로드 필요!

## 🚨 현재 상태
폰트 파일이 없어서 PDF에 한글이 표시되지 않습니다.

## 📥 해결 방법

### 1단계: 나눔고딕 폰트 다운로드

다음 링크 중 하나에서 다운로드하세요:

**옵션 A: 직접 다운로드 (가장 빠름)**
- https://github.com/naver/nanumfont/raw/master/fonts/NanumGothic.ttf
- 위 링크를 클릭하면 바로 다운로드됩니다

**옵션 B: 네이버 공식 사이트**
- https://hangeul.naver.com/font
- "나눔글꼴" 다운로드

**옵션 C: GitHub 릴리즈**
- https://github.com/naver/nanumfont/releases
- 최신 버전 다운로드

### 2단계: 폰트 파일 배치

다운로드한 `NanumGothic.ttf` 파일을:
```
src/main/resources/fonts/NanumGothic.ttf
```
**이 폴더에 복사하세요!**

### 3단계: 파일 구조 확인

다음과 같이 되어야 합니다:
```
src/main/resources/
└── fonts/
    ├── NanumGothic.ttf        👈 이 파일이 있어야 함!
    └── DOWNLOAD_FONT_HERE.md  (이 파일)
```

### 4단계: 애플리케이션 재시작

IntelliJ에서:
1. 실행 중인 애플리케이션 중지 (Ctrl+F2)
2. 다시 실행 (Shift+F10)

또는 터미널에서:
```bash
./gradlew bootRun
```

### 5단계: 확인

콘솔에 다음 메시지가 나타나야 합니다:
```
✅ NanumGothic font loaded from resources
```

그리고 브라우저에서 테스트:
```
http://localhost:8080/api/document/simple
```

한글이 정상적으로 표시됩니다! 🎉

---

## 🔧 문제 해결

### "여전히 한글이 안 나와요"

1. **파일명 확인**
   - 정확히 `NanumGothic.ttf` (대소문자 구분)
   - 공백이나 특수문자 없이

2. **경로 확인**
   ```
   src/main/resources/fonts/NanumGothic.ttf
   ```
   정확한 위치에 있는지 확인

3. **재시작 확인**
   - 애플리케이션을 완전히 종료하고 다시 시작

4. **콘솔 로그 확인**
   - "✅ Font loaded" 메시지가 나오는지 확인
   - "⚠️ WARNING" 메시지가 나오면 폰트가 로드되지 않은 것

### "다운로드가 안 돼요"

직접 다운로드 링크:
- https://github.com/naver/nanumfont/raw/master/fonts/NanumGothic.ttf

또는 브라우저 주소창에 복사해서 엔터!

---

## 💡 참고

- 무료 폰트입니다 (SIL 오픈 폰트 라이선스)
- 상업적 사용 가능
- 파일 크기: 약 2-3MB
