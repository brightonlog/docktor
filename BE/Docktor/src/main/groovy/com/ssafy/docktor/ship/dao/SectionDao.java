package com.ssafy.docktor.ship.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 구역(Section) DAO (MyBatis Mapper Interface)
 * XML 매퍼: SectionMapper.xml
 */
@Mapper
public interface SectionDao {
    
    /**
     * 구역 생성
     * 선박 등록 시 기본 구역(Front, Back, Port, Starboard) 자동 생성
     * @param shipId 선박 ID
     * @param name 구역명 (예: "Front", "Back")
     * @param description 구역 설명 (예: "선수 (Bow)")
     */
    void insertSection(@Param("shipId") Integer shipId, 
                       @Param("name") String name, 
                       @Param("description") String description);
}