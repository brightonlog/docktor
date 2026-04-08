#!/usr/bin/env python3
"""
MLflow Model Registry Manager
모델 버전 관리 및 배포 스테이지 관리
"""

import sys
from pathlib import Path
from mlflow.tracking import MlflowClient
import mlflow
import argparse

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False
    print("Warning: tabulate not installed. Install with: pip install tabulate")
    print("Falling back to simple table format\n")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.training_config import MLFLOW_TRACKING_URI

# Set MLflow tracking URI
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

MODEL_NAME = "yolov8-ship-defect-detector"


class ModelRegistry:
    """
    MLflow Model Registry Manager
    """

    def __init__(self, model_name=MODEL_NAME):
        """
        Args:
            model_name: Registered model name
        """
        self.model_name = model_name
        self.client = MlflowClient()

    def list_versions(self):
        """
        List all model versions

        Returns:
            versions: List of model versions
        """
        try:
            versions = self.client.search_model_versions(f"name='{self.model_name}'")

            if not versions:
                print(f"No versions found for model: {self.model_name}")
                return []

            # Prepare table data
            table_data = []
            for v in sorted(versions, key=lambda x: int(x.version), reverse=True):
                table_data.append([
                    v.version,
                    v.current_stage,
                    v.run_id[:8],
                    v.status,
                    v.creation_timestamp
                ])

            # Print table
            headers = ["Version", "Stage", "Run ID", "Status", "Created"]
            print(f"\nModel: {self.model_name}")
            print("=" * 80)

            if TABULATE_AVAILABLE:
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
            else:
                # Simple fallback
                print(" | ".join(headers))
                print("-" * 80)
                for row in table_data:
                    print(" | ".join(str(x) for x in row))

            print("=" * 80)

            return versions

        except Exception as e:
            print(f"Error listing versions: {e}")
            return []

    def get_latest_version(self, stage=None):
        """
        Get latest model version

        Args:
            stage: Filter by stage (None, 'Staging', 'Production', 'Archived')

        Returns:
            version: Latest model version
        """
        try:
            if stage:
                versions = self.client.get_latest_versions(self.model_name, stages=[stage])
            else:
                versions = self.client.search_model_versions(f"name='{self.model_name}'")
                versions = sorted(versions, key=lambda x: int(x.version), reverse=True)

            if versions:
                latest = versions[0]
                print(f"\nLatest version: {latest.version}")
                print(f"Stage: {latest.current_stage}")
                print(f"Run ID: {latest.run_id}")
                return latest
            else:
                print(f"No versions found for model: {self.model_name}")
                return None

        except Exception as e:
            print(f"Error getting latest version: {e}")
            return None

    def transition_stage(self, version, stage):
        """
        Transition model version to a new stage

        Args:
            version: Model version number
            stage: Target stage ('Staging', 'Production', 'Archived')

        Returns:
            success: Whether transition succeeded
        """
        valid_stages = ['None', 'Staging', 'Production', 'Archived']
        if stage not in valid_stages:
            print(f"Error: Invalid stage '{stage}'. Must be one of {valid_stages}")
            return False

        try:
            self.client.transition_model_version_stage(
                name=self.model_name,
                version=version,
                stage=stage,
                archive_existing_versions=False
            )
            print(f"\nSuccessfully transitioned version {version} to {stage}")
            return True

        except Exception as e:
            print(f"Error transitioning stage: {e}")
            return False

    def promote_to_production(self, version, archive_old=True):
        """
        Promote model version to Production

        Args:
            version: Model version to promote
            archive_old: Whether to archive old production versions

        Returns:
            success: Whether promotion succeeded
        """
        try:
            self.client.transition_model_version_stage(
                name=self.model_name,
                version=version,
                stage='Production',
                archive_existing_versions=archive_old
            )
            print(f"\nSuccessfully promoted version {version} to Production")
            if archive_old:
                print("Old production versions have been archived")
            return True

        except Exception as e:
            print(f"Error promoting to production: {e}")
            return False

    def load_model(self, version=None, stage=None):
        """
        Load model from registry

        Args:
            version: Specific version to load
            stage: Load latest from stage ('Staging', 'Production')

        Returns:
            model_path: Path to loaded model
        """
        try:
            if version:
                model_uri = f"models:/{self.model_name}/{version}"
            elif stage:
                model_uri = f"models:/{self.model_name}/{stage}"
            else:
                # Load latest version
                latest = self.get_latest_version()
                if latest:
                    model_uri = f"models:/{self.model_name}/{latest.version}"
                else:
                    print("No model versions found")
                    return None

            # Download model
            model_path = mlflow.artifacts.download_artifacts(model_uri)
            print(f"\nLoaded model from: {model_uri}")
            print(f"Local path: {model_path}")
            return model_path

        except Exception as e:
            print(f"Error loading model: {e}")
            return None

    def delete_version(self, version):
        """
        Delete model version

        Args:
            version: Model version to delete

        Returns:
            success: Whether deletion succeeded
        """
        try:
            self.client.delete_model_version(
                name=self.model_name,
                version=version
            )
            print(f"\nSuccessfully deleted version {version}")
            return True

        except Exception as e:
            print(f"Error deleting version: {e}")
            return False

    def get_model_info(self, version):
        """
        Get detailed information about a model version

        Args:
            version: Model version

        Returns:
            info: Model version info
        """
        try:
            model_version = self.client.get_model_version(
                name=self.model_name,
                version=version
            )

            print(f"\nModel: {self.model_name}")
            print(f"Version: {model_version.version}")
            print(f"Stage: {model_version.current_stage}")
            print(f"Status: {model_version.status}")
            print(f"Run ID: {model_version.run_id}")
            print(f"Created: {model_version.creation_timestamp}")
            print(f"Description: {model_version.description}")

            # Get run metrics
            run = mlflow.get_run(model_version.run_id)
            print("\nMetrics:")
            for key, value in run.data.metrics.items():
                print(f"  {key}: {value:.4f}")

            # Get run parameters
            print("\nParameters:")
            for key, value in run.data.params.items():
                print(f"  {key}: {value}")

            return model_version

        except Exception as e:
            print(f"Error getting model info: {e}")
            return None

    def compare_versions(self, versions=None):
        """
        Compare performance metrics across model versions

        Args:
            versions: List of version numbers to compare (None = all versions)

        Returns:
            comparison: List of version metrics
        """
        try:
            all_versions = self.client.search_model_versions(f"name='{self.model_name}'")

            if not all_versions:
                print(f"No versions found for model: {self.model_name}")
                return []

            # Filter versions if specified
            if versions:
                all_versions = [v for v in all_versions if v.version in versions]

            # Collect metrics for each version
            comparison_data = []
            for v in sorted(all_versions, key=lambda x: int(x.version)):
                run = mlflow.get_run(v.run_id)

                metrics = run.data.metrics
                params = run.data.params

                comparison_data.append({
                    'version': v.version,
                    'stage': v.current_stage,
                    'model': params.get('model', 'N/A'),
                    'epochs': params.get('epochs', 'N/A'),
                    'batch_size': params.get('batch_size', 'N/A'),
                    'mAP50': metrics.get('metrics/mAP50', 0),
                    'mAP50-95': metrics.get('metrics/mAP50-95', 0),
                    'precision': metrics.get('metrics/precision', 0),
                    'recall': metrics.get('metrics/recall', 0),
                    'run_id': v.run_id[:8]
                })

            # Print comparison table
            if comparison_data:
                table_data = []
                for d in comparison_data:
                    table_data.append([
                        d['version'],
                        d['stage'],
                        d['model'],
                        d['epochs'],
                        d['batch_size'],
                        f"{d['mAP50']:.4f}",
                        f"{d['mAP50-95']:.4f}",
                        f"{d['precision']:.4f}",
                        f"{d['recall']:.4f}",
                        d['run_id']
                    ])

                headers = ["Ver", "Stage", "Model", "Epochs", "Batch", "mAP50", "mAP50-95", "Precision", "Recall", "Run ID"]
                print(f"\nModel Performance Comparison: {self.model_name}")
                print("=" * 120)

                if TABULATE_AVAILABLE:
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                else:
                    # Simple fallback
                    print(" | ".join(headers))
                    print("-" * 120)
                    for row in table_data:
                        print(" | ".join(str(x) for x in row))

                print("=" * 120)

                # Find best model
                best_map50 = max(comparison_data, key=lambda x: x['mAP50'])
                best_map50_95 = max(comparison_data, key=lambda x: x['mAP50-95'])

                print("\nBest Models:")
                print(f"  Best mAP50: Version {best_map50['version']} ({best_map50['mAP50']:.4f})")
                print(f"  Best mAP50-95: Version {best_map50_95['version']} ({best_map50_95['mAP50-95']:.4f})")

            return comparison_data

        except Exception as e:
            print(f"Error comparing versions: {e}")
            return []

    def get_best_model(self, metric='mAP50'):
        """
        Get best performing model version

        Args:
            metric: Metric to optimize ('mAP50', 'mAP50-95', 'precision', 'recall')

        Returns:
            best_version: Best model version info
        """
        try:
            versions = self.client.search_model_versions(f"name='{self.model_name}'")

            if not versions:
                print(f"No versions found for model: {self.model_name}")
                return None

            # Collect metrics
            version_metrics = []
            metric_map = {
                'mAP50': 'metrics/mAP50',
                'mAP50-95': 'metrics/mAP50-95',
                'precision': 'metrics/precision',
                'recall': 'metrics/recall'
            }

            if metric not in metric_map:
                print(f"Invalid metric: {metric}. Choose from {list(metric_map.keys())}")
                return None

            mlflow_metric = metric_map[metric]

            for v in versions:
                run = mlflow.get_run(v.run_id)
                metric_value = run.data.metrics.get(mlflow_metric, 0)
                version_metrics.append((v, metric_value))

            # Find best
            best_version, best_value = max(version_metrics, key=lambda x: x[1])

            print(f"\nBest model by {metric}:")
            print(f"  Version: {best_version.version}")
            print(f"  Stage: {best_version.current_stage}")
            print(f"  {metric}: {best_value:.4f}")
            print(f"  Run ID: {best_version.run_id}")

            return best_version

        except Exception as e:
            print(f"Error getting best model: {e}")
            return None


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='MLflow Model Registry Manager')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List versions
    subparsers.add_parser('list', help='List all model versions')

    # Get latest
    latest_parser = subparsers.add_parser('latest', help='Get latest model version')
    latest_parser.add_argument('--stage', type=str, help='Filter by stage')

    # Transition stage
    stage_parser = subparsers.add_parser('stage', help='Transition model stage')
    stage_parser.add_argument('version', type=str, help='Model version')
    stage_parser.add_argument('stage', type=str,
                             choices=['None', 'Staging', 'Production', 'Archived'],
                             help='Target stage')

    # Promote to production
    promote_parser = subparsers.add_parser('promote', help='Promote to Production')
    promote_parser.add_argument('version', type=str, help='Model version')
    promote_parser.add_argument('--no-archive', action='store_true',
                               help='Do not archive old production versions')

    # Load model
    load_parser = subparsers.add_parser('load', help='Load model')
    load_parser.add_argument('--version', type=str, help='Model version')
    load_parser.add_argument('--stage', type=str, help='Load from stage')

    # Model info
    info_parser = subparsers.add_parser('info', help='Get model info')
    info_parser.add_argument('version', type=str, help='Model version')

    # Delete version
    delete_parser = subparsers.add_parser('delete', help='Delete model version')
    delete_parser.add_argument('version', type=str, help='Model version')

    # Compare versions
    compare_parser = subparsers.add_parser('compare', help='Compare model versions')
    compare_parser.add_argument('--versions', nargs='+', help='Versions to compare (default: all)')

    # Get best model
    best_parser = subparsers.add_parser('best', help='Get best performing model')
    best_parser.add_argument('--metric', type=str, default='mAP50',
                            choices=['mAP50', 'mAP50-95', 'precision', 'recall'],
                            help='Metric to optimize (default: mAP50)')

    args = parser.parse_args()

    # Create registry manager
    registry = ModelRegistry()

    # Execute command
    if args.command == 'list':
        registry.list_versions()

    elif args.command == 'latest':
        registry.get_latest_version(stage=args.stage)

    elif args.command == 'stage':
        registry.transition_stage(args.version, args.stage)

    elif args.command == 'promote':
        registry.promote_to_production(args.version, archive_old=not args.no_archive)

    elif args.command == 'load':
        registry.load_model(version=args.version, stage=args.stage)

    elif args.command == 'info':
        registry.get_model_info(args.version)

    elif args.command == 'delete':
        registry.delete_version(args.version)

    elif args.command == 'compare':
        registry.compare_versions(versions=args.versions)

    elif args.command == 'best':
        registry.get_best_model(metric=args.metric)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
