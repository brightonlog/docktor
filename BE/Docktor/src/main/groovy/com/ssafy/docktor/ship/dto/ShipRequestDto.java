package com.ssafy.docktor.ship.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 선박 등록/수정 요청 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ShipRequestDto {
    private Integer corpId;                  // corp_id (선택)
    private String name;                     // 선박명
    private String classNo;
    private String imo;
    private String classNotation;
    private String flagState;
    private String port;
    private Double ton;
    private Double deadWeight;
    private Double lbp;
    private String shipbuilder;
    private String hullNumber;
    private LocalDateTime deliveryDate;
    private LocalDateTime buildDate;
}