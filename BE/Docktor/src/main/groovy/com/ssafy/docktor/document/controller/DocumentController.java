package com.ssafy.docktor.document.controller;

import com.ssafy.docktor.document.dto.InspectionReportRequest;
import com.ssafy.docktor.document.service.HtmlToPdfService;
import com.ssafy.docktor.document.service.LLMService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@RestController
@RequestMapping("/api/document")
public class DocumentController {


    @Autowired
    private HtmlToPdfService htmlToPdfService;

    @Autowired
    private LLMService llmService;
    /**
     * 검사 결과 보고서 PDF 생성
     * POST /api/document/inspection-report
     */
    @PostMapping("/inspection-report")
    public ResponseEntity<byte[]> generateInspectionReport(@RequestBody InspectionReportRequest request) {
        // 1. GMS(AI)에게 결함 리스트를 보내 분석 결과 받기
        String aiAnalysis = llmService.analyzeShipCondition(request.getShip(), request.getInspection(), request.getDefects());

        // 2. 분석 결과를 포함하여 HTML 생성
        String html = htmlToPdfService.createInspectionReportHtml(request, aiAnalysis);
        byte[] pdfBytes = htmlToPdfService.convertHtmlToPdf(html);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_PDF);

        // 파일명: inspection_report_{shipName}_{timestamp}.pdf
        String filename = String.format("inspection_report_%s_%s.pdf",
                request.getShip().getName().replaceAll("\\s+", "_"),
                LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss")));

        headers.setContentDispositionFormData("attachment", filename);
        headers.setCacheControl("must-revalidate, post-check=0, pre-check=0");

        return ResponseEntity.ok()
                .headers(headers)
                .body(pdfBytes);
    }
}
