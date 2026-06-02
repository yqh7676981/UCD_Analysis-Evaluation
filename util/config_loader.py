"""
Unified configuration loader for OpenDesign Benchmark.
Loads all settings from config.yaml.
"""

import yaml
import os
from pathlib import Path


class Config:
    """Singleton configuration loader."""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        # Find config.yaml in project root (util -> project root)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        config_path = project_root / "config.yaml"

        if not config_path.exists():
            # Fallback: search upward for config.yaml
            search_dir = Path.cwd()
            for _ in range(5):  # Search up 5 levels
                config_path = search_dir / "config.yaml"
                if config_path.exists():
                    break
                search_dir = search_dir.parent

        if not config_path.exists():
            raise FileNotFoundError(f"config.yaml not found. Searched from {project_root}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

        # Replace environment variables
        self._replace_env_vars(self._config)
    
    def _replace_env_vars(self, obj):
        """Recursively replace ${VAR} with environment variables."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    obj[key] = os.getenv(env_var)
                elif isinstance(value, (dict, list)):
                    self._replace_env_vars(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str) and item.startswith('${') and item.endswith('}'):
                    env_var = item[2:-1]
                    obj[i] = os.getenv(env_var)
                elif isinstance(item, (dict, list)):
                    self._replace_env_vars(item)
    
    def get(self, key_path, default=None):
        """
        Get configuration value by dot-separated path.
        
        Example:
            config.get('openai.api_key')
            config.get('generation.temperature')
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_all(self):
        """Get entire configuration dictionary."""
        return self._config
    
    @property
    def model_to_evaluate(self):
        """Get model name from MODEL config (maps to MODEL in config.yaml)."""
        return self.get('MODEL')
    
    @property
    def model(self):
        """Get model name (alias for model_to_evaluate)."""
        return self.get('MODEL')
    
    @property
    def url(self):
        """Get API URL."""
        return self.get('URL')
    
    @property
    def api_key(self):
        """Get API key."""
        return self.get('API_KEY')
    
    @property
    def repeat_times(self):
        """Get repeat times."""
        return self.get('REPEAT_TIMES', 1)
    
    @property
    def data_source(self):
        """Get data source path."""
        return self.get('DATA_SOURCE')
    
    @property
    def data_file(self):
        """Get processed data file path (tmp file with purified HTML)."""
        original = self.get('benchmark.data_file', 'test.jsonl')
        return original.replace('.jsonl', '_tmp.jsonl')
    
    @property
    def use_api(self):
        return self.get('use_api', True)
    
    @property
    def judge_model(self):
        """Deprecated: use static_judge_config or interactive_judge_config instead."""
        return self.get('static_judge.model', 'gpt-4o')
    
    @property
    def num_threads(self):
        return self.get('generation.num_threads', 32)
    
    @property
    def output_dir(self):
        return self.get('benchmark.output_dir', 'arena-bench-result')
    
    @property
    def openai_config(self):
        """Get OpenAI API configuration for answer generation."""
        return {
            'api_key': self.api_key,
            'base_url': self.url,
            'model': self.model,
            'max_tokens': self.get('openai.max_tokens', 8192),
            'temperature': self.get('openai.temperature', 0.7),
        }
    
    @property
    def screenshot_config(self):
        """Get screenshot configuration."""
        return {
            'max_workers': self.get('screenshot.max_workers', 4),
            'timeout': self.get('screenshot.timeout', 120),
            'batch_size': self.get('screenshot.batch_size', 100),
            'widths': self.get('screenshot.widths', [1280, 390, 768]),
            'judge_widths': self.get('judge_widths', [1280, 390, 768]),
        }
    
    @property
    def static_judge_config(self):
        """Get static aesthetics judge model configuration."""
        return {
            'api_key': self.get('static_judge.api_key', self.api_key),
            'base_url': self.get('static_judge.base_url', self.url),
            'model': self.get('static_judge.model', self.model),
            'max_tokens': self.get('static_judge.max_tokens', 4096),
            'temperature': self.get('static_judge.temperature', 0.0),
        }
    
    @property
    def interactive_judge_config(self):
        """Get interactive score judge model configuration."""
        return {
            'api_key': self.get('interactive_judge.api_key', self.api_key),
            'base_url': self.get('interactive_judge.base_url', self.url),
            'model': self.get('interactive_judge.model', self.model),
            'max_tokens': self.get('interactive_judge.max_tokens', 4096),
            'temperature': self.get('interactive_judge.temperature', 0.0),
        }

    @property
    def design_judge_config(self):
        """Get Design Judge MVP configuration, falling back to root level settings."""
        return {
            'api_key': self.get('design_judge.api_key', self.api_key),
            'base_url': self.get('design_judge.base_url', self.url),
            'model': self.get('design_judge.model', self.model),
            'max_tokens': self.get('design_judge.max_tokens', 4096),
            'temperature': self.get('design_judge.temperature', 0.0),
            'max_workers': self.get('design_judge.max_workers', self.get('screenshot.max_workers', 4)),
            'render_timeout': self.get('design_judge.render_timeout', self.get('screenshot.timeout', 120)),
            'viewport_width': self.get('design_judge.viewport.width', 1280),
            'mobile_width': self.get('screenshot.mobile_width', 390),
        }


# Global config instance
config = Config()


if __name__ == "__main__":
    # Test config loading
    print("=" * 50)
    print("Configuration Test")
    print("=" * 50)
    print(f"MODEL: {config.model}")
    print(f"URL: {config.url}")
    print(f"API_KEY set: {bool(config.api_key)}")
    print(f"REPEAT_TIMES: {config.repeat_times}")
    print(f"DATA_SOURCE: {config.data_source}")
    print(f"model_to_evaluate: {config.model_to_evaluate}")
    print("-" * 50)
    print(f"benchmark.bench_name: {config.get('benchmark.bench_name')}")
    print(f"benchmark.data_file: {config.get('benchmark.data_file')}")
    print(f"benchmark.output_dir: {config.get('benchmark.output_dir')}")
    print(f"output_dir (property): {config.output_dir}")
    print("-" * 50)
    print(f"screenshot.max_workers: {config.get('screenshot.max_workers')}")
    print(f"screenshot.timeout: {config.get('screenshot.timeout')}")
    print(f"screenshot.batch_size: {config.get('screenshot.batch_size')}")
    print(f"screenshot.widths: {config.get('screenshot.widths')}")
    print(f"judge_widths: {config.get('judge_widths')}")
    print("-" * 50)
    print("openai_config:", config.openai_config)
    print("screenshot_config:", config.screenshot_config)
