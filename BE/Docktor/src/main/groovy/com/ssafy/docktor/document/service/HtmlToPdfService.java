package com.ssafy.docktor.document.service;

import com.ssafy.docktor.defect.dto.DefectDto;
import com.ssafy.docktor.document.dto.InspectionReportRequest;
import com.ssafy.docktor.ship.dto.Ship;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;
import org.xhtmlrenderer.pdf.ITextRenderer;
import com.lowagie.text.pdf.BaseFont;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.math.BigDecimal; // BigDecimal 임포트 추가
import java.nio.file.Files;
import java.util.List;
import java.util.Base64;

@Service
public class HtmlToPdfService {

    public byte[] convertHtmlToPdf(String htmlContent) {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try {
            ITextRenderer renderer = new ITextRenderer();

            // 1. 폰트 설정
            boolean fontLoaded = false;
            try {
                ClassPathResource fontResource = new ClassPathResource("fonts/NanumGothic.ttf");
                if (fontResource.exists()) {
                    try {
                        File fontFile = fontResource.getFile();
                        renderer.getFontResolver().addFont(
                                fontFile.getAbsolutePath(),
                                BaseFont.IDENTITY_H,
                                BaseFont.EMBEDDED
                        );
                        fontLoaded = true;
                    } catch (Exception e) {
                        InputStream fontStream = fontResource.getInputStream();
                        File tempFont = File.createTempFile("NanumGothic", ".ttf");
                        tempFont.deleteOnExit();
                        Files.copy(fontStream, tempFont.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                        fontStream.close();
                        renderer.getFontResolver().addFont(
                                tempFont.getAbsolutePath(),
                                BaseFont.IDENTITY_H,
                                BaseFont.EMBEDDED
                        );
                        fontLoaded = true;
                    }
                }
            } catch (Exception e) {
                System.out.println("⚠️ 폰트 로딩 실패: " + e.getMessage());
            }

            if (!fontLoaded) {
                String[][] systemFonts = {
                        {"C:/Windows/Fonts/malgun.ttf", "Malgun Gothic"},
                        {"C:/Windows/Fonts/batang.ttf", "Batang"},
                        {"C:/Windows/Fonts/gulim.ttf", "Gulim"}
                };
                for (String[] fontInfo : systemFonts) {
                    try {
                        File fontFile = new File(fontInfo[0]);
                        if (fontFile.exists()) {
                            renderer.getFontResolver().addFont(
                                    fontInfo[0],
                                    BaseFont.IDENTITY_H,
                                    BaseFont.EMBEDDED
                            );
                            fontLoaded = true;
                            break;
                        }
                    } catch (Exception e) {}
                }
            }

            renderer.setDocumentFromString(htmlContent);
            renderer.layout();
            renderer.createPDF(baos);

        } catch (Exception e) {
            e.printStackTrace();
        }
        return baos.toByteArray();
    }

    private String getLogoBase64() {
        try {
            ClassPathResource logoResource = new ClassPathResource("img/logo.png");
            if (logoResource.exists()) {
                byte[] logoBytes = logoResource.getInputStream().readAllBytes();
                return Base64.getEncoder().encodeToString(logoBytes);
            }
        } catch (Exception e) {}
        return "";
    }

    public String createInspectionReportHtml(InspectionReportRequest request, String aiAnalysisResult) {
        String logoBase64 = getLogoBase64();

        // 날짜 및 데이터 포맷팅
        java.time.format.DateTimeFormatter formatter = java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
        String inspectionTime = request.getInspection().getStartTime() != null
                ? request.getInspection().getStartTime().format(formatter) : "N/A";

        Ship ship = request.getShip();
        String shipName = ship.getName() != null ? ship.getName() : "-";
        String shipClass = ship.getClassNotation() != null ? ship.getClassNotation() : "-";
        String imo = ship.getImo() != null ? ship.getImo() : "-";
        String flag = ship.getFlagState() != null ? ship.getFlagState() : "-";
        String port = ship.getPort() != null ? ship.getPort() : "-";
        String ton = ship.getTon() != null ? String.format("%.0f", ship.getTon()) : "-";
        String sectionName = request.getInspection().getSectionKRName() != null ? request.getInspection().getSectionKRName() : "-";
        int defectCount = request.getDefects() != null ? request.getDefects().size() : 0;

        // 결함 리스트 생성
        StringBuilder defectRows = new StringBuilder();
        List<DefectDto> defects = request.getDefects();

        if (defects != null && !defects.isEmpty()) {
            for (int i = 0; i < defects.size(); i++) {
                DefectDto defect = defects.get(i);

                // 짝수 인덱스 -> 새로운 행(tr) 시작
                if (i % 2 == 0) defectRows.append("<tr style='page-break-inside: avoid;'>");

                // 이미지 URL 처리
                String imageUrl = defect.getCroppedImageUrl() != null && !defect.getCroppedImageUrl().isEmpty()
                        ? defect.getCroppedImageUrl()
                        : "https://via.placeholder.com/300x300?text=No+Image";

                // 결함 종류 처리
                String defectType = defect.getCategoryName() != null ? defect.getCategoryNameKr() : "미확인";

                // -------------------------------------------------------------------
                // ⭐ [수정됨] BigDecimal 신뢰도 연산 처리
                // -------------------------------------------------------------------
                String confidenceHtml = "";
                Integer catId = defect.getCategoryId();

                // 카테고리 ID가 10이 아닐 때만 표시
                if (catId == null || catId != 10) {
                    String confVal = "-";
                    if (defect.getConfidence() != null) {
                        // BigDecimal 연산: 값 * 100
                        BigDecimal confidenceVal = defect.getConfidence();
                        BigDecimal percentVal = confidenceVal.multiply(new BigDecimal("100"));
                        confVal = String.format("%.1f%%", percentVal);
                    }

                    confidenceHtml = String.format("""
                            <div class="info-line">
                                <span class="label">신뢰도</span>
                                <span class="value blue-text">%s</span>
                            </div>
                            """, confVal);
                }

                // 좌표 정보 처리
                String location = (defect.getXCord() != null && defect.getYCord() != null)
                        ? String.format("X: %d, Y: %d", defect.getXCord(), defect.getYCord())
                        : "-";

                // HTML 조립
                defectRows.append(String.format("""
                        <td class="defect-card">
                            <div class="defect-box">
                                <div class="img-wrapper">
                                    <table style="width: 100%%; height: 100%%; border: none; border-spacing: 0;">
                                        <tr>
                                            <td style="vertical-align: middle; text-align: center; padding: 0; border: none;">
                                                <img src="%s" class="defect-img" alt="결함"/>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <div class="info-wrapper">
                                    <div class="info-line"><span class="label">결함종류</span><span class="value red-text">%s</span></div>
                                    %s  <div class="info-line"><span class="label">좌표</span><span class="value">%s</span></div>
                                </div>
                            </div>
                        </td>
                        """, imageUrl, defectType, confidenceHtml, location));

                // 홀수 인덱스 or 마지막 요소 -> 행(tr) 닫기
                if (i % 2 == 1 || i == defects.size() - 1) {
                    if (i == defects.size() - 1 && i % 2 == 0) defectRows.append("<td class='defect-card empty'></td>");
                    defectRows.append("</tr>");
                }
            }
        } else {
            defectRows.append("<tr><td colspan='2' style='text-align:center; padding:50px; color:#999;'>결함 없음</td></tr>");
        }

        String finalAiAnalysis = (aiAnalysisResult != null && !aiAnalysisResult.isBlank())
                ? aiAnalysisResult.replace("\n", "<br/>") : "분석 결과 없음";

        return """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8"/>
                    <style>
                        @page { size: A4; margin: 15mm; }
                        body { font-family: 'NanumGothic', sans-serif; font-size: 10pt; color: #333; line-height: 1.4; }
                        
                        .header-table { width: 100%%; border: none; margin-bottom: 25px; border-bottom: 2px solid #333; padding-bottom: 10px; }
                        h1 { font-size: 22pt; margin: 0; text-align: center; }
                        
                        .section-title { font-size: 14pt; font-weight: bold; margin: 25px 0 10px 0; border-left: 6px solid #2c3e50; padding-left: 10px; color: #2c3e50; }
                        
                        .info-table { width: 100%%; border-collapse: collapse; margin-bottom: 10px; page-break-inside: avoid; }
                        .info-table td { border: 1px solid #ccc; padding: 7px 10px; }
                        .label-cell { background-color: #f8f9fa; font-weight: bold; text-align: center; width: 18%%; }
                        .content-cell { width: 32%%; }
                        
                        /* 결함 그리드 */
                        .defect-table { width: 100%%; border-collapse: separate; border-spacing: 0 15px; border: none; page-break-inside: auto; }
                        .defect-table tr { page-break-inside: avoid; }
                        .defect-card { width: 50%%; vertical-align: top; padding: 0 8px; border: none; }
                        .defect-box { border: 1px solid #ddd; border-radius: 8px; padding: 10px; background-color: #fff; }
                        .defect-card.empty .defect-box { border: none; background: none; }
                        
                        /* 이미지 박스 (테이블 정렬용) */
                        .img-wrapper {
                            width: 100%%;
                            height: 320px;
                            background-color: #fff;
                            border: 1px solid #eee;
                            margin-bottom: 10px;
                            display: block; 
                            overflow: hidden;
                        }
                        
                        .defect-img {
                            max-width: 100%%;
                            max-height: 310px;
                            width: auto;
                            height: auto;
                        }
                        
                        .info-wrapper { padding: 0 5px; }
                        .info-line { margin-bottom: 5px; font-size: 11pt; }
                        .label { font-weight: bold; color: #666; margin-right: 10px; }
                        .value { color: #333; }
                        .red-text { color: #e74c3c; font-weight: bold; }
                        .blue-text { color: #3498db; font-weight: bold; }
                        
                        .ai-box { margin-top: 30px; padding: 20px; background-color: #eaf2f8; border: 1px solid #d6eaf8; border-radius: 8px; page-break-inside: avoid; }
                        .ai-title { color: #2980b9; font-weight: bold; font-size: 12pt; margin-bottom: 10px; border-bottom: 1px solid #a9cce3; padding-bottom: 5px; }
                    </style>
                </head>
                <body>
                    <table class="header-table">
                        <tr>
                            <td style="width: 20%%; border: none;"><img src="data:image/png;base64,%s" style="width: 120px;"/></td>
                            <td style="text-align: center; border: none;"><h1>검사 결과 보고서</h1></td>
                            <td style="width: 20%%; border: none;"></td>
                        </tr>
                    </table>
                    
                    <div class="section-title">배 정보</div>
                    <table class="info-table">
                        <tr><td class="label-cell">선박명</td><td class="content-cell">%s</td><td class="label-cell">Class</td><td class="content-cell">%s</td></tr>
                        <tr><td class="label-cell">IMO</td><td class="content-cell">%s</td><td class="label-cell">Flag</td><td class="content-cell">%s</td></tr>
                        <tr><td class="label-cell">Port</td><td class="content-cell">%s</td><td class="label-cell">Ton</td><td class="content-cell">%s</td></tr>
                    </table>
                    
                    <div class="section-title">검사 정보</div>
                    <table class="info-table">
                        <tr><td class="label-cell">검사 일시</td><td class="content-cell" colspan="3">%s</td></tr>
                        <tr><td class="label-cell">검사 위치</td><td class="content-cell">%s</td><td class="label-cell">총 결함 수</td><td class="content-cell">%d개</td></tr>
                    </table>
                    
                    <div class="section-title">결함 정보</div>
                    <table class="defect-table">
                        %s
                    </table>
                    
                    <div class="ai-box">
                        <div class="ai-title">🤖 AI 종합 분석</div>
                        <div class="ai-content">%s</div>
                    </div>
                </body>
                </html>
                """.formatted(
                logoBase64, shipName, shipClass, imo, flag, port, ton,
                inspectionTime, sectionName, defectCount, defectRows.toString(), finalAiAnalysis
        );
    }
}