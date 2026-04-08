package com.ssafy.docktor.common.tenant;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.annotation.Order;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * 모든 요청에서 현재 로그인한 사용자의 Corp ID를 TenantContext에 설정
 * JWT 필터 이후에 실행되어야 함 (Order 중요!)
 */
@Slf4j
@Component
@Order(2) // JWT 필터(Order 1) 다음에 실행
public class TenantFilter extends OncePerRequestFilter {
    
    @Override
    protected void doFilterInternal(HttpServletRequest request, 
                                    HttpServletResponse response, 
                                    FilterChain filterChain) throws ServletException, IOException {
        try {
            // SecurityContext에서 인증 정보 가져오기
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            
            if (authentication != null && authentication.isAuthenticated() 
                && authentication.getPrincipal() instanceof Integer) {
                
                Integer corpId = (Integer) authentication.getPrincipal();
                
                // ThreadLocal에 현재 Corp ID 설정
                TenantContext.setCurrentTenant(corpId);
                
                log.debug("🔑 Tenant 설정 완료 - URI: {}, Corp ID: {}", 
                         request.getRequestURI(), corpId);
            }
            
            // 다음 필터 실행
            filterChain.doFilter(request, response);
            
        } finally {
            // 요청 처리 완료 후 반드시 ThreadLocal 정리
            TenantContext.clear();
        }
    }
    
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // 로그인, 회원가입 등 인증이 필요없는 경로는 필터링하지 않음
        String path = request.getRequestURI();
        return path.startsWith("/api/auth/login") 
            || path.startsWith("/api/auth/register")
            || path.startsWith("/actuator")
            || path.startsWith("/h2-console");
    }
}
