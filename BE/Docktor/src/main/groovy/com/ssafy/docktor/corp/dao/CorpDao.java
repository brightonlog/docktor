package com.ssafy.docktor.corp.dao;

import com.ssafy.docktor.corp.dto.CorpResponseDto;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * Corp DAO
 */
@Mapper
public interface CorpDao {

    CorpResponseDto selectCorpById(@Param("corpId") Integer corpId);
    int updateCorp(CorpResponseDto corpDto);
}
