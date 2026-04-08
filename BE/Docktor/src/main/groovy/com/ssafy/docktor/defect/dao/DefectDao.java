package com.ssafy.docktor.defect.dao;

import com.ssafy.docktor.defect.dto.DefectDto;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface DefectDao {
    
    /**
     * 특정 inspect의 모든 결함 조회
     */
    List<DefectDto> findByInspectId(@Param("inspectId") Integer inspectId);
    
    /**
     * 결함 상세 조회 (카테고리명 포함)
     */
    DefectDto findById(@Param("defectId") Integer defectId);
    
    /**
     * 결함 등록 (AI 서버에서 받은 데이터)
     */
    int insertDefect(DefectDto defect);
    
    /**
     * 결함 수 조회
     */
    int countByInspectId(@Param("inspectId") Integer inspectId);

}
