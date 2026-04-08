pipeline {
    agent any

    environment {
        EC2_USER = "ubuntu"
        EC2_IP = "i14e201.p.ssafy.io"
        JAR_NAME = "Docktor-0.0.1-SNAPSHOT.jar"
        SERVER_URL = "http://i14e201.p.ssafy.io:8080"
        OPENAI_API_KEY = credentials('OPENAI_API_KEY')
    }

    stages {
        stage('Git Checkout') {
            steps {
                git branch: 'dev',
                    credentialsId: 'ssafy-gitlab-id',
                    url: 'https://lab.ssafy.com/s14-webmobile3-sub1/S14P11E201.git'
            }
        }

        stage('Spring Build') {
            steps {
                dir('BE/Docktor') {
                    sh 'chmod +x gradlew'
                    sh "./gradlew clean build --refresh-dependencies -x test -Dspring.ai.openai.api-key=${OPENAI_API_KEY}"
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: 'ec2-key', keyFileVariable: 'PEM_KEY'),
                    string(credentialsId: 'DB_PASSWORD', variable: 'DB_PASS'),
                    string(credentialsId: 'AWS_ACCESS_KEY', variable: 'AWS_ACCESS'),
                    string(credentialsId: 'AWS_SECRET_KEY', variable: 'AWS_SECRET')
                ]) {
                    script {
                        echo "🚀 EC2 배포 시작 (${env.EC2_IP})..."

                        sh "scp -i $PEM_KEY -o StrictHostKeyChecking=no BE/Docktor/build/libs/${env.JAR_NAME} ${env.EC2_USER}@${env.EC2_IP}:~/"

                        sh """
                            ssh -i $PEM_KEY -o StrictHostKeyChecking=no ${env.EC2_USER}@${env.EC2_IP} "
                                sudo fuser -k 8080/tcp || true

                                nohup java -jar ~/${env.JAR_NAME} \
                                    --spring.ai.openai.api-key=${OPENAI_API_KEY} \
                                    --spring.datasource.password=${DB_PASS} \
                                    --spring.data.redis.host=localhost \
                                    --mqtt.client-id=docktor-spring-server \
                                    --mqtt.topic.robot-move=robot/orin_01/move \
                                    --mqtt.broker.url=tcp://localhost:1883 \
                                    --cloud.aws.credentials.access-key=${AWS_ACCESS} \
                                    --cloud.aws.credentials.secret-key='${AWS_SECRET}' \
                                    --cloud.aws.region.static=ap-northeast-2 \
                                    --cloud.aws.s3.bucket=docktor-bucket \
                                    --cloud.aws.stack.auto=false \
                                    --robot.callback.url=${env.SERVER_URL}/api/inspect/callback \
                                    > nohup.out 2>&1 &
                            "
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            echo '✅ 빌드 및 배포 성공!'
            sh "curl -X POST -H 'Content-Type: application/json' -d '{\"text\": \"배포 성공\"}' ${env.MM_WEBHOOK}"
        }
        failure {
            echo '❌ 빌드 및 배포 실패!'
        }
    }
}