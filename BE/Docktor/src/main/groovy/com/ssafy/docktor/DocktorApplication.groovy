package com.ssafy.docktor

import org.springframework.boot.SpringApplication
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.retry.annotation.EnableRetry
import org.springframework.scheduling.annotation.EnableAsync
import org.springframework.scheduling.annotation.EnableScheduling

@EnableAsync
@EnableRetry
@EnableScheduling
@SpringBootApplication
class DocktorApplication {

    static void main(String[] args) {
        SpringApplication.run(DocktorApplication, args)
    }

}
