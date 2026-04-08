// 🔹 API 기본 설정
import { ApiResponse, LoginRequest, LoginResponse } from '../types/auth-types';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080'

// 🔹 로그인 API 함수
export async function loginApi(
  credentials: LoginRequest
): Promise<ApiResponse<LoginResponse>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    })


    const result: LoginResponse = await response.json()

    // HTTP 상태 코드 확인
    if (!response.ok) {
      return {
        success: false,
        error: result.message || '로그인에 실패했습니다.',
      }
    }

    // 성공 응답
    return {
      success: true,
      message: result.message,
      data :result,
    }

  } catch (error) {
    // 네트워크 에러 등
    console.error('Login API Error:', error)
    return {
      success: false,
      error: '서버와 연결할 수 없습니다.',
    }
  }
}



