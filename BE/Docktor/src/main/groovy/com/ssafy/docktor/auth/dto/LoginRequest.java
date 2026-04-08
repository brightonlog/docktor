package com.ssafy.docktor.auth.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class LoginRequest {
    private String corpCode;
    private String password;
}
