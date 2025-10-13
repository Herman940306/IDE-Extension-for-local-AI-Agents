"""
Unit tests for Parallel File Creator
Project Creator: Herman Swanepoel
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from src.utils.parallel_file_creator import ParallelFileCreator, create_files_parallel


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def creator(temp_dir):
    """Create ParallelFileCreator instance"""
    return ParallelFileCreator(
        base_dir=temp_dir,
        max_workers=4
    )


@pytest.mark.asyncio
async def test_create_single_file(creator, temp_dir):
    """Test creating a single file"""
    result = await creator.create_file("test.txt", "Hello World")
    
    assert result is not None
    assert result.exists()
    assert result.read_text() == "Hello World"


@pytest.mark.asyncio
async def test_create_multiple_files_parallel(creator, temp_dir):
    """Test creating multiple files in parallel"""
    file_tasks = [
        {"name": f"file_{i}.txt", "content": f"Content {i}"}
        for i in range(10)
    ]
    
    results = await creator.create_files_parallel(file_tasks)
    
    # Check all files created
    assert len(results) == 10
    assert all(r is not None for r in results)
    
    # Verify content
    for i in range(10):
        file_path = temp_dir / f"file_{i}.txt"
        assert file_path.exists()
        assert file_path.read_text() == f"Content {i}"


@pytest.mark.asyncio
async def test_statistics_tracking(creator):
    """Test that statistics are tracked correctly"""
    file_tasks = [
        {"name": f"file_{i}.txt", "content": f"Content {i}"}
        for i in range(5)
    ]
    
    await creator.create_files_parallel(file_tasks)
    stats = creator.get_stats()
    
    assert stats["total_files_created"] == 5
    assert stats["total_errors"] == 0


@pytest.mark.asyncio
async def test_error_handling(creator, temp_dir):
    """Test error handling for invalid operations"""
    # Try to create file in non-existent subdirectory
    result = await creator.create_file("subdir/test.txt", "Content")
    
    # Should handle gracefully
    assert result is None or result.exists()


@pytest.mark.asyncio
async def test_convenience_function(temp_dir):
    """Test convenience function"""
    file_tasks = [
        {"name": f"file_{i}.txt", "content": f"Content {i}"}
        for i in range(5)
    ]
    
    results = await create_files_parallel(
        file_tasks,
        base_dir=temp_dir,
        max_workers=4
    )
    
    assert len(results) == 5
    assert all(r is not None for r in results)


@pytest.mark.asyncio
async def test_concurrent_execution(creator):
    """Test that files are created concurrently"""
    import time
    
    file_tasks = [
        {"name": f"file_{i}.txt", "content": f"Content {i}" * 100}
        for i in range(20)
    ]
    
    start = time.time()
    results = await creator.create_files_parallel(file_tasks)
    elapsed = time.time() - start
    
    # Should be faster than sequential (rough estimate)
    assert len(results) == 20
    assert elapsed < 5.0  # Should complete quickly with parallelism


@pytest.mark.asyncio
async def test_godmode_reporting(creator, caplog):
    """Test GODMODE batch reporting"""
    file_tasks = [
        {"name": f"file_{i}.txt", "content": f"Content {i}"}
        for i in range(10)
    ]
    
    await creator.create_files_parallel(file_tasks)
    
    # Check that GODMODE report was logged
    assert "GODMODE Parallel File Creation Summary" in caplog.text
    assert "Success:" in caplog.text
    assert "Throughput:" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
