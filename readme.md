# 🚢 Docktor: 선박 검사 자동화를 위한 객체·이상 탐지 융합 AIoT 시스템

> **"안전한 검사, 정밀한 진단, 선박 유지보수의 디지털 전환"** 
> - 고소 작업의 위험을 제거하고 AI로 선체 결함을 자동 감지하는 온디바이스 AIoT 솔루션입니다.

---

## 1. 프로젝트 개요

* **목표**: 선박 검사원의 안전 확보 및 검사 효율성(비용 50% 절감, 시간 1/3 단축) 향상
* **배경**: 기존 육안 검사의 고위험·고비용 문제를 자동화 로봇 및 AI로 해결
* **기간**: 2026.01.12 ~ 2026.02.09 (6인 프로젝트)
* **인원**: 6인 | 이기성(팀장), 김예린, 김하은, 엄송현, 원서영, 진혜린



---



## 2. 주요 기능

| 기능 | 상세 내용 |
| --- | --- |
| **이중 결함 탐지** | **YOLOv8**로 녹·균열 등 4종 탐지 + **Autoencoder**로 미지의 이상 징후 감지 |
| **능동적 재촬영** | 결함이 잘릴 경우 로봇이 스스로 후진하여 최적의 이미지 확보 |
| **3D 시각화** | **Three.js**를 활용해 3D 선박 모델 위에 결함 위치 실시간 매핑 |
| **온디바이스 AI** | Jetson Orin Nano 기반의 독립형 현장 작동 시스템 |

1. YOLO 기반 실시간 결함 탐지
   ![실시간 검사.gif](Img%2F%EC%8B%A4%EC%8B%9C%EA%B0%84%20%EA%B2%80%EC%82%AC.gif)
2. LLM 기반 보고서 작성
   ![보고서 (online-video-cutter.com).gif](Img%2F%EB%B3%B4%EA%B3%A0%EC%84%9C%20%28online-video-cutter.com%29.gif)


---



## 3. 기술 스택

* **AI**: YOLOv8, PyTorch, TensorRT, Jetson Orin Nano, Timm, MLflow, Ultratics
* **Embedded**: Jetson Orin Car, Linux
* **Back-end**: Java 17, Spring Boot 3.4, Spring Security, Spring AI, ITextRenderer, SSE, MyBatis, MQTT Broker(Mosquitto), Paho MQTT
* **DataBase** : MySQL, Redis
* **Front-end**: React 19, Next.js 16, TypeScript, Three.js, Zustand, Tailwind
* **Infra/DevOps**: AWS(EC2, RDS, S3), Docker, Jenkins, Nginx


---



## 4. 서비스 흐름 및 아키텍처 구조

### 1. 서비스 흐름도 (선박 검사원)
1. 준비: 로봇 배치 및 웹에서 검사 대상(선박/영역) 선택
2. 검사: 로봇이 YOLO AI로 결함을 자동 탐지 및 촬영
3. 완료: 웹에서 결과 확인 및 LLM 기반 보고서 다운로드

![image.png](Img%2Fimage.png)


### 2. 아키텍처 구조
전체 시스템은 로봇 제어, AI 추론, 데이터 관리의 3단계로 흐릅니다.
1. **AI/Embedded**: Jetson Orin Nano에서 YOLO/TensorRT를 통한 실시간 추론 및 로봇 제어
2. **Back-end**: Spring Boot 기반의 데이터 관리, MQTT 통신, PDF 리포트 생성
3. **Front-end**: Next.js & Three.js 기반의 실시간 모니터링 및 대시보드

![프로젝트 아키텍처.drawio.png](Img%2F%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8%20%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98.drawio.png)


---


## 5. ERD 다이어그램
![ddd.png](Img%2Fddd.png)

---

## 6. Jetson Orin Car 시연
1. 현장 시연 (부산 강서구 신호항)
- ![s.jpeg](Img%2Fs.jpeg)
- ![IMG_9870.jpeg](Img%2FIMG_9870.jpeg)

2. 강의실 내부 시연
- ![20260206_121835.jpg](Img%2F20260206_121835.jpg)

---
## 7. 기능별 화면 (UI)

| 기능                     | 스크린샷                                                                        |
|------------------------|-----------------------------------------------------------------------------|
| **로그인**                | ![로그인](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20102852.png) |
| **배 목록**               | ![배목록](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20102902.png) |
| **배 상세(3D)**           | ![배 상세](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20102915.png) |
| **검사 이력**              |  ![검사 이력](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20103011.png)|
| **결함 목록**              |  ![결함 목록](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20103021.png)  |
| **결함 상세**              | ![결함상세](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20103029.png) |
| **검사 시작**              | ![모니터링](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20103305.png) |
| **LLM 기반 검사 보고서 다운로드** | ![보고서관리](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20103108.png) |
| **LLM 기반 검사 보고서 샘플**   | ![리포트샘플](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20103436.png) |
| **AI 실시간 분석 대시보드**     | ![실시간분석](Img%2F%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-02-06%20113900.png) |

## 📦 대용량 파일 다운로드

프로젝트 실행에 필요한 대용량 파일은 아래에서 다운로드할 수 있습니다:

### 모델 파일
- **patchcore_model.npz** (639MB)
  - 다운로드: [Google Drive 링크](https://drive.google.com/file/d/1NmshdjN9Np2TK3TyRotDcqM9ciCevVYb/view?usp=sharing)
  - 위치: `Embedded/lks/models/anomaly_detection/patchcore_model.npz`

### 테스트 영상
- **solidWhiteRight_input.mp4** (73MB)
  - 위치: `Embedded/yolo_project/Sub2/프로젝트 확장/solidWhiteRight_input.mp4`
  - *(선택사항) 테스트 영상이 필요한 경우 별도 다운로드*