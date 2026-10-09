import os
import json
import subprocess
import sys

def secure_environment():
    """Scrub sensitive environment variables before running untrusted participant code"""
    sensitive_keys = [
        "GROQ_API_KEY", "TTS_API_KEY", "SUPABASE_URL", "SUPABASE_KEY",
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", 
        "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"
    ]
    for key in sensitive_keys:
        if key in os.environ:
            del os.environ[key]
    
    # Set a flag that we are in evaluation mode
    os.environ["MOCK_EVALUATION_MODE"] = "true"

def run_tests():
    """Run pytest with JSON reporting"""
    # The tests/conftest.py will automatically inject mocks and block network access
    report_file = "evaluation_report.json"
    
    print("Running mock integration tests...\n")
    # Run pytest on the tests directory
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--json-report", f"--json-report-file={report_file}", "-q"],
        capture_output=True,
        text=True
    )
    
    # We do not check result.returncode here because some tests might legitimately fail for participants
    return report_file

def generate_evaluation_summary(report_file):
    """Parse the JSON report and score the participant"""
    if not os.path.exists(report_file):
        print(f"Error: {report_file} not found. Tests may have failed to execute entirely.")
        return
        
    with open(report_file, 'r') as f:
        data = json.load(f)
        
    summary = data.get('summary', {})
    total = summary.get('total', 0)
    passed = summary.get('passed', 0)
    failed = summary.get('failed', 0)
    errors = summary.get('error', 0)
    
    print("="*40)
    print("      PARTICIPANT EVALUATION REPORT")
    print("="*40)
    
    # List all tests and their status
    tests = data.get('tests', [])
    for test in tests:
        node_id = test.get('nodeid')
        outcome = test.get('outcome')
        
        icon = "[PASS]" if outcome == "passed" else "[FAIL]"
        print(f"{icon} {node_id}")
        
        if outcome != "passed":
            # Print failure details
            call = test.get('call', {})
            crash = call.get('crash', {})
            msg = crash.get('message', 'Unknown Error')
            print(f"   -> FAILED: {msg.splitlines()[0]}")
            
    print("-" * 40)
    print(f"Total Tests Run: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    print("-" * 40)
    
    if total > 0:
        score = (passed / total) * 100
        print(f"FINAL SCORE: {score:.1f}%")
        if score == 100:
            print("\n[+] Excellent! All mock integration tests passed.")
        else:
            print("\n[-] Keep working! Some tests are failing.")
    else:
        print("FINAL SCORE: 0.0%")
        print("No tests were found or executed.")

if __name__ == "__main__":
    secure_environment()
    report = run_tests()
    generate_evaluation_summary(report)
