package com.ssafy.docktor.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class RefreshTokenResponse {
    private boolean success;
    private String message;
    private String accessToken;
}