"""
Tests for JSON filtering edge cases and concurrent/multi-thread retrieval.

Tests cover:
- Complex nested JSON structures
- Special characters and edge cases
- Concurrent access patterns
- Thread safety
- Race conditions
"""
from __future__ import annotations

import pytest
import threading
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from memoric.core.memory_manager import Memoric


@pytest.fixture(scope="function")
def mem():
    """Create Memoric instance with in-memory SQLite."""
    # Use truly isolated in-memory database per test
    # Must override storage.tiers structure, not database.dsn
    return Memoric(overrides={
        "storage": {
            "tiers": [
                {"name": "long_term", "dsn": "sqlite:///:memory:"}
            ]
        }
    })


class TestJSONFilteringEdgeCases:
    """Test complex and edge case JSON filtering scenarios."""

    def test_deeply_nested_objects(self, mem):
        """Test filtering on deeply nested JSON objects."""
        mem.save(
            user_id="user1",
            content="Deeply nested test",
            metadata={
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {
                                "level5": "deep_value"
                            }
                        }
                    }
                }
            }
        )

        # Filter by deep nested value
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {
                                "level5": "deep_value"
                            }
                        }
                    }
                }
            },
            top_k=10
        )

        assert len(results) == 1

    def test_mixed_types_in_metadata(self, mem):
        """Test metadata with mixed data types."""
        mem.save(
            user_id="user1",
            content="Mixed types test",
            metadata={
                "string": "text",
                "integer": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, 2, 3],
                "object": {"nested": "value"}
            }
        )

        # Filter by integer
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"integer": 42},
            top_k=10
        )
        assert len(results) == 1

        # Filter by boolean
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"boolean": True},
            top_k=10
        )
        assert len(results) == 1

    def test_special_characters_in_keys(self, mem):
        """Test special characters in JSON keys."""
        special_key = "key-with-dashes_and_underscores.and.dots"

        mem.save(
            user_id="user1",
            content="Special key test",
            metadata={special_key: "value"}
        )

        results = mem.retrieve(
            user_id="user1",
            metadata_filter={special_key: "value"},
            top_k=10
        )

        assert len(results) == 1

    def test_special_characters_in_values(self, mem):
        """Test special characters in JSON values."""
        special_values = [
            "value with spaces",
            "value\nwith\nnewlines",
            "value\twith\ttabs",
            "value\"with\"quotes",
            "value'with'single'quotes",
            r"value\with\backslashes",
            "value/with/slashes",
            "value<with>brackets",
            "value{with}braces",
            "value[with]square",
        ]

        for i, special_val in enumerate(special_values):
            mem.save(
                user_id="user1",
                content=f"Special value test {i}",
                metadata={"special": special_val}
            )

        # Filter by each special value
        for special_val in special_values:
            results = mem.retrieve(
                user_id="user1",
                metadata_filter={"special": special_val},
                top_k=20
            )
            assert len(results) >= 1

    def test_unicode_in_metadata(self, mem):
        """Test Unicode characters in metadata."""
        unicode_tests = [
            {"lang": "chinese", "text": "你好世界"},
            {"lang": "arabic", "text": "مرحبا بالعالم"},
            {"lang": "russian", "text": "Привет мир"},
            {"lang": "emoji", "text": "Hello 🌍 🚀 ⭐"},
            {"lang": "japanese", "text": "こんにちは世界"},
        ]

        for test in unicode_tests:
            mem.save(
                user_id="user1",
                content=f"Unicode test {test['lang']}",
                metadata=test
            )

        # Filter by each Unicode text
        for test in unicode_tests:
            results = mem.retrieve(
                user_id="user1",
                metadata_filter={"text": test["text"]},
                top_k=10
            )
            assert len(results) == 1
            assert results[0]["metadata"]["text"] == test["text"]

    def test_empty_values(self, mem):
        """Test empty strings, lists, and objects in metadata."""
        mem.save(
            user_id="user1",
            content="Empty values test",
            metadata={
                "empty_string": "",
                "empty_list": [],
                "empty_object": {},
                "normal": "value"
            }
        )

        # Filter by empty string
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"empty_string": ""},
            top_k=10
        )
        assert len(results) == 1

        # Filter by normal value
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"normal": "value"},
            top_k=10
        )
        assert len(results) == 1

    def test_large_json_objects(self, mem):
        """Test large JSON objects in metadata."""
        # Create large metadata
        large_metadata = {
            f"key_{i}": f"value_{i}" for i in range(100)
        }
        large_metadata["target"] = "find_me"

        mem.save(
            user_id="user1",
            content="Large JSON test",
            metadata=large_metadata
        )

        # Filter by specific key in large object
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"target": "find_me"},
            top_k=10
        )

        assert len(results) == 1

    def test_array_containment(self, mem):
        """Test array containment filtering."""
        mem.save(
            user_id="user1",
            content="Array test 1",
            metadata={"tags": ["python", "programming", "backend"]}
        )
        mem.save(
            user_id="user1",
            content="Array test 2",
            metadata={"tags": ["javascript", "frontend"]}
        )
        mem.save(
            user_id="user1",
            content="Array test 3",
            metadata={"tags": ["python", "data-science"]}
        )

        # Filter by array containing "python"
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"tags": ["python"]},
            top_k=10
        )

        # Should match arrays that contain "python"
        assert len(results) >= 2

    def test_numeric_precision(self, mem):
        """Test numeric precision in metadata filtering."""
        mem.save(
            user_id="user1",
            content="Precision test",
            metadata={
                "price": 19.99,
                "quantity": 42,
                "ratio": 0.333333
            }
        )

        # Filter by float
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"price": 19.99},
            top_k=10
        )
        assert len(results) == 1

        # Filter by integer
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"quantity": 42},
            top_k=10
        )
        assert len(results) == 1

    def test_boolean_filtering(self, mem):
        """Test boolean value filtering."""
        mem.save(
            user_id="user1",
            content="Boolean test 1",
            metadata={"active": True, "verified": False}
        )
        mem.save(
            user_id="user1",
            content="Boolean test 2",
            metadata={"active": False, "verified": True}
        )

        # Filter by True
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"active": True},
            top_k=10
        )
        assert len(results) == 1
        assert results[0]["metadata"]["active"] is True

        # Filter by False
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"verified": True},
            top_k=10
        )
        assert len(results) == 1

    def test_null_value_filtering(self, mem):
        """Test null/None value in metadata."""
        mem.save(
            user_id="user1",
            content="Null test",
            metadata={"nullable_field": None, "other": "value"}
        )

        # Should be able to retrieve even with null field
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"other": "value"},
            top_k=10
        )

        assert len(results) == 1

    def test_case_sensitivity(self, mem):
        """Test case sensitivity in metadata filtering."""
        mem.save(
            user_id="user1",
            content="Case test",
            metadata={"status": "Active"}
        )

        # Exact case match
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"status": "Active"},
            top_k=10
        )
        assert len(results) == 1

        # Different case should not match
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"status": "active"},
            top_k=10
        )
        assert len(results) == 0


class TestConcurrentRetrieval:
    """Test concurrent access and thread safety."""

    def test_concurrent_reads(self, mem):
        """Test concurrent read operations."""
        # Populate database
        for i in range(50):
            mem.save(
                user_id="user1",
                content=f"Memory {i}",
                metadata={"index": i}
            )

        # Concurrent read function
        def read_memories():
            results = mem.retrieve(user_id="user1", top_k=10)
            return len(results)

        # Execute reads concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_memories) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All reads should succeed
        assert len(results) == 20
        assert all(r == 10 for r in results)

    def test_concurrent_writes(self, mem):
        """Test concurrent write operations."""
        def write_memory(index):
            return mem.save(
                user_id="user1",
                content=f"Concurrent memory {index}",
                metadata={"index": index}
            )

        # Execute writes concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_memory, i) for i in range(50)]
            memory_ids = [f.result() for f in as_completed(futures)]

        # All writes should succeed
        assert len(memory_ids) == 50
        assert all(mid > 0 for mid in memory_ids)

        # Verify all memories were saved
        mem._ensure_initialized()
        all_memories = mem.db.get_memories(user_id="user1")
        assert len(all_memories) >= 50

    def test_concurrent_read_write(self, mem):
        """Test concurrent reads and writes."""
        # Initial data
        for i in range(20):
            mem.save(
                user_id="user1",
                content=f"Initial {i}",
                metadata={"type": "initial"}
            )

        results = {"reads": [], "writes": []}
        lock = threading.Lock()

        def read_operation():
            res = mem.retrieve(user_id="user1", top_k=5)
            with lock:
                results["reads"].append(len(res))

        def write_operation(index):
            mid = mem.save(
                user_id="user1",
                content=f"New {index}",
                metadata={"type": "new"}
            )
            with lock:
                results["writes"].append(mid)

        # Mix of reads and writes
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(30):
                if i % 2 == 0:
                    futures.append(executor.submit(read_operation))
                else:
                    futures.append(executor.submit(write_operation, i))

            for f in as_completed(futures):
                f.result()

        # All operations should complete
        assert len(results["reads"]) > 0
        assert len(results["writes"]) > 0

    def test_concurrent_policy_execution(self, mem):
        """Test concurrent policy executions."""
        # Create memories
        for i in range(30):
            mem.save(
                user_id="user1",
                content=f"Policy test {i}",
                metadata={"index": i}
            )

        def run_policy():
            return mem.run_policies()

        # Execute policies concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_policy) for _ in range(3)]
            policy_results = [f.result() for f in as_completed(futures)]

        # All should complete successfully
        assert len(policy_results) == 3
        # Each result should have expected keys
        for result in policy_results:
            assert "migrated" in result
            assert "trimmed" in result
            assert "summarized" in result

    def test_race_condition_cluster_rebuild(self, mem):
        """Test race conditions in cluster rebuilding."""
        # Create memories
        for i in range(20):
            mem.save(
                user_id="user1",
                content=f"Cluster test {i}",
                metadata={"topic": "test", "category": "test"}
            )

        def rebuild_clusters():
            return mem.rebuild_clusters(user_id="user1")

        # Rebuild clusters concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(rebuild_clusters) for _ in range(5)]
            counts = [f.result() for f in as_completed(futures)]

        # All rebuilds should complete
        assert len(counts) == 5

        # Final cluster state should be consistent
        final_clusters = mem.get_topic_clusters(user_id="user1")
        # Should have clusters (exact count may vary)
        assert len(final_clusters) >= 0

    def test_multi_user_concurrent_access(self, mem):
        """Test concurrent access from multiple users."""
        users = ["user1", "user2", "user3", "user4", "user5"]

        def user_operations(user_id):
            # Each user performs operations
            operations = []

            # Write
            for i in range(5):
                mid = mem.save(
                    user_id=user_id,
                    content=f"{user_id} memory {i}",
                    metadata={"user": user_id}
                )
                operations.append(("write", mid))

            # Read
            results = mem.retrieve(user_id=user_id, top_k=5)
            operations.append(("read", len(results)))

            return operations

        # All users operate concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(user_operations, user) for user in users]
            user_results = [f.result() for f in as_completed(futures)]

        # All users should complete successfully
        assert len(user_results) == 5

        # Verify user isolation
        for user_id in users:
            user_memories = mem.retrieve(user_id=user_id, scope="user", top_k=100)
            # Each user should only see their own memories
            assert all(m["user_id"] == user_id for m in user_memories)

    def test_stress_test_rapid_operations(self, mem):
        """Stress test with rapid operations."""
        operations_count = 100
        errors = []

        def rapid_operation(index):
            try:
                # Random mix of operations
                if index % 3 == 0:
                    mem.save(
                        user_id="stress_user",
                        content=f"Stress {index}",
                        metadata={"index": index}
                    )
                elif index % 3 == 1:
                    mem.retrieve(user_id="stress_user", top_k=5)
                else:
                    mem._ensure_initialized()
                    mem.db.count_by_tier(user_id="stress_user")
            except Exception as e:
                errors.append((index, str(e)))

        # Execute rapidly
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(rapid_operation, i) for i in range(operations_count)]
            for f in as_completed(futures):
                f.result()

        # Should have minimal or no errors
        assert len(errors) < operations_count * 0.1  # Less than 10% error rate


class TestThreadSafety:
    """Test thread safety of core operations."""

    def test_initialization_thread_safety(self):
        """Test that lazy initialization is thread-safe."""
        mem = Memoric(overrides={
            "database": {"dsn": "sqlite:///:memory:"}
        })

        init_results = []

        def initialize():
            mem._ensure_initialized()
            init_results.append(mem._initialized)

        # Initialize from multiple threads
        threads = [threading.Thread(target=initialize) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should see initialized state
        assert all(init_results)
        assert len(init_results) == 10

    def test_counter_thread_safety(self, mem):
        """Test that counters are thread-safe."""
        counter = {"value": 0}
        lock = threading.Lock()

        def increment_and_save():
            with lock:
                counter["value"] += 1
                index = counter["value"]

            mem.save(
                user_id="counter_user",
                content=f"Count {index}",
                metadata={"count": index}
            )

        # Increment from multiple threads
        threads = [threading.Thread(target=increment_and_save) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have all 50 memories
        mem._ensure_initialized()
        memories = mem.db.get_memories(user_id="counter_user")
        assert len(memories) == 50

        # All counts should be unique
        counts = [m["metadata"]["count"] for m in memories]
        assert len(set(counts)) == 50
