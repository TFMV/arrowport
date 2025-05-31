# Contributing to Arrowport 🤝

First off, thanks for taking the time to contribute! 🎉

## Development Setup

1. **Clone the repository:**

```bash
git clone https://github.com/TFMV/arrowport.git
cd arrowport
```

2. **Set up your development environment:**

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
poetry install
```

3. **Install pre-commit hooks:**

```bash
pre-commit install
```

## Development Workflow

1. **Create a new branch:**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes:**

- Write tests for new features
- Update documentation as needed
- Follow the code style guidelines

3. **Run tests:**

```bash
pytest
```

4. **Format and lint your code:**

```bash
# Format with black
black .

# Sort imports
isort .

# Type checking
mypy .
```

## Code Style Guidelines

- Follow PEP 8
- Use type hints
- Write docstrings for functions and classes
- Keep functions focused and small
- Use meaningful variable names

## Testing

- Write tests for new features
- Maintain test coverage
- Use pytest fixtures when appropriate
- Mock external services

## Submitting Changes

1. **Push your changes:**

```bash
git push origin feature/your-feature-name
```

2. **Create a Pull Request:**

- Use a clear title
- Describe your changes
- Reference any related issues
- Include test results

## Adding New Features

When adding new features:

1. **Design First:**
   - Discuss major changes in an issue
   - Consider backward compatibility
   - Think about performance implications

2. **Implementation:**
   - Start with tests
   - Add documentation
   - Include examples
   - Consider error cases

3. **Review:**
   - Self-review your code
   - Request reviews from maintainers
   - Address feedback promptly

## Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions and classes
- Include examples in docstrings
- Update API documentation

## Performance Considerations

- Use zero-copy operations where possible
- Consider memory usage
- Profile code changes
- Test with large datasets

## Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

---

Happy coding! 🚀
