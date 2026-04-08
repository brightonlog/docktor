package com.ssafy.docktor.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponse {
    private boolean success;
    private String message;
    private String accessToken;
    private String refreshToken;
    private CorpDto corp;

    // 에러용 생성자
    public LoginResponse(boolean success, String message) {
        this.success = success;
        this.message = message;
    }
}
