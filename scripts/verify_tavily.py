#!/usr/bin/env python
"""
Verify Tavily Search API integration
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings


def test_tavily_search():
    """Test real Tavily search API"""
    print("=" * 60)
    print("Tavily Search API Verification")
    print("=" * 60)

    # Check configuration
    print("\n1. Checking configuration...")
    settings = get_settings()

    if not settings.tavily_api_key:
        print("   ERROR: TAVILY_API_KEY not configured in .env")
        return 1

    print(f"   API key present: {settings.tavily_api_key[:10]}...")

    # Test search
    print("\n2. Testing search API...")
    try:
        import os
        # Set environment variable for Tavily
        os.environ["TAVILY_API_KEY"] = settings.tavily_api_key

        from langchain_community.tools.tavily_search import TavilySearchResults

        search_tool = TavilySearchResults(max_results=3)

        # Real search query
        query = "NVIDIA GPU CVE-2023 vulnerability"
        print(f"   Query: {query}")

        results = search_tool.invoke(query)

        print(f"\n3. Results received:")
        print(f"   Type: {type(results)}")
        print(f"   Count: {len(results) if isinstance(results, list) else 'N/A'}")

        if isinstance(results, list) and len(results) > 0:
            print(f"\n   Sample result:")
            sample = results[0]
            if isinstance(sample, dict):
                print(f"     URL: {sample.get('url', 'N/A')[:80]}")
                print(f"     Content: {sample.get('content', 'N/A')[:200]}...")
            else:
                print(f"     {str(sample)[:200]}...")

            print("\n" + "=" * 60)
            print("RESULT: Tavily Search API WORKING")
            print("=" * 60)
            return 0
        else:
            print("\n   WARNING: Empty results or unexpected format")
            print(f"   Results: {results}")
            return 1

    except Exception as e:
        print(f"\n   ERROR: Search failed: {e}")
        import traceback
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(test_tavily_search())
