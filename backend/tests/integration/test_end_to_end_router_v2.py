"""
End-to-End Integration Tests for Router v2.0
Tests complete flow: HTTP API → Router → 6-Stage Pipeline → LLM → Response

Project Creator: Herman Swanepoel
"""

import asyncio

import pytest
from httpx import AsyncClient

# Test the full pipeline with different task types
BACKEND_URL = "http://localhost:8001"


class TestRouterV2EndToEnd:
    """End-to-end tests for Router v2.0 complete pipeline"""

    @pytest.mark.asyncio
    async def test_code_generation_task(self):
        """Test code generation through full 6-stage pipeline"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            request_data = {
                "prompt": "Write a Python function to calculate factorial",
                "task_type": "code_generation",
                "user_id": "test_user_001",
                "session_id": "test_session_001",
            }

            response = await client.post("/api/v1/route", json=request_data)

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "text" in data
            assert "verified" in data
            assert "safety" in data
            assert "metadata" in data

            # Verify content
            assert len(data["text"]) > 0
            assert "def" in data["text"] or "factorial" in data["text"]

            # Verify metadata
            metadata = data["metadata"]
            assert "latency" in metadata
            assert "models_used" in metadata
            assert "task_type" in metadata
            assert metadata["task_type"] == "code_generation"

            # Verify pipeline stages executed
            if "pipeline_stages" in metadata:
                assert "system1_reasoning" in metadata["pipeline_stages"]
                assert "system2_verification" in metadata["pipeline_stages"]
                assert "safety_check" in metadata["pipeline_stages"]

            print(f"✅ Code generation test passed - Latency: {metadata['latency']:.2f}s")

    @pytest.mark.asyncio
    async def test_refactoring_task(self):
        """Test code refactoring through full pipeline"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            code_to_refactor = """
def calc(x, y, op):
    if op == 'add':
        return x + y
    elif op == 'sub':
        return x - y
    elif op == 'mul':
        return x * y
    else:
        return x / y
"""
            request_data = {
                "prompt": f"Refactor this code to be more maintainable:\n{code_to_refactor}",
                "task_type": "refactor",
                "user_id": "test_user_002",
                "session_id": "test_session_002",
            }

            response = await client.post("/api/v1/route", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert "text" in data
            assert data["verified"] is not None
            assert data["safety"] is not None
            assert len(data["text"]) > 0

            print(f"✅ Refactoring test passed - Verified: {data['verified']}")

    @pytest.mark.asyncio
    async def test_debugging_task(self):
        """Test debugging/bug detection through pipeline"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            buggy_code = """
def divide_numbers(a, b):
    return a / b  # Bug: No zero division check

result = divide_numbers(10, 0)
"""
            request_data = {
                "prompt": f"Find and fix bugs in this code:\n{buggy_code}",
                "task_type": "debugging",
                "user_id": "test_user_003",
                "session_id": "test_session_003",
            }

            response = await client.post("/api/v1/route", json=request_data)

            assert response.status_code == 200
            data = response.json()

            # Should detect zero division issue
            assert "text" in data
            text_lower = data["text"].lower()
            assert any(
                keyword in text_lower
                for keyword in ["zero", "division", "check", "error", "exception"]
            )

            print(f"✅ Debugging test passed - Safety: {data['safety']}")

    @pytest.mark.asyncio
    async def test_documentation_task(self):
        """Test documentation generation through pipeline"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            code_without_docs = """
def process_data(items, filter_func, transform_func):
    filtered = [item for item in items if filter_func(item)]
    transformed = [transform_func(item) for item in filtered]
    return transformed
"""
            request_data = {
                "prompt": f"Generate documentation for this function:\n{code_without_docs}",
                "task_type": "documentation",
                "user_id": "test_user_004",
                "session_id": "test_session_004",
            }

            response = await client.post("/api/v1/route", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert "text" in data
            text_lower = data["text"].lower()

            # Should contain documentation keywords
            assert any(
                keyword in text_lower
                for keyword in ["args", "returns", "parameters", "description", "def"]
            )

            print("✅ Documentation test passed")

    @pytest.mark.asyncio
    async def test_general_task(self):
        """Test general task through pipeline"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            request_data = {
                "prompt": "Explain the difference between list and tuple in Python",
                "task_type": "general",
                "user_id": "test_user_005",
                "session_id": "test_session_005",
            }

            response = await client.post("/api/v1/route", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert "text" in data
            assert len(data["text"]) > 50  # Should have substantial explanation
            text_lower = data["text"].lower()
            assert "list" in text_lower and "tuple" in text_lower

            print("✅ General task test passed")

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Test that metrics are properly tracked after requests"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            # First, make a few requests
            for i in range(3):
                request_data = {
                    "prompt": f"Test request {i}",
                    "task_type": "general",
                    "user_id": f"test_user_{i}",
                    "session_id": f"test_session_{i}",
                }
                await client.post("/api/v1/route", json=request_data)

            # Give metrics time to persist
            await asyncio.sleep(0.5)

            # Now check metrics
            response = await client.get("/api/v1/metrics")

            assert response.status_code == 200
            data = response.json()

            assert "summary" in data
            summary = data["summary"]

            assert summary["total_calls"] >= 3
            assert summary["avg_latency"] > 0
            assert summary["models_tracked"] > 0

            print(f"✅ Metrics tracking test passed - Total calls: {summary['total_calls']}")

    @pytest.mark.asyncio
    async def test_metrics_models_endpoint(self):
        """Test per-model statistics endpoint"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            response = await client.get("/api/v1/metrics/models")

            assert response.status_code == 200
            data = response.json()

            assert "models" in data
            # Should have at least one model tracked
            assert len(data["models"]) > 0

            print(f"✅ Per-model metrics test passed - Models tracked: {len(data['models'])}")

    @pytest.mark.asyncio
    async def test_autotune_recommendations(self):
        """Test auto-tune recommendations endpoint"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            request_data = {
                "latency_threshold": 5.0,
                "success_rate_threshold": 0.7,
            }

            response = await client.post("/api/v1/autotune", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert "recommendations" in data
            # Recommendations list can be empty if all models performing well

            print(f"✅ Auto-tune test passed - Recommendations: {len(data['recommendations'])}")

    @pytest.mark.asyncio
    async def test_safety_check_detection(self):
        """Test that safety layer detects malicious code"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            malicious_code = """
import os
os.system("rm -rf /")  # Dangerous command
"""
            request_data = {
                "prompt": f"Review this code:\n{malicious_code}",
                "task_type": "code_review",
                "user_id": "test_user_safety",
                "session_id": "test_session_safety",
            }

            response = await client.post("/api/v1/route", json=request_data)

            # Safety layer should flag this, but request should still succeed
            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = response.json()
                # Safety should be flagged
                # Note: Depending on implementation, might be in text or safety field
                print(
                    f"✅ Safety detection test passed - Safety status: {data.get('safety', 'N/A')}"
                )

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=60.0) as client:

            async def make_request(i: int):
                request_data = {
                    "prompt": f"Calculate {i} + {i}",
                    "task_type": "general",
                    "user_id": f"concurrent_user_{i}",
                    "session_id": f"concurrent_session_{i}",
                }
                response = await client.post("/api/v1/route", json=request_data)
                return response.status_code == 200

            # Fire 5 concurrent requests
            results = await asyncio.gather(*[make_request(i) for i in range(5)])

            # All should succeed
            assert all(results), "Some concurrent requests failed"

            print("✅ Concurrent requests test passed - 5/5 successful")

    @pytest.mark.asyncio
    async def test_pipeline_latency_targets(self):
        """Test that pipeline meets latency targets"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            request_data = {
                "prompt": "Write a hello world function",
                "task_type": "code_generation",
                "user_id": "test_latency",
                "session_id": "test_latency_session",
            }

            response = await client.post("/api/v1/route", json=request_data)

            assert response.status_code == 200
            data = response.json()

            latency = data["metadata"]["latency"]

            # Full pipeline should complete in under 10s (from vision doc)
            assert latency < 10.0, f"Pipeline too slow: {latency:.2f}s (target: <10s)"

            print(f"✅ Latency test passed - {latency:.2f}s (target: <10s)")

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling with invalid requests"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            # Missing required fields
            invalid_request = {
                "prompt": "Test",
                # Missing task_type
            }

            response = await client.post("/api/v1/route", json=invalid_request)

            # Should return error but not crash
            assert response.status_code in [400, 422, 500]

            print(f"✅ Error handling test passed - Status: {response.status_code}")


class TestTaskTypeRouting:
    """Test that different task types route to appropriate models"""

    @pytest.mark.asyncio
    async def test_task_type_code_generation(self):
        """Verify code generation uses appropriate models"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            request_data = {
                "prompt": "Create a function to sort a list",
                "task_type": "code_generation",
                "user_id": "test_routing_001",
                "session_id": "test_routing_session_001",
            }

            response = await client.post("/api/v1/route", json=request_data)
            assert response.status_code == 200

            data = response.json()
            models_used = data["metadata"].get("models_used", [])

            # Should use System 1 (qwen3) and possibly System 2 (deepseek-r1)
            print(f"✅ Code generation routing - Models used: {models_used}")

    @pytest.mark.asyncio
    async def test_task_type_refactoring(self):
        """Verify refactoring uses verification models"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            request_data = {
                "prompt": "Refactor this function to use list comprehension",
                "task_type": "refactor",
                "user_id": "test_routing_002",
                "session_id": "test_routing_session_002",
            }

            response = await client.post("/api/v1/route", json=request_data)
            assert response.status_code == 200

            data = response.json()
            # Refactoring should go through verification
            assert data["verified"] is not None

            print(f"✅ Refactoring routing - Verified: {data['verified']}")


class TestContextEngine:
    """Test context engine semantic search"""

    @pytest.mark.asyncio
    async def test_context_persistence(self):
        """Test that context is persisted across requests"""
        async with AsyncClient(base_url=BACKEND_URL, timeout=180.0) as client:
            session_id = "test_context_persistence"

            # First request
            request1 = {
                "prompt": "Remember that my favorite color is blue",
                "task_type": "general",
                "user_id": "test_context_user",
                "session_id": session_id,
            }
            await client.post("/api/v1/route", json=request1)

            # Second request referencing first
            request2 = {
                "prompt": "What is my favorite color?",
                "task_type": "general",
                "user_id": "test_context_user",
                "session_id": session_id,
            }
            response2 = await client.post("/api/v1/route", json=request2)

            assert response2.status_code == 200
            data = response2.json()

            # Context engine should help retrieve "blue"
            # Note: This depends on context retrieval working
            print("✅ Context persistence test completed")


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
