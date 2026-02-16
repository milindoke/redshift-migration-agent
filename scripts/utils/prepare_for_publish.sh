#!/bin/bash
# Prepare the project for public distribution

set -e

echo "📦 Preparing Redshift Migration Agent for Public Distribution"
echo "============================================================="

# Get current AWS account ID
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

if [ -z "$CURRENT_ACCOUNT" ]; then
  echo "⚠️  Warning: Could not detect AWS account ID"
  echo "Make sure AWS CLI is configured"
fi

echo ""
echo "Step 1: Removing hardcoded account IDs..."

# Files to clean
FILES_TO_CLEAN=(
  "aws_deploy/ecs-task-definition.json"
  "aws_deploy/task-role-policy.json"
  "aws_deploy/deploy-to-ecs.sh"
  "aws_deploy/deploy-to-lambda.sh"
  "aws_deploy/secure-access-setup.sh"
  "template.yaml"
)

for file in "${FILES_TO_CLEAN[@]}"; do
  if [ -f "$file" ]; then
    # Replace hardcoded account ID with placeholder
    if [ -n "$CURRENT_ACCOUNT" ]; then
      sed -i.bak "s/$CURRENT_ACCOUNT/\${AWS::AccountId}/g" "$file" 2>/dev/null || \
      sed -i '' "s/$CURRENT_ACCOUNT/\${AWS::AccountId}/g" "$file" 2>/dev/null || \
      echo "  Skipped $file (sed not available)"
    fi
    echo "  ✓ Cleaned $file"
  fi
done

echo ""
echo "Step 2: Creating LICENSE file..."

cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 Redshift Migration Agent Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

echo "  ✓ LICENSE created"

echo ""
echo "Step 3: Creating .gitignore..."

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/
dist/
build/

# AWS
.aws-sam/
lambda_package/
lambda_deployment.zip
*.bak
response.json
.agent-credentials

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Config
cluster-config.json
*.log

# Secrets
*.pem
*.key
.env
EOF

echo "  ✓ .gitignore created"

echo ""
echo "Step 4: Replacing README..."

mv README.md README_ORIGINAL.md 2>/dev/null || true
mv README_PUBLIC.md README.md

echo "  ✓ README updated for public distribution"

echo ""
echo "Step 5: Creating CONTRIBUTING.md..."

cat > CONTRIBUTING.md << 'EOF'
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
EOF

echo "  ✓ CONTRIBUTING.md created"

echo ""
echo "Step 6: Creating GitHub Actions workflow..."

mkdir -p .github/workflows

cat > .github/workflows/test.yml << 'EOF'
name: Test

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v
    
    - name: Check code style
      run: |
        pip install flake8
        flake8 src/ --max-line-length=120
EOF

echo "  ✓ GitHub Actions workflow created"

echo ""
echo "Step 7: Creating SAM build script..."

cat > build_sam.sh << 'EOF'
#!/bin/bash
# Build SAM application for deployment

set -e

echo "Building SAM application..."

# Install dependencies
pip install -r requirements-agent.txt -t .

# Build SAM
sam build

echo "✓ Build complete"
echo ""
echo "To deploy:"
echo "  sam deploy --guided"
EOF

chmod +x build_sam.sh

echo "  ✓ SAM build script created"

echo ""
echo "============================================================="
echo "✅ Project prepared for public distribution!"
echo "============================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Review and update these files:"
echo "   - README.md (add your GitHub username)"
echo "   - template.yaml (add your info)"
echo "   - LICENSE (add your name)"
echo ""
echo "2. Initialize git repository:"
echo "   git init"
echo "   git add ."
echo "   git commit -m 'Initial commit'"
echo ""
echo "3. Create GitHub repository and push:"
echo "   git remote add origin https://github.com/YOUR-USERNAME/redshift-migration-agent.git"
echo "   git push -u origin main"
echo ""
echo "4. Publish to AWS SAR:"
echo "   sam publish --template template.yaml --region us-east-1"
echo ""
echo "5. Share your project:"
echo "   - Add to AWS Solutions Library"
echo "   - Write a blog post"
echo "   - Share on social media"
echo ""
echo "For detailed publishing guide, see: PUBLIC_DISTRIBUTION.md"
