package com.ssafy.docktor.common.service;

import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.model.ObjectMetadata;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@Service
@RequiredArgsConstructor
public class S3Service {

    private final AmazonS3 amazonS3;

    @Value("${cloud.aws.s3.bucket}")
    private String bucket;

    /**
     * 파일 업로드
     * @param file 업로드할 파일
     * @param s3Path 저장될 경로 (예: corp_1/ships/1/model/파일.glb)
     * @return 저장된 파일의 S3 URL
     */
    public String uploadFile(MultipartFile file, String s3Path) {
        ObjectMetadata metadata = new ObjectMetadata();
        metadata.setContentLength(file.getSize());
        metadata.setContentType(file.getContentType());

        try {
            amazonS3.putObject(bucket, s3Path, file.getInputStream(), metadata);
        } catch (IOException e) {
            throw new RuntimeException("S3 업로드 실패: " + e.getMessage());
        }

        // 업로드된 파일의 전체 URL 반환
        return amazonS3.getUrl(bucket, s3Path).toString();
    }
    
    /**
     * 파일 삭제
     * @param fileUrl S3 파일 전체 URL (예: https://bucket.s3.region.amazonaws.com/path/to/file.glb)
     */
    public void deleteFile(String fileUrl) {
        try {
            // S3 URL에서 key(경로) 추출
            // 예: https://docktor-bucket.s3.ap-northeast-2.amazonaws.com/corp_1/ships/1/model/file.glb
            //     → corp_1/ships/1/model/file.glb
            String key = extractKeyFromUrl(fileUrl);

            // S3에서 파일 삭제
            amazonS3.deleteObject(bucket, key);
        } catch (Exception e) {
            throw new RuntimeException("S3 파일 삭제 실패: " + e.getMessage());
        }
    }

    /**
     * S3 URL에서 key 추출
     * @param fileUrl S3 전체 URL
     * @return S3 key (경로)
     */
    private String extractKeyFromUrl(String fileUrl) {
        // URL 형식: https://bucket-name.s3.region.amazonaws.com/key
        // 또는: https://s3.region.amazonaws.com/bucket-name/key

        try {
            // bucket 이름 뒤의 경로 추출
            String bucketUrl = amazonS3.getUrl(bucket, "").toString();
            if (fileUrl.startsWith(bucketUrl)) {
                return fileUrl.substring(bucketUrl.length());
            }

            // 다른 URL 형식 처리
            int bucketIndex = fileUrl.indexOf(bucket);
            if (bucketIndex != -1) {
                String afterBucket = fileUrl.substring(bucketIndex + bucket.length());
                return afterBucket.startsWith("/") ? afterBucket.substring(1) : afterBucket;
            }

            throw new IllegalArgumentException("올바르지 않은 S3 URL 형식: " + fileUrl);
        } catch (Exception e) {
            throw new RuntimeException("S3 URL 파싱 실패: " + e.getMessage());
        }
    }
}