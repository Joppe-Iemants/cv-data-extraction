"""SDPA adapter for CUDA builds without fused grouped-query attention.

Expanding the KV heads is mathematically equivalent to enable_gqa=True, but
lets PyTorch select its memory-efficient kernel on native Windows builds.
"""


def expanded_kv_sdpa(module, query, key, value, attention_mask, dropout=0.0,
                     scaling=None, is_causal=None, **kwargs):
    import torch

    groups = query.shape[1] // key.shape[1]
    if groups > 1:
        key = key.repeat_interleave(groups, dim=1)
        value = value.repeat_interleave(groups, dim=1)
    causal = getattr(module, 'is_causal', True) if is_causal is None else is_causal
    causal = bool(causal and query.shape[2] > 1 and attention_mask is None)
    output = torch.nn.functional.scaled_dot_product_attention(
        query, key, value, attn_mask=attention_mask, dropout_p=dropout,
        scale=scaling, is_causal=causal,
    )
    return output.transpose(1, 2).contiguous(), None


def register_expanded_kv_sdpa():
    from transformers import AttentionInterface
    from transformers.masking_utils import AttentionMaskInterface

    AttentionInterface.register('expanded_kv_sdpa', expanded_kv_sdpa)
    AttentionMaskInterface.register('expanded_kv_sdpa', AttentionMaskInterface()['sdpa'])
    return 'expanded_kv_sdpa'
