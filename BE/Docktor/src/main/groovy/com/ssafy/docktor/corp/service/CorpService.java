package com.ssafy.docktor.corp.service;

import com.ssafy.docktor.corp.dto.CorpResponseDto;

/**
 * Corp Service
 */
public interface CorpService {
    
    CorpResponseDto getCorpById(Integer corpId);
    CorpResponseDto updateCorp(Integer corpId, CorpResponseDto requestDto);
}
