# Contributing to Redshift Migration Agent

Thank you for your interest in contributing! 🎉

## How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly**
5. **Commit**: `git commit -m 'Add amazing feature'`
6. **Push**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## Development Setup

```bash
git clone https://github.com/YOUR-USERNAME/redshift-migration-agent
cd redshift-migration-agent
./deploy_agent.sh
source venv/bin/activate
```

## Testing

```bash
# Run tests
python -m pytest tests/

# Test the agent
python redshift_agent.py
```

## Code Style

- Follow PEP 8
- Add docstrings to functions
- Keep functions focused and small
- Add type hints where possible

## Pull Request Guidelines

- Update documentation if needed
- Add tests for new features
- Ensure all tests pass
- Keep PRs focused on a single feature/fix

## Reporting Issues

Use GitHub Issues to report bugs or request features.

Include:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment details

## Questions?

Open a Discussion on GitHub!

Thank you for contributing! 🙏
