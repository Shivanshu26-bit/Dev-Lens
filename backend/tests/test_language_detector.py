from app.analyzers.language_detector import detect_language

def test_language_detection():
    # Supported languages
    assert detect_language("main.py") == "Python"
    assert detect_language("app.js") == "JavaScript"
    assert detect_language("types.ts") == "TypeScript"
    assert detect_language("component.jsx") == "React JSX"
    assert detect_language("Dashboard.tsx") == "React TSX"
    assert detect_language("Service.java") == "Java"
    assert detect_language("main.c") == "C"
    assert detect_language("vector.cpp") == "C++"
    assert detect_language("vector.cc") == "C++"
    assert detect_language("vector.cxx") == "C++"
    assert detect_language("vector.hpp") == "C++"
    assert detect_language("Program.cs") == "C#"
    assert detect_language("main.go") == "Go"
    assert detect_language("lib.rs") == "Rust"
    assert detect_language("index.php") == "PHP"
    assert detect_language("main.rb") == "Ruby"
    assert detect_language("index.html") == "HTML"
    assert detect_language("index.htm") == "HTML"
    assert detect_language("styles.css") == "CSS"
    assert detect_language("styles.scss") == "SCSS"
    assert detect_language("config.json") == "JSON"
    assert detect_language("docker-compose.yml") == "YAML"
    assert detect_language("docker-compose.yaml") == "YAML"
    assert detect_language("README.md") == "Markdown"
    assert detect_language("schema.sql") == "SQL"
    assert detect_language("run.sh") == "Shell"
    
    # Case insensitivity checks
    assert detect_language("MAIN.PY") == "Python"
    assert detect_language("styles.CSS") == "CSS"
    
    # Unknown extensions
    assert detect_language("logo.png") == "Unknown"
    assert detect_language("Dockerfile") == "Unknown"
    assert detect_language("no-extension") == "Unknown"
