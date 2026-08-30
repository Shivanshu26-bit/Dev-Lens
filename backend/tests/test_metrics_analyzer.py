from app.analyzers.metrics_analyzer import calculate_metrics

def test_metrics_empty():
    assert calculate_metrics("", "Python") == (0, 0, 0, 0)
    assert calculate_metrics(None, "Python") == (0, 0, 0, 0)

def test_metrics_python():
    content = """# Python file
def greet():
    # Comment inside greet
    print("Hello")

\"\"\"
Multi-line docstring
spanning two lines.
\"\"\"
"""
    # Total: 10, Blanks: 1 (after print), Comments: 5 (# Python file, # Comment, docstrings), Code: 4
    total, blank, comment, code = calculate_metrics(content, "Python")
    assert total == 9
    assert blank == 1
    assert comment == 6
    assert code == 2

def test_metrics_c_style():
    content = """/* C-style file
   Multi-line block comment */
const x = 10; // Inline comment

// Another comment

function test() {
}
"""
    # Total: 9, Blanks: 2, Comments: 4 (/* */, //, //), Code: 3 (const, function, })
    total, blank, comment, code = calculate_metrics(content, "TypeScript")
    assert total == 8
    assert blank == 2
    assert comment == 3
    assert code == 3
