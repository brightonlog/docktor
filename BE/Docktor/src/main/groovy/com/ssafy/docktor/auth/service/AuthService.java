package com.ssafy.docktor.auth.service;

import com.ssafy.docktor.auth.dto.*;

public interface AuthService {
    LoginResponse login(LoginRequest loginRequest);
    RefreshTokenResponse refresh(RefreshTokenRequest request);// 토근 갱신 메서드
    void logout(LogoutRequest request);
}
