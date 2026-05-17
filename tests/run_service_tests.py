#!/usr/bin/env python
"""Run all service tests.

This script runs all the tests for the service layer to verify functionality.
"""

import os
import sys

# Ensure package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_tests():
    """Run all service tests."""
    failures = []

    print("=" * 70)
    print("Running Service Layer Tests")
    print("=" * 70)

    # Test SupernovaFilterService
    print("\n[1/2] Testing SupernovaFilterService...")
    try:
        import tests.test_supernova_filter_service as filter_tests

        # Run all test functions
        for name in dir(filter_tests):
            if name.startswith("test_"):
                func = getattr(filter_tests, name)
                try:
                    func()
                    print(f"  ✓ {name}")
                except AssertionError as e:
                    print(f"  ✗ {name}: {e}")
                    failures.append(f"test_supernova_filter_service.{name}")
                except Exception as e:
                    print(f"  ✗ {name}: {type(e).__name__}: {e}")
                    failures.append(f"test_supernova_filter_service.{name}")
    except Exception as e:
        print(f"  ✗ Failed to load filter service tests: {e}")
        failures.append("test_supernova_filter_service (module load)")

    # Test SupernovaSelectionService
    print("\n[2/2] Testing SupernovaSelectionService...")
    try:
        import tests.test_supernova_selection_service as selection_tests

        for name in dir(selection_tests):
            if name.startswith("test_"):
                func = getattr(selection_tests, name)
                try:
                    func()
                    print(f"  ✓ {name}")
                except AssertionError as e:
                    print(f"  ✗ {name}: {e}")
                    failures.append(f"test_supernova_selection_service.{name}")
                except Exception as e:
                    print(f"  ✗ {name}: {type(e).__name__}: {e}")
                    failures.append(f"test_supernova_selection_service.{name}")
    except Exception as e:
        print(f"  ✗ Failed to load selection service tests: {e}")
        failures.append("test_supernova_selection_service (module load)")

    # Summary
    print("\n" + "=" * 70)
    if not failures:
        print("✓ All tests passed!")
        print("=" * 70)
        return 0
    else:
        print(f"✗ {len(failures)} test(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
