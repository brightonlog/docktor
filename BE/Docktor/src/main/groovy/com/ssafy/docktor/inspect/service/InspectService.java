package com.ssafy.docktor.inspect.service;

import com.ssafy.docktor.inspect.dto.InspectDto;
import com.ssafy.docktor.inspect.dto.InspectRequest;
import com.ssafy.docktor.inspect.dto.RobotStatusDto;

import java.util.List;
import java.util.Map;

public interface InspectService {
    List<InspectDto> getInspectList(Integer shipId);

//    String sendMoveCommand(InspectRequest inspectRequest);
      Map<String,Object>  sendMoveCommand(InspectRequest inspectRequest);


    void completeInspect(Map<String, Object> result);

    void updateRobotHeartbeat(RobotStatusDto status);
    RobotStatusDto getRobotStatus(String robotId);

    void syncRobotStatusWithDb();
}