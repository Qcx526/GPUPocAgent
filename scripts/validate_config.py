#!/usr/bin/env python
"""
Offline configuration validation test.
No API calls - just verify env vars and imports work.
"""

import sys
import os
from pathlib import Path

# Ensure proper encoding on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("OFFLINE CONFIGURATION VALIDATION TEST")
print("=" * 70)

# Test 1: Import config module
print("\n[1] Testing config module import...")
try:
    from src.config import get_config, checkpoint_db_path, artifact_index_path
    print("[OK] Config module imports successfully")
except Exception as e:
    print(f"[FAIL] Config import failed: {e}")
    sys.exit(1)

# Test 2: Load configuration
print("\n[2] Loading configuration from .env...")
try:
    config = get_config()
    print(f"✓ Configuration loaded")
    print(f"  - Project root: {config.project_root}")
    print(f"  - Workspace root: {config.workspace_root}")
    print(f"  - LLM Base URL: {config.llm_base_url}")
    print(f"  - LLM Model: {config.llm_model}")
    print(f"  - Has API Key: {bool(config.llm_api_key)}")
    print(f"  - Has Tavily Key: {bool(config.tavily_api_key)}")
except Exception as e:
    print(f"✗ Configuration loading failed: {e}")
    sys.exit(1)

# Test 3: Verify DeepSeek API endpoint
print("\n[3] Validating DeepSeek API endpoint...")
if config.llm_base_url == "https://api.deepseek.com":
    print("✓ DeepSeek official API endpoint configured correctly")
else:
    print(f"⚠ Unexpected base URL: {config.llm_base_url}")

# Test 4: Check workspace paths
print("\n[4] Verifying workspace directories...")
try:
    checkpoint_db = checkpoint_db_path()
    artifact_db = artifact_index_path()
    print(f"✓ Checkpoint DB path: {checkpoint_db}")
    print(f"✓ Artifact index path: {artifact_db}")

    # Verify directories exist
    checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
    artifact_db.parent.mkdir(parents=True, exist_ok=True)
    print("✓ Workspace directories created")
except Exception as e:
    print(f"✗ Workspace path error: {e}")
    sys.exit(1)

# Test 5: Import LangChain/DeepSeek client
print("\n[5] Testing LangChain imports...")
try:
    from langchain_openai import ChatOpenAI
    print("✓ LangChain OpenAI imports work")
    print("  (Ready to create DeepSeek client with OpenAI-compatible interface)")
except Exception as e:
    print(f"✗ LangChain import failed: {e}")
    sys.exit(1)

# Test 6: Test LLM client instantiation (no API call)
print("\n[6] Testing LLM client instantiation (no API call)...")
try:
    llm_client = ChatOpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
        temperature=0.3
    )
    print("✓ LLM client instantiated successfully")
    print(f"  - Client type: {type(llm_client).__name__}")
    print(f"  - Model: {llm_client.model_name}")
except Exception as e:
    print(f"✗ LLM client instantiation failed: {e}")
    sys.exit(1)

# Test 7: Verify .env security
print("\n[7] Verifying .env security settings...")
try:
    # Check that .env is in gitignore
    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        if ".env" in gitignore_content and "!.env.example" in gitignore_content:
            print("✓ .env is properly ignored by Git")
            print("✓ .env.example is whitelisted for tracking")
        else:
            print("⚠ .gitignore might not properly exclude .env")
    else:
        print("⚠ .gitignore file not found")
except Exception as e:
    print(f"⚠ Could not verify .gitignore: {e}")

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
print("\n✓ All offline checks passed")
print("Configuration is ready for API testing.")
print("\nNext step: Run a real API test with low budget")
print("(e.g., simple tool call to verify connectivity)")
