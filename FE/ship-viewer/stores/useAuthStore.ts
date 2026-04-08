import {create} from 'zustand'
import {persist, devtools} from 'zustand/middleware'


// 🔹 기업 상세 정보 (이미지 응답 기반)
export interface Corp {
    corpId: number;
    corpCode: string;
    corpName: string;
    manager: string;
    phone: string | null;
    email: string | null;
    createDate: string;
}

interface AuthState {
    corp: Corp | null
    accessToken: string | null      // ✅ 추가
    refreshToken: string | null     // ✅ 추가

    login: (corp: Corp, accessToken: string, refreshToken: string) => void
    logout: () => void
    setAccessToken: (token: string) => void  // ✅ 토큰 갱신용
}

export const useAuthStore = create<AuthState>()(
    devtools(
        persist(
            (set) => ({
                corp: null,
                accessToken: null,      // ✅ 추가
                refreshToken: null,     // ✅ 추가

                login: (corp, accessToken, refreshToken) => set({
                    corp,
                    accessToken,        // ✅ 추가
                    refreshToken,       // ✅ 추가
                }),

                logout: () => set({
                    corp: null,
                    accessToken: null,
                    refreshToken: null,
                }),

                setAccessToken: (token) => set({ accessToken: token }),
            }),
            {
                name: 'auth-storage',
            }
        ),
        {
            name: 'AuthStore',
            enabled: process.env.NODE_ENV === 'development',
        }
    )
)
