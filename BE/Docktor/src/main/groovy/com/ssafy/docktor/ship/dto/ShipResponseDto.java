package com.ssafy.docktor.ship.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 선박 정보 응답 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ShipResponseDto {
    private Integer shipId;                  // ship_id
    private Integer corpId;                  // corp_id
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
    
    // 3D 모델 파일 URL (S3)
    private String modelFileUrl;

    // 썸네일 파일 URL (S3)
    private String thumbnailUrl;

    /**
     * Ship -> ShipResponseDto 변환
     */
    public static ShipResponseDto from(Ship ship) {
        return ShipResponseDto.builder()
                .shipId(ship.getShipId())
                .corpId(ship.getCorpId())
                .name(ship.getName())
                .classNo(ship.getClassNo())
                .imo(ship.getImo())
                .classNotation(ship.getClassNotation())
                .flagState(ship.getFlagState())
                .port(ship.getPort())
                .ton(ship.getTon())
                .deadWeight(ship.getDeadWeight())
                .lbp(ship.getLbp())
                .shipbuilder(ship.getShipbuilder())
                .hullNumber(ship.getHullNumber())
                .deliveryDate(ship.getDeliveryDate())
                .buildDate(ship.getBuildDate())
                .createDate(ship.getCreateDate())
                .build();
    }

    /**
     * Ship + modelFileUrl + thumbnailUrl -> ShipResponseDto 변환
     */
    public static ShipResponseDto from(Ship ship, String modelFileUrl, String thumbnailUrl) {
        return ShipResponseDto.builder()
                .shipId(ship.getShipId())
                .corpId(ship.getCorpId())
                .name(ship.getName())
                .classNo(ship.getClassNo())
                .imo(ship.getImo())
                .classNotation(ship.getClassNotation())
                .flagState(ship.getFlagState())
                .port(ship.getPort())
                .ton(ship.getTon())
                .deadWeight(ship.getDeadWeight())
                .lbp(ship.getLbp())
                .shipbuilder(ship.getShipbuilder())
                .hullNumber(ship.getHullNumber())
                .deliveryDate(ship.getDeliveryDate())
                .buildDate(ship.getBuildDate())
                .createDate(ship.getCreateDate())
                .modelFileUrl(modelFileUrl)
                .thumbnailUrl(thumbnailUrl)
                .build();
    }
}