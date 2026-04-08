package com.ssafy.docktor.auth.filter;

import com.ssafy.docktor.auth.util.JwtUtil;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.ArrayList;

@Slf4j
@Component
@RequiredArgsConstructor
@org.springframework.core.annotation.Order(1) // Tenant 필터보다 먼저 실행
public class JwtAuthenticationFilter extends OncePerRequestFilter {
    private final JwtUtil jwtUtil;


    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain) throws ServletException, IOException {
        try {
            // 1. Authorization 헤더에서 JWT 토큰 추출
            String token = extractTokenFromRequest(request);

            if (token != null && jwtUtil.validateAccessToken(token)) {
                Integer corpId = jwtUtil.extractCorpId(token);
                String corpCode = jwtUtil.extractCorpCode(token);

                log.debug("JWT 인증 성공 - corpId: {}, corpCode:{}", corpId, corpCode);

                //Spring Security 인증 객체 생성
                UsernamePasswordAuthenticationToken authenticationToken = new UsernamePasswordAuthenticationToken(corpId, // principal(주체)
                        null, // credentials(비밀번호 불필요)
                        new ArrayList<>() // authorities (권한 목록)
                );

                // 5. 요청 세부 정보 설정
                authenticationToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

                // 6. SecurityContext에 인증 정보 저장
                SecurityContextHolder.getContext().setAuthentication(authenticationToken);
            }

        } catch (Exception e) {
            log.error("JWT 인증 처리 중 오류 발생: {}", e.getMessage());
        }

        // 7. 다음 필터로 요청 전달
        filterChain.doFilter(request, response);

    }

    /**
     * HTTP 요청 헤더에서 JWT 토큰 추출
     * Authorization: Bearer eyJh..
     */
    private String extractTokenFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");

        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}
