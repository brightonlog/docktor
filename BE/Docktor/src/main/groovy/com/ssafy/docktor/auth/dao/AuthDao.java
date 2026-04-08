package com.ssafy.docktor.auth.dao;

import com.ssafy.docktor.auth.dto.CorpDto;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface AuthDao {
    CorpDto findByCorpCode(String corpCode);
    CorpDto findByCorpId(Integer corpId);
}

