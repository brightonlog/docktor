package com.ssafy.docktor.ship.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 선박 엔티티
 * DB의 ship 테이블과 매핑
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Ship {
    private Integer shipId;                  // ship_id (PK)
    private Integer corpId;                  // corp_id (FK)
    private String name;
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
    private LocalDateTime createDate;
}