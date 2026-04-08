import socket# [cite: 510]

# 중요! 여기서 HOST는 라즈베리 파이의 wlan0 IP 주소를 넣으세요. [cite: 534]
HOST = '192.168.0.12' 
PORT = 1234 # [cite: 512]

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # [cite: 514]
    s.connect((HOST, PORT)) # 서버 접속 시도 [cite: 516]
    while True:
        message = input("라즈베리 파이에게 보낼 인사: ") # [cite: 521]
        s.sendall(message.encode()) # 메시지 전송 [cite: 522]
        
        data = s.recv(1024) # 서버 답장 수신 [cite: 530]
        print(f"라즈베리 파이의 답장: {data.decode()}") # [cite: 532]