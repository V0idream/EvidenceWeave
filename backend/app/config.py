from pathlib import Path
from urllib.parse import urlparse
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    data_dir: Path = ROOT / 'data'
    database_url: str = ''
    ollama_base_url: str = 'http://127.0.0.1:11434'
    ollama_model: str = 'qwen3:14b'
    ollama_fallback_model: str = 'qwen3:8b'
    ollama_timeout: int = 240
    ollama_cache: bool = True
    ocr_provider: str = ''
    mineru_command: str = 'mineru'
    max_upload_mb: int = 100

    def model_post_init(self, __context):
        if urlparse(self.ollama_base_url).hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('Ollama 地址必须是本机回环地址，禁止发送案件到远程服务')
        if not self.data_dir.is_absolute():
            self.data_dir = ROOT / self.data_dir
        if self.database_url and not self.database_url.startswith('sqlite:///'):
            raise ValueError('V1 只支持本地 SQLite')
        if not self.database_url:
            self.database_url = 'sqlite:///' + (self.data_dir / 'evidenceweave.sqlite3').as_posix()

settings = Settings()
