from app.analyzers.code_quality_analyzer import scan_quality

def test_scan_quality_todo():
    content = """# TODO: implement scanner logic
const x = 10; // FIXME: check this
"""
    findings = scan_quality(content, "src/main.ts", "TypeScript")
    assert len(findings) == 2
    assert any(f["title"] == "Unresolved TODO Comment" for f in findings)
    assert any(f["title"] == "Unresolved FIXME Comment" for f in findings)

def test_scan_quality_line_length():
    # A single line with 130 characters
    long_line = "a" * 130
    findings = scan_quality(long_line, "index.js", "JavaScript")
    assert len(findings) == 1
    assert findings[0]["title"] == "Line Too Long"
    assert findings[0]["severity"] == "low"

def test_scan_quality_python_broad_except_and_print():
    content = """
try:
    x = 1/0
except Exception:
    print("Error occurred!")
"""
    findings = scan_quality(content, "app.py", "Python")
    # Matches: broad except, print statement
    assert len(findings) == 2
    assert any(f["title"] == "Broad Exception Clause" for f in findings)
    assert any(f["title"] == "Debug Print Statement" for f in findings)

def test_scan_quality_js_console_log():
    content = """
function calculate() {
    console.log("Starting calculation...");
    return 42;
}
"""
    findings = scan_quality(content, "calc.js", "JavaScript")
    assert len(findings) == 1
    assert findings[0]["title"] == "Console Debug Logger"
    assert findings[0]["severity"] == "low"
