"""
Real-time Training Visualization Dashboard
Combines multiple visualization tools: MLflow, TensorBoard, Custom Plots

Usage:
    python visualization_dashboard.py --experiment ship_defect_detection
"""

import os
import sys
import json
import time
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

try:
    from tensorboard import program
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False


class TrainingMonitor:
    """실시간 학습 모니터링 클래스"""

    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent

        self.base_dir = base_dir
        self.experiments_dir = base_dir / 'experiments'
        self.mlruns_dir = self.experiments_dir / 'mlruns'
        self.yolo_runs_dir = self.experiments_dir / 'yolo_runs'
        self.plots_dir = self.experiments_dir / 'plots'
        self.plots_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_history: Dict[str, List[float]] = {}
        self.class_names = ['blister', 'crack', 'peeling', 'sagging', 'welding_damage']

    def start_mlflow_ui(self, port: int = 5000) -> Optional[str]:
        """MLflow UI 시작"""
        if not MLFLOW_AVAILABLE:
            print("Warning: MLflow not installed")
            return None

        mlflow.set_tracking_uri(self.mlruns_dir.as_uri())
        url = f"http://localhost:{port}"

        def run_server():
            os.system(f"mlflow ui --backend-store-uri {self.mlruns_dir.as_uri()} --port {port}")

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        print(f"MLflow UI started at: {url}")
        return url

    def start_tensorboard(self, port: int = 6006) -> Optional[str]:
        """TensorBoard 시작"""
        if not TENSORBOARD_AVAILABLE:
            print("Warning: TensorBoard not installed")
            return None

        logdir = str(self.yolo_runs_dir)
        url = f"http://localhost:{port}"

        def run_server():
            os.system(f"tensorboard --logdir={logdir} --port={port}")

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        print(f"TensorBoard started at: {url}")
        return url

    def plot_training_curves(self, results_csv: Path, save_path: Path = None):
        """학습 곡선 시각화"""
        import pandas as pd

        if not results_csv.exists():
            print(f"Results file not found: {results_csv}")
            return

        df = pd.read_csv(results_csv)
        df.columns = df.columns.str.strip()

        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('YOLOv26n Training Progress', fontsize=14)

        # Box Loss
        if 'train/box_loss' in df.columns:
            axes[0, 0].plot(df['epoch'], df['train/box_loss'], 'b-', label='Train')
            if 'val/box_loss' in df.columns:
                axes[0, 0].plot(df['epoch'], df['val/box_loss'], 'r--', label='Val')
            axes[0, 0].set_title('Box Loss')
            axes[0, 0].set_xlabel('Epoch')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)

        # Class Loss
        if 'train/cls_loss' in df.columns:
            axes[0, 1].plot(df['epoch'], df['train/cls_loss'], 'b-', label='Train')
            if 'val/cls_loss' in df.columns:
                axes[0, 1].plot(df['epoch'], df['val/cls_loss'], 'r--', label='Val')
            axes[0, 1].set_title('Classification Loss')
            axes[0, 1].set_xlabel('Epoch')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)

        # DFL Loss
        if 'train/dfl_loss' in df.columns:
            axes[0, 2].plot(df['epoch'], df['train/dfl_loss'], 'b-', label='Train')
            if 'val/dfl_loss' in df.columns:
                axes[0, 2].plot(df['epoch'], df['val/dfl_loss'], 'r--', label='Val')
            axes[0, 2].set_title('DFL Loss')
            axes[0, 2].set_xlabel('Epoch')
            axes[0, 2].legend()
            axes[0, 2].grid(True, alpha=0.3)

        # mAP50
        if 'metrics/mAP50(B)' in df.columns:
            axes[1, 0].plot(df['epoch'], df['metrics/mAP50(B)'], 'g-', linewidth=2)
            axes[1, 0].set_title('mAP@50')
            axes[1, 0].set_xlabel('Epoch')
            axes[1, 0].set_ylim(0, 1)
            axes[1, 0].grid(True, alpha=0.3)

        # mAP50-95
        if 'metrics/mAP50-95(B)' in df.columns:
            axes[1, 1].plot(df['epoch'], df['metrics/mAP50-95(B)'], 'g-', linewidth=2)
            axes[1, 1].set_title('mAP@50-95')
            axes[1, 1].set_xlabel('Epoch')
            axes[1, 1].set_ylim(0, 1)
            axes[1, 1].grid(True, alpha=0.3)

        # Precision & Recall
        if 'metrics/precision(B)' in df.columns and 'metrics/recall(B)' in df.columns:
            axes[1, 2].plot(df['epoch'], df['metrics/precision(B)'], 'b-', label='Precision')
            axes[1, 2].plot(df['epoch'], df['metrics/recall(B)'], 'r-', label='Recall')
            axes[1, 2].set_title('Precision & Recall')
            axes[1, 2].set_xlabel('Epoch')
            axes[1, 2].set_ylim(0, 1)
            axes[1, 2].legend()
            axes[1, 2].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path is None:
            save_path = self.plots_dir / f'training_curves_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'

        plt.savefig(save_path, dpi=150)
        plt.close()

        print(f"Training curves saved to: {save_path}")
        return save_path

    def plot_class_performance(self, results_dir: Path, save_path: Path = None):
        """클래스별 성능 시각화"""
        # confusion matrix가 있는지 확인
        confusion_matrix_path = results_dir / 'confusion_matrix.png'
        if confusion_matrix_path.exists():
            print(f"Confusion matrix available at: {confusion_matrix_path}")

        # F1 curve
        f1_curve_path = results_dir / 'F1_curve.png'
        if f1_curve_path.exists():
            print(f"F1 curve available at: {f1_curve_path}")

        # PR curve
        pr_curve_path = results_dir / 'PR_curve.png'
        if pr_curve_path.exists():
            print(f"PR curve available at: {pr_curve_path}")

    def create_summary_report(self, run_dir: Path) -> Dict:
        """학습 결과 요약 리포트 생성"""
        report = {
            'run_dir': str(run_dir),
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'config': {},
        }

        # results.csv에서 최종 메트릭 추출
        results_csv = run_dir / 'results.csv'
        if results_csv.exists():
            import pandas as pd
            df = pd.read_csv(results_csv)
            df.columns = df.columns.str.strip()

            last_row = df.iloc[-1]
            report['metrics'] = {
                'final_epoch': int(last_row.get('epoch', 0)),
                'mAP50': float(last_row.get('metrics/mAP50(B)', 0)),
                'mAP50_95': float(last_row.get('metrics/mAP50-95(B)', 0)),
                'precision': float(last_row.get('metrics/precision(B)', 0)),
                'recall': float(last_row.get('metrics/recall(B)', 0)),
            }

        # args.yaml에서 설정 추출
        args_yaml = run_dir / 'args.yaml'
        if args_yaml.exists():
            import yaml
            with open(args_yaml, 'r') as f:
                report['config'] = yaml.safe_load(f)

        # 리포트 저장
        report_path = run_dir / 'training_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nTraining Summary Report")
        print("=" * 50)
        print(f"Run Directory: {run_dir}")
        print(f"\nFinal Metrics:")
        for key, value in report['metrics'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")

        return report

    def watch_training(self, run_name: str = None, refresh_interval: int = 30):
        """
        학습 진행 상황 실시간 모니터링

        Args:
            run_name: 모니터링할 run 이름 (None이면 최신 run)
            refresh_interval: 갱신 간격 (초)
        """
        print("Starting training monitor...")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                # 최신 run 폴더 찾기
                if run_name:
                    run_dir = self.yolo_runs_dir / run_name
                else:
                    runs = sorted(self.yolo_runs_dir.glob('*'), key=os.path.getmtime, reverse=True)
                    if not runs:
                        print("No training runs found. Waiting...")
                        time.sleep(refresh_interval)
                        continue
                    run_dir = runs[0]

                results_csv = run_dir / 'results.csv'
                if results_csv.exists():
                    import pandas as pd
                    df = pd.read_csv(results_csv)
                    df.columns = df.columns.str.strip()

                    if len(df) > 0:
                        last = df.iloc[-1]
                        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
                              f"Epoch: {int(last.get('epoch', 0)):3d} | "
                              f"mAP50: {last.get('metrics/mAP50(B)', 0):.4f} | "
                              f"mAP50-95: {last.get('metrics/mAP50-95(B)', 0):.4f} | "
                              f"Loss: {last.get('train/box_loss', 0):.4f}", end='')

                time.sleep(refresh_interval)

            except KeyboardInterrupt:
                print("\n\nMonitoring stopped.")
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(refresh_interval)


def launch_all_dashboards(base_dir: Path = None):
    """모든 시각화 대시보드 실행"""
    monitor = TrainingMonitor(base_dir)

    print("=" * 60)
    print("Launching Visualization Dashboards")
    print("=" * 60)

    urls = {}

    # MLflow UI
    mlflow_url = monitor.start_mlflow_ui(port=5000)
    if mlflow_url:
        urls['MLflow'] = mlflow_url

    # TensorBoard
    tb_url = monitor.start_tensorboard(port=6006)
    if tb_url:
        urls['TensorBoard'] = tb_url

    print("\n" + "=" * 60)
    print("Dashboard URLs:")
    for name, url in urls.items():
        print(f"  {name}: {url}")
    print("=" * 60)

    # 브라우저 열기
    for url in urls.values():
        try:
            webbrowser.open(url)
            time.sleep(1)
        except:
            pass

    return urls


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Training Visualization Dashboard')
    parser.add_argument('--launch', action='store_true', help='Launch all dashboards')
    parser.add_argument('--watch', action='store_true', help='Watch training progress')
    parser.add_argument('--run', type=str, default=None, help='Specific run name to monitor')
    parser.add_argument('--plot', type=str, default=None, help='Path to results.csv for plotting')
    parser.add_argument('--report', type=str, default=None, help='Generate report for run directory')

    args = parser.parse_args()

    monitor = TrainingMonitor()

    if args.launch:
        launch_all_dashboards()
        print("\nDashboards are running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")

    elif args.watch:
        monitor.watch_training(run_name=args.run)

    elif args.plot:
        monitor.plot_training_curves(Path(args.plot))

    elif args.report:
        monitor.create_summary_report(Path(args.report))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
