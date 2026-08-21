import ast
import os
import sys
from pathlib import Path

root = Path("C:/Users/Keith/x402-mcp")
tests_dir = root / "tests"

test_files = list(tests_dir.glob("test_*.py"))
print(f"Total test files found: {len(test_files)}")

total_test_functions = 0
total_assertions = 0
skipped_tests = []
suspicious_tests = []

for tf in test_files:
    try:
        tree = ast.parse(tf.read_text(encoding="utf-8"), filename=str(tf))
    except Exception as e:
        print(f"Error parsing {tf.name}: {e}")
        continue

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            total_test_functions += 1
            # Count asserts in this function
            func_asserts = [n for n in ast.walk(node) if isinstance(n, ast.Assert)]
            total_assertions += len(func_asserts)
            
            # Check decorators for skip/xfail
            for dec in node.decorator_list:
                dec_str = ast.dump(dec)
                if "skip" in dec_str or "xfail" in dec_str:
                    skipped_tests.append(f"{tf.name}::{node.name}")
            
            # Check body
            body = [n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
            if not body or (len(body) == 1 and isinstance(body[0], ast.Pass)):
                suspicious_tests.append(f"{tf.name}::{node.name} (EMPTY/PASS BODY)")
            elif len(func_asserts) == 0:
                # Some tests use pytest.raises with with-statement
                with_stmts = [n for n in ast.walk(node) if isinstance(n, ast.With)]
                has_pytest_raises = any("raises" in ast.dump(w) for w in with_stmts)
                if not has_pytest_raises:
                    # Could be helper or run without assert
                    suspicious_tests.append(f"{tf.name}::{node.name} (NO ASSERTS OR RAISES)")

print(f"\n--- Forensic Test Integrity Summary ---")
print(f"Total test functions: {total_test_functions}")
print(f"Total assert statements: {total_assertions}")
print(f"Skipped / xfailed tests: {len(skipped_tests)} ({skipped_tests})")
print(f"Suspicious tests: {len(suspicious_tests)} ({suspicious_tests[:10]})")
