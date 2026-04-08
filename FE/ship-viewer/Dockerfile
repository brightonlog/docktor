# 1. 환경 설정
FROM node:20-alpine
WORKDIR /app

ARG NEXT_PUBLIC_API_BASE_URL
# 2. Next.js 빌드 시 환경 변수로 인식하게 설정
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# 2. 빌드에 필요한 파일 복사
COPY package*.json ./
RUN npm install

# 3. 전체 소스 복사 및 빌드 (out 폴더 안 만듦)
COPY . .
RUN npm run build

# 4. 서버 실행 (Next.js 자체 서버 사용)
EXPOSE 3000
CMD ["npm", "run", "start"]