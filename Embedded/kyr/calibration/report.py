import json
import os
from datetime import datetime

def generate_markdown_report(json_file_path):
    """
    기존 JSON 캘리브레이션 데이터를 읽어서 markdown 리포트 생성
    """
    # JSON 파일 읽기
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            calibration_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"❌ JSON 파일 형식이 올바르지 않습니다: {json_file_path}")
        return
    
    # Markdown 파일 경로 (JSON 파일과 같은 위치)
    base_dir = os.path.dirname(json_file_path)
    md_file = os.path.join(base_dir, 'calibration_report.md')
    
    # Markdown 생성
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# 🏎️ Jetson Orin Nano Car 캘리브레이션 결과\n\n")
        f.write(f"**리포트 생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**총 테스트 세트 수**: {len(calibration_data)}개\n\n")
        f.write("---\n\n")
        
        if len(calibration_data) == 0:
            f.write("아직 저장된 결과가 없습니다.\n")
            print("⚠️  저장된 데이터가 없습니다.")
            return
        
        # 각 테스트 세트별로 정리
        for idx, test_set in enumerate(calibration_data, 1):
            f.write(f"## 테스트 세트 #{idx}\n\n")
            f.write(f"- **측정 시간**: {test_set.get('timestamp', '미기록')}\n")
            f.write(f"- **모터 출력**: {test_set['pwm']}%\n")
            f.write(f"- **주행 시간**: {test_set['time']}초\n\n")
            
            # 테이블 헤더
            f.write("| 시도 | 거리(cm) | 속도(cm/s) |\n")
            f.write("|------|----------|------------|\n")
            
            # 각 시도 결과
            speeds = []
            for trial_idx, distance in enumerate(test_set['trials'], 1):
                speed = distance / test_set['time']
                speeds.append(speed)
                f.write(f"| {trial_idx} | {distance:.2f} | {speed:.2f} |\n")
            
            # 평균값 계산
            avg_distance = sum(test_set['trials']) / len(test_set['trials'])
            avg_speed = sum(speeds) / len(speeds)
            
            f.write(f"\n**📊 평균 거리**: {avg_distance:.2f} cm\n")
            f.write(f"**⭐ 평균 속도**: {avg_speed:.2f} cm/s\n\n")
            f.write("---\n\n")
        
        # 전체 요약 통계
        f.write("## 📈 전체 요약\n\n")
        
        # 출력별 평균 속도 정리
        pwm_speeds = {}  # {pwm값: [속도들]}
        for test_set in calibration_data:
            pwm = test_set['pwm']
            for distance in test_set['trials']:
                speed = distance / test_set['time']
                if pwm not in pwm_speeds:
                    pwm_speeds[pwm] = []
                pwm_speeds[pwm].append(speed)
        
        if pwm_speeds:
            f.write("### 출력별 평균 속도\n\n")
            f.write("| 출력(%) | 평균 속도(cm/s) | 측정 횟수 |\n")
            f.write("|---------|-----------------|----------|\n")
            
            for pwm in sorted(pwm_speeds.keys()):
                speeds = pwm_speeds[pwm]
                avg = sum(speeds) / len(speeds)
                f.write(f"| {pwm} | {avg:.2f} | {len(speeds)} |\n")
    
    print(f"✅ Markdown 리포트 생성 완료!")
    print(f"📄 파일 위치: {md_file}")

if __name__ == "__main__":
    import sys
    
    # 커맨드 라인 인자로 JSON 파일 경로를 받거나, 기본값 사용
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # 기본값: 현재 디렉토리의 calibration_data.json
        json_file = 'calibration_data.json'
    
    print(f"🔍 JSON 파일 읽는 중: {json_file}")
    generate_markdown_report(json_file)