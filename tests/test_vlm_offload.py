"""Exercise placement decisions without downloading or allocating a VLM."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cv_extraction.config import validate_stages
from cv_extraction.extraction.methods import vlm_runtime
from cv_extraction.extraction.methods.vlm_structuring import structure_cv_images

GiB = 1024 ** 3


class VLMOffloadTests(unittest.TestCase):
    def setUp(self):
        self.model = Mock()
        # A CPU first parameter must not send inputs to CPU when the hook runs on CUDA.
        self.model.device = 'cpu'
        self.model.hf_device_map = {'visual': 'cpu', 'language_model': 0}
        self.model._hf_hook = SimpleNamespace(execution_device=0)
        self.torch = SimpleNamespace(
            float16='float16',
            cuda=SimpleNamespace(
                is_available=Mock(return_value=True),
                mem_get_info=Mock(return_value=(8 * GiB, 8 * GiB)),
                synchronize=Mock(),
            ),
        )
        self.transformers = SimpleNamespace(
            AutoProcessor=SimpleNamespace(from_pretrained=Mock()),
            BitsAndBytesConfig=Mock(),
            Qwen3VLForConditionalGeneration=SimpleNamespace(from_pretrained=Mock(return_value=self.model)),
        )
        self.modules = patch.dict('sys.modules', {
            'torch': self.torch,
            'transformers': self.transformers,
            'psutil': SimpleNamespace(virtual_memory=lambda: SimpleNamespace(available=20 * GiB)),
        })
        self.cache = patch.multiple(vlm_runtime, _RUNTIME=None, _RUNTIME_KEY=None)
        self.modules.start()
        self.cache.start()
        self.addCleanup(self.modules.stop)
        self.addCleanup(self.cache.stop)

    def test_cpu_offload_uses_budget_and_execution_device(self):
        result = vlm_runtime.get_vlm_runtime('test-model', True, True)
        kwargs = self.transformers.Qwen3VLForConditionalGeneration.from_pretrained.call_args.kwargs
        self.assertEqual(kwargs['device_map'], 'auto')
        self.assertEqual(kwargs['max_memory'], {0: 6 * GiB, 'cpu': 16 * GiB})
        self.assertTrue(self.transformers.BitsAndBytesConfig.call_args.kwargs['llm_int8_enable_fp32_cpu_offload'])
        self.assertEqual(result['input_device'], 'cuda:0')
        self.assertTrue(result['cpu_offload_used'])

    def test_original_gpu_only_loading_is_preserved(self):
        self.model.device = 'cuda:0'
        self.model.hf_device_map = {'': 0}
        result = vlm_runtime.get_vlm_runtime('test-model', True)
        kwargs = self.transformers.Qwen3VLForConditionalGeneration.from_pretrained.call_args.kwargs
        self.assertEqual(kwargs['device_map'], {'': 0})
        self.assertNotIn('max_memory', kwargs)
        self.assertFalse(result['cpu_offload_used'])

    def test_placement_change_does_not_silently_reuse_runtime(self):
        vlm_runtime.get_vlm_runtime('test-model', True, True)
        self.assertTrue(vlm_runtime.get_vlm_runtime('test-model', True, True)['model_reused'])
        with self.assertRaisesRegex(ValueError, 'separate experiment process'):
            vlm_runtime.get_vlm_runtime('test-model', True, False)

    def test_disk_placement_is_not_silently_enabled(self):
        self.model.hf_device_map = {'visual': 0, 'language_model': 'disk'}
        with self.assertRaisesRegex(RuntimeError, 'disk offloading is not enabled'):
            vlm_runtime.get_vlm_runtime('test-model', True, True)
        self.assertIsNone(vlm_runtime._RUNTIME)

    def test_gpu_remains_required(self):
        self.torch.cuda.is_available.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'CUDA-enabled'):
            vlm_runtime.get_vlm_runtime('test-model', True, True)
        self.transformers.Qwen3VLForConditionalGeneration.from_pretrained.assert_not_called()

    def test_missing_root_hook_uses_first_accelerator(self):
        self.model._hf_hook = None
        result = vlm_runtime.get_vlm_runtime('test-model', True, True)
        self.assertEqual(result['input_device'], 'cuda:0')


class VLMConfigurationTests(unittest.TestCase):
    def test_new_and_existing_stage_configs_validate(self):
        config = json.loads((Path(__file__).parents[1] / 'experiments/configs/vision_extraction.json').read_text())
        validate_stages(config['stages'])
        legacy = copy.deepcopy(config['stages'])
        legacy[-1]['settings'].pop('allow_cpu_offload')
        validate_stages(legacy)
        invalid = copy.deepcopy(config['stages'])
        invalid[-1]['settings']['allow_cpu_offload'] = 'true'
        with self.assertRaises(ValueError):
            validate_stages(invalid)

    def test_inputs_use_execution_device_and_placement_is_reported(self):
        from contextlib import nullcontext

        tokens = Mock()
        tokens.shape = [1, 1]
        output = Mock()
        output.__getitem__ = Mock(return_value=tokens)
        inputs = {'input_ids': SimpleNamespace(shape=[1, 3])}
        batch = Mock()
        batch.pop = Mock()
        batch.to.return_value = inputs
        processor = Mock()
        processor.apply_chat_template.return_value = batch
        processor.batch_decode.return_value = ['{}']
        model = Mock()
        model.device = 'cpu'
        model.generate.return_value = output
        runtime = dict(processor=processor, model=model, input_device='cuda:0',
                       device_map={'visual': 'cpu', 'language_model': '0'},
                       cpu_offload_used=True, max_memory={'0': 6 * GiB},
                       model_load_seconds=1., model_reused=False)
        cuda = Mock()
        for name in ['memory_allocated', 'max_memory_allocated', 'max_memory_reserved']:
            getattr(cuda, name).return_value = 0
        torch = SimpleNamespace(cuda=cuda, inference_mode=nullcontext)
        image = Mock()
        image.__enter__ = Mock(return_value=image)
        image.__exit__ = Mock(return_value=False)
        image.convert.return_value = Mock()
        with patch.dict('sys.modules', {'torch': torch}), \
             patch('PIL.Image.open', return_value=image), \
             patch('cv_extraction.extraction.methods.vlm_structuring.get_vlm_runtime', return_value=runtime):
            result = structure_cv_images(
                {'pages': [{'page_number': 1, 'image_path': 'unused.png'}], 'dpi': 120},
                'test-model', True, 10, allow_cpu_offload=True,
                max_pixels=301056, gpu_memory_fraction=0.85,
            )
        batch.to.assert_called_once_with('cuda:0')
        self.assertTrue(result['metrics']['cpu_offload_used'])
        self.assertEqual(result['metrics']['device_map'], runtime['device_map'])
        self.assertTrue(result['artifacts']['request']['allow_cpu_offload'])
        cuda.set_per_process_memory_fraction.assert_called_once_with(0.85, 0)
        self.assertEqual(processor.apply_chat_template.call_args.kwargs['processor_kwargs'],
                         {'images_kwargs': {'size': {'shortest_edge': 65536, 'longest_edge': 301056}}})
        self.assertEqual(model.generate.call_args.kwargs['logits_to_keep'], 1)


if __name__ == '__main__':
    unittest.main()
