# 🔐 Docktor 환경 설정 가이드

## 신규 팀원 설정 방법

### 1️⃣ Git 클론 후 첫 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd Docktor
```

### 2️⃣ application-secret.properties 수정

IntelliJ에서 파일 열기:
```
src/main/resources/application-secret.properties
```

**수정 내용:**
```properties
spring.datasource.password=YOUR_PASSWORD_HERE
```
↓
```properties
spring.datasource.password=실제_RDS_비밀번호
```

### 3️⃣ Git 상태 확인

```bash
git status
```

✅ **정상:** `application-secret.properties`가 보이지 않아야 함  
❌ **비정상:** 파일이 보이면 `.gitignore` 확인 필요

### 4️⃣ 애플리케이션 실행

IntelliJ에서 실행 또는:
```bash
./gradlew bootRun
```

## 🚨 보안 주의사항

### ❌ 절대 하지 말 것

```bash
# 이렇게 커밋하지 마세요!
git add src/main/resources/application-secret.properties
git commit -m "Add secret config"  # 🔥 위험!
```

### ✅ 안전한 방법

```bash
# .gitignore가 자동으로 제외합니다
git add .
git commit -m "Update configuration"
# application-secret.properties는 자동 제외됨
```

## 📋 체크리스트

- [ ] `application-secret.properties` 파일 수정 완료
- [ ] RDS 비밀번호 입력 완료
- [ ] 애플리케이션 정상 실행 확인
- [ ] Git 상태에 secret 파일 없음 확인

## ❓ 문제 해결

### Q1. "application-secret.properties를 찾을 수 없습니다"
**A.** 파일이 누락되었습니다. 팀원에게 요청하거나 아래 내용으로 직접 생성:
```properties
spring.datasource.password=YOUR_PASSWORD_HERE
```

### Q2. "Access denied for user 'admin'"
**A.** RDS 비밀번호가 틀렸습니다. `application-secret.properties` 확인

### Q3. "Could not connect to database"
**A.** 
- RDS 보안 그룹 설정 확인
- VPN 또는 네트워크 연결 확인
- AWS RDS 상태 확인

---

**작성일**: 2026.01.20  
**데이터베이스**: AWS RDS MySQL  
**버전**: 1.0
