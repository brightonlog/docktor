import {ApiResponse} from "@/lib/types/api-types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

// 🔹 토큰 관리 인터페이스 (전역에서 주입받음)
interface TokenManager {
    getAccessToken: () => string | null;
    getRefreshToken: () => string | null;
    setAccessToken: (token: string) => void;
    logout: () => void;
    redirectToLogin: () => void;
}

let tokenManager: TokenManager | null = null;

// 🔹 토큰 매니저 설정 (앱 초기화 시 호출)
export function setTokenManager(manager: TokenManager) {
    tokenManager = manager;
}

// 🔹 범용 API 요청 (응답 형식 자유)
async function apiFetch<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {

    try {

        const response = await fetch(`${API_BASE_URL}${endpoint}`,
            {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
                ...options,
            });
        if (response.status === 401) {
            throw new Error('TOKEN_EXPIRED');
        }

        if (response.status === 403) {
            throw new Error('FORBIDDEN');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || '요청에 실패했습니다.');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// 🔹 토큰 재발급 함수
async function refreshAccessToken(): Promise<string | null> {
    if (!tokenManager) {
        console.error('TokenManager not initialized');
        return null;
    }

    const refreshToken = tokenManager.getRefreshToken();
    if (!refreshToken) {
        return null;
    }

    try {
        console.log("액세스 토큰 만료, 재발급 시도")
        const response = await publicFetch<{ accessToken: string }>('/api/auth/refresh', {
            method: 'POST',
            body: JSON.stringify({ refreshToken }),
        });
        
        const newAccessToken = response.accessToken;
        console.log("재발급 완료!",newAccessToken)
        if (newAccessToken) {
            tokenManager.setAccessToken(newAccessToken);
            return newAccessToken;
        }
        return null;
    } catch (error) {
        console.error('Token refresh failed:', error);
        return null;
    }
}

// 🔹 인증이 필요한 API 요청 (자동 토큰 재발급 포함)
export async function authenticatedFetch<T>(
    endpoint: string,
    token: string,
    options: RequestInit = {}
): Promise<T> {
    try {
        // 첫 번째 시도
        return await apiFetch<T>(endpoint, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`,
            },
        });
    } catch(error) {
        console.error('API Error:', error);
    }
    // } catch (error: any) {
    //     // 401 에러 (토큰 만료) - 자동 재발급 시도
    //     if (error.message === 'TOKEN_EXPIRED' && tokenManager) {
    //         console.log('🔄 Access token expired, attempting refresh...');
    //
    //         const newToken = await refreshAccessToken();
    //
    //         if (newToken) {
    //             // 새 토큰으로 재시도
    //             console.log('✅ Token refreshed, retrying request...');
    //             return await apiFetch<T>(endpoint, {
    //                 ...options,
    //                 headers: {
    //                     ...options.headers,
    //                     'Authorization': `Bearer ${newToken}`,
    //                 },
    //             });
    //         } else {
    //             // 재발급 실패 - 로그아웃 및 로그인 페이지 이동
    //             console.log('❌ Token refresh failed, logging out...');
    //             alert('세션이 만료되었습니다. 다시 로그인해주세요.');
    //             tokenManager.logout();
    //             tokenManager.redirectToLogin();
    //             throw new Error('SESSION_EXPIRED');
    //         }
    //     }
    //
    //     // 403 에러 또는 기타 에러
    //     if (error.message === 'FORBIDDEN') {
    //         alert('접근 권한이 없습니다.');
    //     }
    //
    //     throw error;
    // }

}

// 🔹 인증이 필요 없는 API 요청 (응답 형식 자유)
export async function publicFetch<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    return apiFetch<T>(endpoint, options);
}





export {API_BASE_URL};