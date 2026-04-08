package com.ssafy.docktor.inspect.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class InspectRequest {
    private Integer corpId;
    private Integer shipId;
    private Integer sectionId;
}
