// 🔹 인증(Auth) 관련 타입들만 모아놓은 파일
import { ApiResponse } from './api-types';

// 🔹 로그인 시 보낼 데이터 (ID, PW)
export interface LoginRequest {
    corpCode: string;
    password: string;
}

// 🔹 기업 상세 정보 (이미지 응답 기반)
export interface CorpDto {
    corpId: number;
    corpCode: string;
    corpName: string;
    manager: string;
    phone: string | null;
    email: string | null;
    createDate: string;
}

// 🔹 로그인 최종 응답 데이터
export interface LoginResponse {
    success: boolean;
    message: string;
    accessToken: string;
    refreshToken: string;
    corp: CorpDto;
}

// 🔹 ApiResponse 재export (하위 호환성 유지)
export type { ApiResponse };