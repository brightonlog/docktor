# ============================================================
# Prometheus GPU Metrics Exporter (Jetson Orin Nano)
# ============================================================
# Jetson GPU/CPU 온도, 사용량, 메모리 등을 Prometheus로 내보내기

from prometheus_client import start_http_server, Gauge, Info
import subprocess
import re
import time
import os

# Prometheus 메트릭 정의
gpu_usage = Gauge('jetson_gpu_usage_percent', 'GPU Usage Percentage')
gpu_freq = Gauge('jetson_gpu_freq_mhz', 'GPU Frequency in MHz')
cpu_usage = Gauge('jetson_cpu_usage_percent', 'CPU Usage Percentage', ['core'])
cpu_temp = Gauge('jetson_cpu_temp_celsius', 'CPU Temperature in Celsius')
gpu_temp = Gauge('jetson_gpu_temp_celsius', 'GPU Temperature in Celsius')
memory_used = Gauge('jetson_memory_used_mb', 'Memory Used in MB')
memory_total = Gauge('jetson_memory_total_mb', 'Memory Total in MB')
power_usage = Gauge('jetson_power_usage_mw', 'Power Usage in Milliwatts')
system_info = Info('jetson_system', 'Jetson System Information')


def parse_tegrastats():
    """tegrastats 명령어로 시스템 정보 파싱"""
    try:
        result = subprocess.run(
            ['tegrastats', '--interval', '1000'],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.stdout
    except Exception as e:
        print(f"tegrastats 실행 오류: {e}")
        return None


def parse_jtop():
    """jtop을 사용한 시스템 정보 수집"""
    try:
        # jtop이 설치되어 있는지 확인
        from jtop import jtop

        with jtop() as jetson:
            if jetson.ok():
                # GPU 정보
                if 'GPU' in jetson.gpu:
                    gpu_usage.set(jetson.gpu['GPU']['status']['load'])

                # 온도 정보
                if 'GPU' in jetson.temperature:
                    gpu_temp.set(jetson.temperature['GPU'])
                if 'CPU' in jetson.temperature:
                    cpu_temp.set(jetson.temperature['CPU'])

                # 메모리 정보
                mem = jetson.memory
                memory_used.set(mem['used'] / (1024 * 1024))  # MB로 변환
                memory_total.set(mem['total'] / (1024 * 1024))

                # CPU 정보
                for i, cpu_val in enumerate(jetson.cpu['cpu']):
                    if cpu_val is not None:
                        cpu_usage.labels(core=f'cpu{i+1}').set(cpu_val)

                # 전력 정보
                if jetson.power:
                    total_power = sum(jetson.power.values())
                    power_usage.set(total_power)

                return True
    except ImportError:
        print("jtop이 설치되지 않음. 대체 방법 사용")
        return False
    except Exception as e:
        print(f"jtop 오류: {e}")
        return False


def get_cpu_temp_from_thermal():
    """thermal_zone에서 온도 읽기"""
    try:
        # CPU 온도
        with open('/sys/devices/virtual/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read().strip()) / 1000.0
            cpu_temp.set(temp)

        # GPU 온도 (thermal_zone1 또는 thermal_zone2)
        for zone in range(1, 5):
            thermal_path = f'/sys/devices/virtual/thermal/thermal_zone{zone}/type'
            if os.path.exists(thermal_path):
                with open(thermal_path, 'r') as f:
                    zone_type = f.read().strip()

                if 'GPU' in zone_type.upper():
                    with open(f'/sys/devices/virtual/thermal/thermal_zone{zone}/temp', 'r') as f:
                        temp = int(f.read().strip()) / 1000.0
                        gpu_temp.set(temp)
                    break

        return True
    except Exception as e:
        print(f"온도 읽기 오류: {e}")
        return False


def get_memory_info():
    """메모리 정보 읽기"""
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()

        mem_total = int(re.search(r'MemTotal:\s+(\d+)', meminfo).group(1)) / 1024
        mem_available = int(re.search(r'MemAvailable:\s+(\d+)', meminfo).group(1)) / 1024
        mem_used = mem_total - mem_available

        memory_total.set(mem_total)
        memory_used.set(mem_used)

        return True
    except Exception as e:
        print(f"메모리 정보 읽기 오류: {e}")
        return False


def get_cpu_usage():
    """CPU 사용률 읽기"""
    try:
        with open('/proc/stat', 'r') as f:
            lines = f.readlines()

        for line in lines:
            if line.startswith('cpu') and len(line.split()) > 1:
                parts = line.split()
                if parts[0] == 'cpu':
                    continue  # 전체 CPU는 건너뛰기

                cpu_num = parts[0].replace('cpu', '')
                user = int(parts[1])
                nice = int(parts[2])
                system = int(parts[3])
                idle = int(parts[4])

                total = user + nice + system + idle
                usage = ((total - idle) / total) * 100 if total > 0 else 0

                cpu_usage.labels(core=f'cpu{cpu_num}').set(usage)

        return True
    except Exception as e:
        print(f"CPU 사용률 읽기 오류: {e}")
        return False


def collect_metrics():
    """메트릭 수집"""
    # jtop 시도
    if not parse_jtop():
        # 대체 방법 사용
        get_cpu_temp_from_thermal()
        get_memory_info()
        get_cpu_usage()


def main():
    """메인 함수"""
    print("=" * 70)
    print("  Prometheus GPU Metrics Exporter")
    print("=" * 70)
    print("포트: 9100")
    print("메트릭 엔드포인트: http://<Jetson IP>:9100/metrics")
    print("=" * 70)

    # 시스템 정보 설정
    try:
        with open('/etc/nv_tegra_release', 'r') as f:
            jetpack_version = f.read().strip()
            system_info.info({
                'jetpack': jetpack_version,
                'device': 'Jetson Orin Nano'
            })
    except:
        system_info.info({'device': 'Jetson Orin Nano'})

    # Prometheus HTTP 서버 시작
    start_http_server(9100)

    print("\n[INFO] 메트릭 수집 시작...")
    print("[INFO] Ctrl+C로 종료")

    # 메트릭 수집 루프
    while True:
        try:
            collect_metrics()
            time.sleep(5)  # 5초마다 수집
        except KeyboardInterrupt:
            print("\n[INFO] 종료 중...")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
