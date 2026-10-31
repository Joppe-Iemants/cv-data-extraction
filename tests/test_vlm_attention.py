"""The memory-saving attention adapter must preserve grouped-query results."""
from types import SimpleNamespace
import unittest

import torch

from cv_extraction.extraction.methods.vlm_attention import expanded_kv_sdpa


class AttentionTests(unittest.TestCase):
    def test_prefill_decode_and_mask_match_native_gqa(self):
        generator = torch.Generator().manual_seed(42)
        for length, causal, masked in [(5, True, False), (1, True, False), (5, False, True)]:
            with self.subTest(length=length, masked=masked):
                query = torch.randn(1, 4, length, 8, generator=generator)
                key = torch.randn(1, 2, 5, 8, generator=generator)
                value = torch.randn(1, 2, 5, 8, generator=generator)
                mask = torch.ones(length, 5, dtype=torch.bool) if masked else None
                if mask is not None:
                    mask[:, -1] = False
                expected = torch.nn.functional.scaled_dot_product_attention(
                    query, key, value, attn_mask=mask,
                    is_causal=causal and length > 1 and mask is None,
                    enable_gqa=True,
                )
                actual, weights = expanded_kv_sdpa(
                    SimpleNamespace(is_causal=causal), query, key, value, mask,
                )
                torch.testing.assert_close(actual, expected.transpose(1, 2))
                self.assertIsNone(weights)


if __name__ == '__main__':
    unittest.main()
