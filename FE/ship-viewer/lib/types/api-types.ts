// 🔹 API 응답 공통 래퍼
// 모든 API 응답에 사용되는 공통 타입
export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    message?: string;
    error?: string;
}
