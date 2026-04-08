import {publicFetch, authenticatedFetch} from "@/lib/api/client";
import {LoginRequest, LoginResponse} from "@/lib/types/auth-types";

export async function login(credentials : LoginRequest){
    return publicFetch<LoginResponse> ('/auth/login',{
        method : 'POST',
        body: JSON.stringify(credentials),
    })
}

export async function logout (token:string){
    return authenticatedFetch<void>('auth/logout',token,{
        method : 'POST',
    })
}

// 🔹 토큰 갱신
export async function refreshAccessTokenApi(refreshToken: string) {
    return publicFetch<{ accessToken: string }>('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refreshToken }),
    });
}
// 🔹 토큰 검증
export async function verifyTokenApi(token: string) {
    return authenticatedFetch<LoginResponse>('/auth/verify', token, {
        method: 'GET',
    });
}