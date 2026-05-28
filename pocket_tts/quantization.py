"""
Dynamic int8 quantization for pocket-tts using torchao.

Quantizes attention (Q/K/V/output projections) and FFN (linear1/linear2) layers
in the FlowLM transformer. The flow matching network and Mimi VAE decoder
remain in float32.

Requires torchao (install via ``uv add torchao`` or ``pip install pocket-tts[quantize]``).
"""

import logging

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

RECOMMENDED_CONFIG = {"attention", "ffn"}


def _get_backend() -> str:
    """Detect if torchao is available.

    Returns "torchao" if torchao is installed, otherwise raises ImportError.
    """
    try:
        import importlib.util

        if importlib.util.find_spec("torchao") is None:
            raise ImportError("torchao is not installed")
        import torchao  # noqa: F401

        return "torchao"
    except ImportError:
        logger.error(
            "torchao is required for quantization. Install with: uv add torchao"
        )
        raise


def _quantize_module(module: nn.Module):
    """Apply int8 dynamic quantization using torchao.

    Modifies the module in-place by replacing its linear layers
    with int8 dynamically-quantized versions.
    """
    from torchao.quantization import Int8DynamicActivationInt8WeightConfig, quantize_

    quantize_(module, Int8DynamicActivationInt8WeightConfig())


def apply_dynamic_int8(flow_lm: nn.Module, quantize_groups: set[str]) -> nn.Module:
    """
    Apply int8 dynamic quantization to the specified layer groups of a FlowLM model.

    Args:
        flow_lm: The FlowLM model (model.flow_lm).
        quantize_groups: Set of group keys to quantize.
            Valid keys: "attention", "ffn", "flow_net".

    Returns:
        The quantized model (modified in-place).
    """
    if not quantize_groups:
        logger.info("No quantization groups specified, returning model unchanged.")
        return flow_lm

    _get_backend()
    logger.info("Applying torchao int8 dynamic quantization")

    if "flow_net" in quantize_groups:
        _quantize_module(flow_lm.flow_net)

    for layer in flow_lm.transformer.layers:
        if "attention" in quantize_groups:
            _quantize_module(layer.self_attn)

        if "ffn" in quantize_groups:
            _quantize_module(layer.linear1)
            _quantize_module(layer.linear2)

    return flow_lm
