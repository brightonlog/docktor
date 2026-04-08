import torch
import tensorrt as trt
import os

def convert_pt_to_tensorrt(pt_path, onnx_path, engine_path, input_shape=(1, 3, 224, 224)):
    """
    Convert PyTorch model (.pt) to TensorRT engine via ONNX intermediate format.

    Args:
        pt_path (str): Path to the PyTorch model file (.pt)
        onnx_path (str): Path to save the ONNX model
        engine_path (str): Path to save the TensorRT engine
        input_shape (tuple): Input shape for the model (batch_size, channels, height, width)
    """
    # Load PyTorch model
    print(f"Loading PyTorch model from {pt_path}")
    model = torch.load(pt_path, map_location='cpu')
    model.eval()

    # Create dummy input
    dummy_input = torch.randn(*input_shape)

    # Export to ONNX
    print(f"Exporting to ONNX: {onnx_path}")
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        verbose=True,
        input_names=['input'],
        output_names=['output'],
        opset_version=11
    )

    # Convert ONNX to TensorRT engine
    print(f"Converting ONNX to TensorRT engine: {engine_path}")
    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

    with trt.Builder(TRT_LOGGER) as builder, \
         builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)) as network, \
         trt.OnnxParser(network, TRT_LOGGER) as parser:

        # Parse ONNX model
        with open(onnx_path, 'rb') as model_file:
            if not parser.parse(model_file.read()):
                print("Failed to parse ONNX model")
                for error in range(parser.num_errors):
                    print(parser.get_error(error))
                return False

        # Create builder config
        config = builder.create_builder_config()
        config.max_workspace_size = 1 << 30  # 1GB workspace

        # Build engine
        engine = builder.build_engine(network, config)
        if engine is None:
            print("Failed to build TensorRT engine")
            return False

        # Serialize and save engine
        with open(engine_path, 'wb') as f:
            f.write(engine.serialize())

        print(f"TensorRT engine saved to {engine_path}")
        return True

if __name__ == "__main__":
    # Paths
    pt_file = "kyr/best_fixed.pt"
    onnx_file = "best_fixed.onnx"
    engine_file = "best_fixed.engine"

    # Note: Adjust input_shape based on your model's requirements
    # For YOLO models, it might be (1, 3, 640, 640) or similar
    input_shape = (1, 3, 640, 640)  # Default; modify as needed

    if not os.path.exists(pt_file):
        print(f"Error: {pt_file} not found")
        exit(1)

    success = convert_pt_to_tensorrt(pt_file, onnx_file, engine_file, input_shape)
    if success:
        print("Conversion completed successfully!")
    else:
        print("Conversion failed!")