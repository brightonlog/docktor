#!/usr/bin/env python3
"""
Prometheus Metrics Exporter for Training
실시간 학습 메트릭을 Prometheus로 export
"""

import time
import sys
from pathlib import Path
from prometheus_client import start_http_server, Gauge, Counter, Info
import pandas as pd
from threading import Thread
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.training_config import PROMETHEUS_PORT


# Define metrics
training_info = Info('yolov8_training', 'Training information')

# Loss metrics
train_box_loss = Gauge('yolov8_train_box_loss', 'Training box loss')
train_cls_loss = Gauge('yolov8_train_cls_loss', 'Training classification loss')
train_dfl_loss = Gauge('yolov8_train_dfl_loss', 'Training DFL loss')

val_box_loss = Gauge('yolov8_val_box_loss', 'Validation box loss')
val_cls_loss = Gauge('yolov8_val_cls_loss', 'Validation classification loss')
val_dfl_loss = Gauge('yolov8_val_dfl_loss', 'Validation DFL loss')

# Performance metrics
precision = Gauge('yolov8_precision', 'Precision')
recall = Gauge('yolov8_recall', 'Recall')
map50 = Gauge('yolov8_map50', 'mAP@0.5')
map50_95 = Gauge('yolov8_map50_95', 'mAP@0.5:0.95')

# Training progress
current_epoch = Gauge('yolov8_current_epoch', 'Current epoch')
total_epochs = Gauge('yolov8_total_epochs', 'Total epochs')
training_time = Gauge('yolov8_training_time_seconds', 'Training time in seconds')

# System metrics (if available)
try:
    import GPUtil
    gpu_utilization = Gauge('yolov8_gpu_utilization', 'GPU utilization %')
    gpu_memory_used = Gauge('yolov8_gpu_memory_used_mb', 'GPU memory used in MB')
    gpu_memory_total = Gauge('yolov8_gpu_memory_total_mb', 'GPU memory total in MB')
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# Counters
training_runs = Counter('yolov8_training_runs_total', 'Total training runs')


class PrometheusExporter:
    """
    Export training metrics to Prometheus
    """

    def __init__(self, results_csv=None, port=PROMETHEUS_PORT):
        """
        Args:
            results_csv: Path to YOLO results.csv file
            port: Prometheus metrics port
        """
        self.results_csv = results_csv
        self.port = port
        self.running = False
        self.start_time = None

    def start_server(self):
        """Start Prometheus HTTP server"""
        print(f"Starting Prometheus metrics server on port {self.port}")
        start_http_server(self.port)
        print(f"Metrics available at http://localhost:{self.port}/metrics")

    def update_gpu_metrics(self):
        """Update GPU metrics if available"""
        if not GPU_AVAILABLE:
            return

        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Use first GPU
                gpu_utilization.set(gpu.load * 100)
                gpu_memory_used.set(gpu.memoryUsed)
                gpu_memory_total.set(gpu.memoryTotal)
        except Exception as e:
            pass

    def update_from_csv(self):
        """Update metrics from results.csv"""
        if not self.results_csv or not Path(self.results_csv).exists():
            return

        try:
            df = pd.read_csv(self.results_csv)

            if len(df) == 0:
                return

            # Get latest row
            latest = df.iloc[-1]

            # Update loss metrics
            if 'train/box_loss' in latest:
                train_box_loss.set(latest['train/box_loss'])
            if 'train/cls_loss' in latest:
                train_cls_loss.set(latest['train/cls_loss'])
            if 'train/dfl_loss' in latest:
                train_dfl_loss.set(latest['train/dfl_loss'])

            if 'val/box_loss' in latest:
                val_box_loss.set(latest['val/box_loss'])
            if 'val/cls_loss' in latest:
                val_cls_loss.set(latest['val/cls_loss'])
            if 'val/dfl_loss' in latest:
                val_dfl_loss.set(latest['val/dfl_loss'])

            # Update performance metrics
            if 'metrics/precision(B)' in latest:
                precision.set(latest['metrics/precision(B)'])
            if 'metrics/recall(B)' in latest:
                recall.set(latest['metrics/recall(B)'])
            if 'metrics/mAP50(B)' in latest:
                map50.set(latest['metrics/mAP50(B)'])
            if 'metrics/mAP50-95(B)' in latest:
                map50_95.set(latest['metrics/mAP50-95(B)'])

            # Update epoch
            if 'epoch' in latest:
                current_epoch.set(latest['epoch'])

            # Update training time
            if self.start_time:
                elapsed = time.time() - self.start_time
                training_time.set(elapsed)

        except Exception as e:
            print(f"Error updating metrics from CSV: {e}")

    def monitor_loop(self, interval=5):
        """
        Main monitoring loop

        Args:
            interval: Update interval in seconds
        """
        self.running = True
        self.start_time = time.time()

        print(f"Monitoring started. Updating every {interval}s")

        while self.running:
            try:
                # Update metrics
                self.update_from_csv()
                self.update_gpu_metrics()

                time.sleep(interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(interval)

    def start_monitoring(self, interval=5):
        """
        Start monitoring in background thread

        Args:
            interval: Update interval in seconds
        """
        self.start_server()

        # Start monitoring thread
        monitor_thread = Thread(target=self.monitor_loop, args=(interval,), daemon=True)
        monitor_thread.start()

        return monitor_thread

    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Prometheus metrics exporter')
    parser.add_argument('--csv', type=str, required=True,
                       help='Path to YOLO results.csv')
    parser.add_argument('--port', type=int, default=PROMETHEUS_PORT,
                       help=f'Prometheus port (default: {PROMETHEUS_PORT})')
    parser.add_argument('--interval', type=int, default=5,
                       help='Update interval in seconds (default: 5)')
    parser.add_argument('--epochs', type=int, default=100,
                       help='Total epochs (for progress tracking)')
    args = parser.parse_args()

    # Set total epochs
    total_epochs.set(args.epochs)

    # Increment training runs counter
    training_runs.inc()

    # Create exporter
    exporter = PrometheusExporter(results_csv=args.csv, port=args.port)

    # Start monitoring
    exporter.start_monitoring(interval=args.interval)

    print(f"\nMonitoring {args.csv}")
    print("Press Ctrl+C to stop")

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping exporter...")
        exporter.stop_monitoring()


if __name__ == "__main__":
    main()
