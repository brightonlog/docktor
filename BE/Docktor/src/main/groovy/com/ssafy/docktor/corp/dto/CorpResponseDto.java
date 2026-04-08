package com.ssafy.docktor.corp.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * Corp DTO (password 제외)
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CorpResponseDto {
    private Integer corpId;
    private String corpCode;
    private String corpName;
    private String manager;
    private String phone;
    private String email;
    private LocalDateTime createDate;
}
