package com.ssafy.docktor.inspect.dao;

import com.ssafy.docktor.inspect.dto.InspectDto;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface InspectDao {
    List<InspectDto> selectAllAnalyze(int corpId);
    int insertInspect(InspectDto inspectDto);
    int updateStatus(InspectDto inspectDto);

    List<InspectDto> selectOngoingInspects();

    int updateStatusByRobotId(String robotId, String disconnected);

    int updateAllInProgressToDisconnected();

    String getCurrentStatus();

    InspectDto findById(@Param("inspectId") Integer inspectId);
}