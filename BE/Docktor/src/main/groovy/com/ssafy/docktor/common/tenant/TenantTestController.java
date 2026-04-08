package com.ssafy.docktor.common.tenant;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * 멀티테넌트 테스트용 컨트롤러
 * 현재 Tenant 정보 확인
 */
@RestController
@RequestMapping("/api/tenant")
@RequiredArgsConstructor
public class TenantTestController {
    
    @GetMapping("/current")
    public Map<String, Object> getCurrentTenant() {
        Map<String, Object> response = new HashMap<>();
        
        Integer corpId = TenantContext.getCurrentTenant();
        
        if (corpId != null) {
            response.put("success", true);
            response.put("corpId", corpId);
            response.put("message", "현재 Tenant가 설정되어 있습니다.");
        } else {
            response.put("success", false);
            response.put("message", "Tenant가 설정되지 않았습니다.");
        }
        
        return response;
    }
}
