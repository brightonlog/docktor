package com.ssafy.docktor.ship.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 파일 DAO (MyBatis Mapper Interface)
 * XML 매퍼: FileMapper.xml
 */
@Mapper
public interface FileDao {
    
    /**
     * 파일 정보 저장
     * @param tableName 테이블명 (예: "ship")
     * @param tableId 테이블 ID (예: shipId)
     * @param path S3 파일 URL
     */
    void insertFile(@Param("tableName") String tableName, 
                    @Param("tableId") Integer tableId, 
                    @Param("path") String path);
    
    /**
     * 모델 파일 경로 조회 (path에 'model' 포함, 가장 최근 1개)
     * @param tableName 테이블명 (예: "ship")
     * @param tableId 테이블 ID (예: shipId)
     * @return 모델 파일 경로(URL), 없으면 null
     */
    String selectModelPathByTableId(@Param("tableName") String tableName,
                                     @Param("tableId") Integer tableId);
    
    /**
     * 썸네일 파일 경로 조회 (path에 'thumbnail' 포함, 가장 최근 1개)
     * @param tableName 테이블명 (예: "ship")
     * @param tableId 테이블 ID (예: shipId)
     * @return 썸네일 파일 경로(URL), 없으면 null
     */
    String selectThumbnailPathByTableId(@Param("tableName") String tableName,
                                         @Param("tableId") Integer tableId);

    /**
     * 특정 테이블의 모든 파일 삭제
     * @param tableName 테이블명 (예: "ship")
     * @param tableId 테이블 ID (예: shipId)
     * @return 삭제된 행 수
     */
    int deleteFilesByTableId(@Param("tableName") String tableName, 
                              @Param("tableId") Integer tableId);

}