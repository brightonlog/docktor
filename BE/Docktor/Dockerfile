# 1단계: 빌드 전용 컨테이너 (Gradle 8.10 + JDK 17 사용)
FROM gradle:8.10-jdk17 AS build
WORKDIR /app

# 소스 코드 전체 복사
COPY . .

# Gradle을 이용해 jar 빌드 (로컬 Java 버전과 상관없이 실행됨)
RUN chmod +x ./gradlew
RUN ./gradlew bootJar -x test

# 2단계: 실제 실행용 컨테이너 (경량화된 JRE 사용)
FROM eclipse-temurin:17-jdk-alpine
WORKDIR /app

# 빌드 컨테이너에서 생성된 jar만 가져옴
COPY --from=build /app/build/libs/*.jar app.jar

ENTRYPOINT ["java", "-jar", "app.jar"]