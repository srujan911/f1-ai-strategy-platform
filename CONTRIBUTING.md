# Contributing to F1 AI Strategy Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Welcome diverse perspectives and experiences

## Getting Started

### Development Environment Setup

1. **Fork the repository** on GitHub
2. **Clone your fork locally**
   ```bash
   git clone https://github.com/yourusername/f1-ai-strategy-platform.git
   cd f1-ai-strategy-platform
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Development Workflow

### Creating a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions

### Code Standards

#### Style Guide
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Line length: 120 characters (configured in black)
- Use type hints for all function parameters and return values

#### Formatting
```bash
# Auto-format code with black
black src/ tests/ app/

# Sort imports with isort
isort src/ tests/ app/

# Check style with flake8
flake8 src/ tests/ app/

# Type checking with mypy
mypy src/
```

#### Docstring Format
Use Google-style docstrings for all public functions and classes:

```python
def your_function(param1: str, param2: int) -> bool:
    """
    Short description of what the function does.

    Longer description explaining the function's behavior, 
    context, and any important details.

    Args:
        param1 (str): Description of param1
        param2 (int): Description of param2

    Returns:
        bool: Description of return value

    Raises:
        ValueError: When something goes wrong

    Example:
        >>> result = your_function("test", 42)
        >>> print(result)
        True
    """
    # Implementation here
    pass
```

### Testing

#### Writing Tests
- Place tests in `tests/test_*.py` files
- Use pytest for testing framework
- Write descriptive test names

```python
def test_specific_behavior_with_edge_case():
    """Test that function handles edge case correctly."""
    # Arrange
    input_data = ...
    expected_output = ...
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_output
```

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

#### Coverage Requirements
- Aim for >80% code coverage on new features
- Always test edge cases and error conditions

### Commits

#### Commit Message Format
Use clear, descriptive commit messages:

```
[Type] Brief description (50 chars max)

Longer explanation if needed. Wrap at 72 characters.
Explain what changed and why, not how.

Fixes #123 (if applicable)
```

Types:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring
- `docs:` Documentation update
- `test:` Test addition
- `perf:` Performance improvement
- `chore:` Maintenance task

Examples:
- `feat: Add weather impact modeling to lap time prediction`
- `fix: Correct fuel correction calculation in tyre degradation`
- `docs: Update README with API examples`

## Pull Request Process

1. **Update documentation** for any API changes
2. **Add tests** for new functionality
3. **Ensure all tests pass**
   ```bash
   pytest
   ```

4. **Run code quality checks**
   ```bash
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of changes made
   - Reference to related issues (#123)
   - Screenshots/plots if UI changes

### PR Review Process
- Address review comments promptly
- Push updates to the same branch
- Request re-review after updates
- Be open to feedback and suggestions

## Project Structure

```
src/
├── data_loader.py           # Data loading functions
├── feature_engineering.py   # Feature preprocessing
├── visualization.py         # Plotting utilities
├── analysis/               # Analysis modules
│   └── multi_race_analysis.py
├── models/                 # ML models
│   ├── lap_time_model.py
│   └── tyre_deg_model.py
├── strategy/               # Strategy optimization
│   └── pit_strategy.py
└── prediction/             # Predictions
    └── 2026_strategy.py

tests/                       # Unit tests
├── test_models.py
├── test_strategy.py
└── test_data_loader.py

app/
└── dashboard.py            # Streamlit dashboard
```

## Documentation

### Docstring Updates
Any API changes require docstring updates. Ensure examples work:

```python
def example_function(x: int) -> int:
    """
    Do something with x.

    Example:
        >>> example_function(5)
        10
    """
```

### README Updates
Update README.md for:
- New major features
- New dependencies
- API changes
- Installation changes

## Issues

### Reporting Bugs
- Search existing issues first
- Provide minimal reproducible example
- Include Python and dependency versions
- Describe expected vs actual behavior

### Suggesting Features
- Check existing issues for duplicates
- Explain use case and benefit
- Provide examples if possible
- Discuss feasibility

## Questions?

- Open a GitHub discussion
- Create an issue for questions
- Email: your.email@example.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for making F1 AI Strategy Platform better! 🏎️
