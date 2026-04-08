package com.ssafy.docktor.auth.dto;

import lombok.Getter;
import lombok.Setter;

import java.sql.Timestamp;

@Getter
@Setter
public class CorpDto {
    private Integer corpId;  // id → corpId
    private String corpCode;
    private String password;
    private String corpName;
    private String manager;
    private String phone;
    private String email;
    private Timestamp createDate;
}
