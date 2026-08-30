from app.analyzers.file_classifier import classify_file

def test_file_classification():
    # 1. Documentation
    assert classify_file("README.md") == "documentation"
    assert classify_file("LICENSE") == "documentation"
    assert classify_file("docs/changelog.txt") == "documentation"
    
    # 2. Configuration
    assert classify_file("package.json") == "configuration"
    assert classify_file(".gitignore") == "configuration"
    assert classify_file("requirements.txt") == "configuration"
    assert classify_file("config.yaml") == "configuration"
    assert classify_file("Dockerfile") == "configuration"
    
    # 3. Assets
    assert classify_file("images/logo.png") == "asset"
    assert classify_file("fonts/inter.woff2") == "asset"
    assert classify_file("assets/video.mp4") == "asset"
    assert classify_file("archive.zip") == "asset"
    
    # 4. Test Files (directories or filename match)
    assert classify_file("tests/test_main.py") == "test"
    assert classify_file("test/test_app.js") == "test"
    assert classify_file("src/__tests__/App.tsx") == "test"
    assert classify_file("src/components/button.test.ts") == "test"
    assert classify_file("src/components/button.spec.tsx") == "test"
    
    # 5. Source code (recognized but not configurations/tests/docs/assets)
    assert classify_file("src/main.py") == "source"
    assert classify_file("app/index.js") == "source"
    assert classify_file("components/Header.tsx") == "source"
    assert classify_file("styles/main.css") == "source"
    
    # 6. Unknown
    assert classify_file("random.bin") == "asset" # Classified under ASSET binary extensions
    assert classify_file("unknown_format.xyz") == "unknown"
