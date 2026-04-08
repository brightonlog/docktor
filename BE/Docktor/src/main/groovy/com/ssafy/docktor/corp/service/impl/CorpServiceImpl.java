package com.ssafy.docktor.corp.service.impl;

import com.ssafy.docktor.corp.dao.CorpDao;
import com.ssafy.docktor.corp.dto.CorpResponseDto;
import com.ssafy.docktor.corp.service.CorpService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;


@Service
@RequiredArgsConstructor
public class CorpServiceImpl implements CorpService {
    
    private final CorpDao corpDao;
    
    @Override
    public CorpResponseDto getCorpById(Integer corpId) {
        CorpResponseDto corpDto = corpDao.selectCorpById(corpId);
        if (corpDto == null) {
            throw new IllegalArgumentException("해당 기업을 찾을 수 없습니다. ID: " + corpId);
        }
        return convertToResponseDto(corpDto);
    }
    
    @Override
    @Transactional
    public CorpResponseDto updateCorp(Integer corpId, CorpResponseDto requestDto) {
        // 기존 데이터 조회
        CorpResponseDto existingCorp = corpDao.selectCorpById(corpId);
        if (existingCorp == null) {
            throw new IllegalArgumentException("해당 기업을 찾을 수 없습니다. ID: " + corpId);
        }
        
        // 업데이트할 데이터 설정
        CorpResponseDto updateDto = CorpResponseDto.builder()
                .corpId(corpId)
                .corpName(requestDto.getCorpName())
                .manager(requestDto.getManager())
                .phone(requestDto.getPhone())
                .email(requestDto.getEmail())
                .build();
        
        // 업데이트 실행
        int result = corpDao.updateCorp(updateDto);
        if (result == 0) {
            throw new RuntimeException("기업 정보 수정에 실패했습니다.");
        }
        
        // 수정된 데이터 반환
        return getCorpById(corpId);
    }
    
    /**
     * CorpDto를 CorpResponseDto로 변환 (password 제외)
     */
    private CorpResponseDto convertToResponseDto(CorpResponseDto corpDto) {
        return CorpResponseDto.builder()
                .corpId(corpDto.getCorpId())
                .corpCode(corpDto.getCorpCode())
                .corpName(corpDto.getCorpName())
                .manager(corpDto.getManager())
                .phone(corpDto.getPhone())
                .email(corpDto.getEmail())
                .createDate(corpDto.getCreateDate())
                .build();
    }
}
