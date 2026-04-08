package com.ssafy.docktor.common.tenant;

import lombok.extern.slf4j.Slf4j;

/**
 * 현재 요청의 Tenant(Corp) ID를 ThreadLocal로 관리
 * 멀티테넌트 구현의 핵심 클래스
 */
@Slf4j
public class TenantContext {
    
    private static final ThreadLocal<Integer> CURRENT_TENANT = new ThreadLocal<>();
    
    /**
     * 현재 스레드의 Tenant(Corp) ID 설정
     */
    public static void setCurrentTenant(Integer corpId) {
        log.debug("🏢 Tenant Context 설정: corpId={}", corpId);
        CURRENT_TENANT.set(corpId);
    }
    
    /**
     * 현재 스레드의 Tenant(Corp) ID 조회
     */
    public static Integer getCurrentTenant() {
        Integer corpId = CURRENT_TENANT.get();
        log.debug("🏢 Tenant Context 조회: corpId={}", corpId);
        return corpId;
    }
    
    /**
     * 현재 스레드의 Tenant(Corp) ID 제거
     */
    public static void clear() {
        log.debug("🏢 Tenant Context 클리어");
        CURRENT_TENANT.remove();
    }
    
    /**
     * Tenant가 설정되어 있는지 확인
     */
    public static boolean hasTenant() {
        return CURRENT_TENANT.get() != null;
    }
}
