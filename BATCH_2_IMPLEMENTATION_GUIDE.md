# 🚀 PHASE 3 BATCH 2 - IMPLEMENTATION GUIDE

**Project Creator:** Herman Swanepoel  
**Date:** 2025-10-13  
**Status:** READY FOR EXECUTION  
**Services:** Context Manager, Embeddings Service, Memory Service

---

## 🎯 BATCH 2 OVERVIEW

### Services to Test: 3
### Estimated Tests: 70
### Target Coverage: 85%+
### Estimated Time: 2-3 hours

---

## 📋 SERVICE 1: CONTEXT MANAGER

**File:** `backend/src/services/context_manager.py`  
**Tests:** 25  
**Priority:** HIGH  
**Coverage Target:** 85%+

### Test Categories:
1. **Initialization** (3 tests)
   - Default initialization
   - Custom configuration
   - Dependency injection

2. **Context Creation** (5 tests)
   - Create basic context
   - Create with file path
   - Create with cursor position
   - Create with selected text
   - Create with workspace path

3. **Context Enrichment** (8 tests)
   - Enrich with Git information
   - Enrich with imports
   - Enrich with dependencies
   - Enrich with surrounding code
   - Enrich with recent commits
   - Handle missing files
   - Handle Git errors
   - Handle parse errors

4. **Context Caching** (4 tests)
   - Cache context
   - Retrieve cached context
   - Invalidate cache
   - Cache expiration

5. **Error Handling** (3 tests)
   - Handle file not found
   - Handle permission errors
   - Handle invalid paths

6. **Integration** (2 tests)
   - Integration with Git
   - Integration with file system

### Key Test Scenarios:
```python
# Test file structure
class TestContextManagerInitialization:
    def test_initialization_with_defaults()
    def test_initialization_with_custom_config()
    def test_initialization_with_dependencies()

@pytest.mark.asyncio
class TestContextCreation:
    async def test_create_basic_context()
    async def test_create_context_with_file()
    async def test_create_context_with_cursor()
    async def test_create_context_with_selection()
    async def test_create_context_with_workspace()

@pytest.mark.asyncio
class TestContextEnrichment:
    async def test_enrich_with_git_info()
    async def test_enrich_with_imports()
    async def test_enrich_with_dependencies()
    async def test_enrich_with_surrounding_code()
    async def test_enrich_with_commits()
    async def test_handle_missing_files()
    async def test_handle_git_errors()
    async def test_handle_parse_errors()

@pytest.mark.asyncio
class TestContextCaching:
    async def test_cache_context()
    async def test_retrieve_cached_context()
    async def test_invalidate_cache()
    async def test_cache_expiration()

class TestContextManagerErrorHandling:
    async def test_file_not_found()
    async def test_permission_errors()
    async def test_invalid_paths()
```

---

## 📋 SERVICE 2: EMBEDDINGS SERVICE

**File:** `backend/src/services/embeddings_service.py`  
**Tests:** 20  
**Priority:** HIGH  
**Coverage Target:** 85%+

### Test Categories:
1. **Initialization** (3 tests)
   - Default model
   - Custom model
   - Model loading

2. **Embedding Generation** (6 tests)
   - Generate single embedding
   - Generate batch embeddings
   - Generate with different models
   - Handle empty input
   - Handle long text
   - Handle special characters

3. **Caching** (4 tests)
   - Cache embeddings
   - Retrieve cached embeddings
   - Cache invalidation
   - Cache statistics

4. **Model Management** (3 tests)
   - Load model
   - Switch models
   - Model information

5. **Error Handling** (2 tests)
   - Handle model errors
   - Handle generation errors

6. **Performance** (2 tests)
   - Batch processing performance
   - Single vs batch comparison

### Key Test Scenarios:
```python
class TestEmbeddingsServiceInitialization:
    def test_initialization_with_default_model()
    def test_initialization_with_custom_model()
    def test_model_loading()

@pytest.mark.asyncio
class TestEmbeddingGeneration:
    async def test_generate_single_embedding()
    async def test_generate_batch_embeddings()
    async def test_generate_with_different_models()
    async def test_handle_empty_input()
    async def test_handle_long_text()
    async def test_handle_special_characters()

@pytest.mark.asyncio
class TestEmbeddingsCaching:
    async def test_cache_embeddings()
    async def test_retrieve_cached_embeddings()
    async def test_cache_invalidation()
    async def test_cache_statistics()

class TestModelManagement:
    def test_load_model()
    def test_switch_models()
    def test_model_information()

@pytest.mark.asyncio
class TestEmbeddingsErrorHandling:
    async def test_handle_model_errors()
    async def test_handle_generation_errors()

@pytest.mark.asyncio
class TestEmbeddingsPerformance:
    async def test_batch_processing_performance()
    async def test_single_vs_batch_comparison()
```

---

## 📋 SERVICE 3: MEMORY SERVICE

**File:** `backend/src/services/memory_service.py`  
**Tests:** 25  
**Priority:** HIGH  
**Coverage Target:** 85%+

### Test Categories:
1. **Initialization** (3 tests)
   - Default initialization
   - Custom configuration
   - Vector DB connection

2. **Memory Storage** (6 tests)
   - Store single memory
   - Store batch memories
   - Store with metadata
   - Update existing memory
   - Delete memory
   - Clear all memories

3. **Memory Retrieval** (6 tests)
   - Retrieve by ID
   - Retrieve by query
   - Semantic search
   - Filter by metadata
   - Pagination
   - Sort results

4. **Vector Operations** (4 tests)
   - Generate vectors
   - Similarity search
   - Distance calculation
   - Clustering

5. **Memory Lifecycle** (3 tests)
   - Memory expiration
   - Memory archiving
   - Memory cleanup

6. **Error Handling** (3 tests)
   - Handle storage errors
   - Handle retrieval errors
   - Handle vector DB errors

### Key Test Scenarios:
```python
class TestMemoryServiceInitialization:
    def test_initialization_with_defaults()
    def test_initialization_with_custom_config()
    def test_vector_db_connection()

@pytest.mark.asyncio
class TestMemoryStorage:
    async def test_store_single_memory()
    async def test_store_batch_memories()
    async def test_store_with_metadata()
    async def test_update_existing_memory()
    async def test_delete_memory()
    async def test_clear_all_memories()

@pytest.mark.asyncio
class TestMemoryRetrieval:
    async def test_retrieve_by_id()
    async def test_retrieve_by_query()
    async def test_semantic_search()
    async def test_filter_by_metadata()
    async def test_pagination()
    async def test_sort_results()

@pytest.mark.asyncio
class TestVectorOperations:
    async def test_generate_vectors()
    async def test_similarity_search()
    async def test_distance_calculation()
    async def test_clustering()

@pytest.mark.asyncio
class TestMemoryLifecycle:
    async def test_memory_expiration()
    async def test_memory_archiving()
    async def test_memory_cleanup()

@pytest.mark.asyncio
class TestMemoryServiceErrorHandling:
    async def test_handle_storage_errors()
    async def test_handle_retrieval_errors()
    async def test_handle_vector_db_errors()
```

---

## 🎯 IMPLEMENTATION STRATEGY

### Step 1: Read Source Files
```python
# Read all three service files
context_manager = read_file("backend/src/services/context_manager.py")
embeddings_service = read_file("backend/src/services/embeddings_service.py")
memory_service = read_file("backend/src/services/memory_service.py")
```

### Step 2: Create Test File
```python
# Create comprehensive test file
create_file("backend/tests/unit/test_services_batch2.py")
```

### Step 3: Implement Tests
- Write initialization tests
- Write core functionality tests
- Write integration tests
- Write error handling tests
- Write performance tests

### Step 4: Run and Verify
```bash
pytest tests/unit/test_services_batch2.py -v --cov
```

### Step 5: Validate Coverage
- Ensure 85%+ coverage per service
- Verify all tests passing
- Check execution time

---

## 🛠️ COMMON FIXTURES NEEDED

```python
@pytest.fixture
def mock_git_repo():
    """Mock Git repository"""
    repo = Mock()
    repo.head.commit.hexsha = "abc123"
    repo.active_branch.name = "main"
    return repo

@pytest.fixture
def mock_vector_db():
    """Mock vector database"""
    db = AsyncMock()
    db.add = AsyncMock(return_value=True)
    db.search = AsyncMock(return_value=[])
    return db

@pytest.fixture
def mock_embedding_model():
    """Mock embedding model"""
    model = Mock()
    model.encode = Mock(return_value=[[0.1, 0.2, 0.3]])
    return model

@pytest.fixture
def sample_code_file():
    """Sample code file content"""
    return '''
def hello_world():
    """Say hello"""
    print("Hello, World!")
'''

@pytest.fixture
def sample_memory():
    """Sample memory object"""
    return {
        "id": "mem-123",
        "content": "Test memory",
        "metadata": {"type": "code"},
        "vector": [0.1, 0.2, 0.3]
    }
```

---

## 📊 SUCCESS CRITERIA

### Per Service:
- ✅ 85%+ code coverage
- ✅ All tests passing
- ✅ No breaking changes
- ✅ Fast execution (<5s)
- ✅ Comprehensive scenarios
- ✅ Error handling tested

### Overall Batch 2:
- ✅ 70+ tests created
- ✅ 3 services tested
- ✅ 85%+ average coverage
- ✅ Zero breaking changes
- ✅ All tests passing
- ✅ Documentation updated

---

## 🚀 EXECUTION COMMAND

```bash
# Run Batch 2 tests
cd backend
python -m pytest tests/unit/test_services_batch2.py -v --cov=src/services --cov-report=html

# Check coverage
open htmlcov/index.html
```

---

## 📝 NEXT STEPS AFTER BATCH 2

### Batch 3 - Medium Priority Services
1. Code Smell Detector (20 tests)
2. Telemetry Service (15 tests)
3. Self-Healing Manager (20 tests)
4. Semantic Search (20 tests)

### Batch 4 - Low Priority Services
5. Predictive Cache Manager (15 tests)
6. Mode Manager (10 tests)
7. Cloud Providers (10 tests)
8. Prompt Templates (10 tests)

---

**Project Creator:** Herman Swanepoel  
**AURA-DEV OMNIDEVGOD MODE**  
**Status:** 🔥 BATCH 2 READY FOR EXECUTION 🔥  
**Date:** 2025-10-13
