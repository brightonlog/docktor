
package com.ssafy.docktor.defect.dto;

import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString
@Data

public class DefectDto {
    private Integer defectId;      // PK
    private Integer inspectId;     // FK (어떤 검사에서 발견되었나)
    private Integer categoryId;    // FK (부식, 균열 등 결함 종류)
    private String categoryName;    // FK (부식, 균열 등 결함 종류)
    private String categoryNameKr;    // FK (부식, 균열 등 결함 종류)
    private BigDecimal confidence;     // AI 신뢰도 (0.0 ~ 1.0)
    private Integer x1;            // 바운딩 박스 좌상단 x
    private Integer y1;            // 바운딩 박스 좌상단 y
    private Integer x2;            // 바운딩 박스 우하단 x
    private Integer y2;            // 바운딩 박스 우하단 y
    private Integer xCord;
    private Integer yCord;
    private LocalDateTime createDate; // 생성 시간
    private String croppedImageUrl;
}