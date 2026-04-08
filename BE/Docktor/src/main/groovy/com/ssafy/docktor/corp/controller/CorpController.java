package com.ssafy.docktor.corp.controller;

import com.ssafy.docktor.corp.dto.CorpResponseDto;
import com.ssafy.docktor.corp.service.CorpService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * 기업(Corp) REST API Controller
 */
@RestController
@RequestMapping("/api/corp")
@RequiredArgsConstructor
public class CorpController {

    private final CorpService corpService;

    /**
     * Corp ID로 조회
     */
    @GetMapping("/{corpId}")
    public CorpResponseDto getCorpById(@PathVariable("corpId") Integer corpId) {
        return corpService.getCorpById(corpId);
    }

    /**
     * Corp 정보 수정
     */
    @PatchMapping("/{corpId}")
    public CorpResponseDto updateCorp(
            @PathVariable("corpId") Integer corpId,
            @RequestBody CorpResponseDto requestDto
    ) {
        return corpService.updateCorp(corpId, requestDto);
    }

}
