package com.ssafy.docktor.inspect.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class InspectDto {
    private Integer inspectId;
    private Integer sectionId;
    private Integer shipId;
    private String status; // pending, in_progress, completed, failed
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private LocalDateTime createDate;
    private String sectionName;
    private String sectionKRName;
}