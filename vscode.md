{
    "python.analysis.typeCheckingMode": "strict",
    "editor.defaultFormatter": "ms-python.black-formatter",
    "black-formatter.path": [
        "/opt/homebrew/bin/black"
    ],
    "flake8.path": [
        "/opt/homebrew/bin/flake8"
    ],
    "editor.formatOnSave": true,
    "flake8.args": ["--ignore=E24,W504", "--verbose"],
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.codeActionsOnSave": {
            "source.organizeImports": "always"
        }
      }
}