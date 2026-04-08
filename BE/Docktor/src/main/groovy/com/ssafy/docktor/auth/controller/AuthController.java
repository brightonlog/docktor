package com.ssafy.docktor.auth.controller;

import com.ssafy.docktor.auth.dto.*;
import com.ssafy.docktor.auth.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@RequestBody LoginRequest loginRequest) {
        try {
            LoginResponse response = authService.login(loginRequest);
            
            if (response.isSuccess()) {
                return ResponseEntity.ok(response);
            } else {
                return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(response);
            }
        } catch (Exception e) {
            LoginResponse response = new LoginResponse(false, "로그인 중 오류가 발생했습니다.");
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    // refresh 토큰 갱신 API 추가
    @PostMapping("/refresh")
    public ResponseEntity<RefreshTokenResponse> refresh(@RequestBody RefreshTokenRequest request){
        RefreshTokenResponse response = authService.refresh(request);

        if(!response.isSuccess()){
            return ResponseEntity.status(401).body(response);
        }

        return ResponseEntity.ok(response);
    }

    @PostMapping("/logout")
    public ResponseEntity<Map<String, Object>> logout(
            @RequestBody(required = false) LogoutRequest request
    ) {
        if (request == null) {
            request = new LogoutRequest();
        }

        authService.logout(request);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "로그아웃되었습니다.");

        return ResponseEntity.ok(response);
    }
}
