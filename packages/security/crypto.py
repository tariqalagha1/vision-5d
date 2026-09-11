"""Vision 5D — Security Module"""
import os, hashlib, hmac, secrets, structlog, base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Optional
from uuid import UUID

logger = structlog.get_logger()

# Secret scanning patterns
SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', 'openai_key'),
    (r'sk-ant-[a-zA-Z0-9]{20,}', 'anthropic_key'),
    (r'Bearer\s+[A-Za-z0-9+/=]{20,}', 'bearer_token'),
    (r'api_key[:=]\s*[^\s]{20,}', 'api_key_assignment'),
    (r'("api_key"\s*:\s*"[^"]{20,}")', 'json_api_key'),
]

class SecretEncryption:
    """Tenant-scoped credential encryption using AES-256-GCM."""
    
    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or Fernet.generate_key()
        self._fernet = Fernet(self.master_key)
    
    def derive_tenant_key(self, tenant_id: UUID) -> bytes:
        """Derive a tenant-specific encryption key."""
        return hashlib.sha256(
            self.master_key + str(tenant_id).encode()
        ).digest()
    
    def encrypt(self, tenant_id: UUID, plaintext: str) -> tuple[bytes, str]:
        """Encrypt credential with tenant-specific key. Returns (ciphertext, key_id)."""
        key = self.derive_tenant_key(tenant_id)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return (nonce + ct, hashlib.sha256(key).hexdigest()[:16])
    
    def decrypt(self, tenant_id: UUID, ciphertext: bytes) -> str:
        """Decrypt credential. Caller MUST zero plaintext after use."""
        key = self.derive_tenant_key(tenant_id)
        aesgcm = AESGCM(key)
        nonce, ct = ciphertext[:12], ciphertext[12:]
        return aesgcm.decrypt(nonce, ct, None).decode()

def _load_or_create_master_key() -> bytes:
    """Return a stable master key that survives process restarts.

    Priority:
      1. ``V5D_ENCRYPTION_KEY`` env var — deterministically derived into a Fernet key.
      2. Persisted key file (``V5D_ENCRYPTION_KEY_FILE``, default
         ``<project_root>/.storage/encryption.key``).
      3. Generate a fresh key and persist it for future starts.

    Without this, a new random key was generated on every import, making
    stored provider credentials undecryptable after a restart.
    """
    # 1. Explicit env var — derive a valid Fernet key deterministically.
    env_key = os.getenv("V5D_ENCRYPTION_KEY", "").strip()
    if env_key:
        derived = hashlib.sha256(env_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(derived)

    # 2. Persisted key file (project_root/.storage/encryption.key).
    key_path = os.getenv(
        "V5D_ENCRYPTION_KEY_FILE",
        os.path.join(os.path.dirname(__file__), "..", "..", ".storage", "encryption.key"),
    )
    key_path = os.path.abspath(key_path)
    try:
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                existing = f.read().strip()
            if existing:
                return existing
    except OSError:
        logger.warning("encryption_key_read_failed", path=key_path)

    # 3. Generate + persist so the key is stable across restarts.
    key = Fernet.generate_key()
    try:
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        logger.info("encryption_key_created", path=key_path)
    except OSError as e:
        logger.warning("encryption_key_persist_failed", path=key_path, error=str(e))
    return key


# Global encryption instance — initialized at startup with a stable key.
secret_encryption = SecretEncryption(master_key=_load_or_create_master_key())

def scan_for_secrets(data: str) -> list[str]:
    """Scan data for known secret patterns. Returns list of matched pattern names."""
    import re
    found = []
    for pattern, name in SECRET_PATTERNS:
        if re.search(pattern, data, re.IGNORECASE):
            found.append(name)
    return found

def sanitize_for_log(data: str) -> str:
    """Remove detected secrets from a string."""
    import re
    for pattern, _ in SECRET_PATTERNS:
        data = re.sub(pattern, '[REDACTED]', data, flags=re.IGNORECASE)
    return data
