# Quick Navigation Guide

Find what you need quickly!

## 🚀 I Want To...

### Deploy the Agent
```bash
./deploy
```
Or see: [Deployment Guide](docs/deployment/DEPLOY_NOW.md)

### Start Chatting
```bash
./chat
```
Or see: [Chat Guide](docs/guides/START_CHATTING.md)

### Troubleshoot Issues
- [Lambda Troubleshooting](docs/deployment/TROUBLESHOOT_LAMBDA.md)
- [Check Logs](scripts/utils/check_lambda_logs.sh)

### Understand the Project
- [Project Structure](PROJECT_STRUCTURE.md)
- [Main README](README.md)

### Contribute
- [Contributing Guide](CONTRIBUTING.md)
- [Source Code](src/redshift_migrate/)

### Publish/Share
- [Publishing Guide](docs/release/PUBLISHING_GUIDE.md)
- [GitHub Setup](docs/release/GITHUB_SETUP_GUIDE.md)

## 📁 Directory Guide

```
📦 Root
├── 📄 README.md              ← Start here
├── 📄 PROJECT_STRUCTURE.md   ← Project layout
├── 🔧 chat                   ← Quick chat command
├── 🔧 deploy                 ← Quick deploy command
│
├── 📚 docs/
│   ├── deployment/           ← How to deploy
│   ├── guides/               ← User guides
│   ├── release/              ← Publishing docs
│   └── archive/              ← Old docs
│
├── 🔧 scripts/
│   ├── deployment/           ← Deploy scripts
│   ├── chat/                 ← Chat interface
│   └── utils/                ← Utilities
│
├── 💻 src/                   ← Source code
├── 💡 examples/              ← Example scripts
├── 🧪 tests/                 ← Test files
└── ☁️  aws_deploy/           ← AWS configs
```

## 🎯 Common Tasks

| Task | Command | Documentation |
|------|---------|---------------|
| Deploy | `./deploy` | [Guide](docs/deployment/DEPLOY_NOW.md) |
| Chat | `./chat` | [Guide](docs/guides/START_CHATTING.md) |
| Check logs | `scripts/utils/check_lambda_logs.sh` | [Troubleshooting](docs/deployment/TROUBLESHOOT_LAMBDA.md) |
| Run tests | `pytest tests/` | [Tests](tests/) |
| Build | `sam build --use-container` | [Deployment](docs/deployment/DEPLOY.md) |

## 📖 Documentation Index

### Getting Started
1. [README.md](README.md) - Project overview
2. [START_CHATTING.md](docs/guides/START_CHATTING.md) - Quick start
3. [DEPLOY_NOW.md](docs/deployment/DEPLOY_NOW.md) - Deploy guide

### User Guides
- [Chat Guide](docs/guides/CHAT_GUIDE.md) - Complete chat documentation
- [Security Setup](docs/guides/SECURE_ACCESS.md) - IAM and permissions
- [Quick Start](docs/QUICKSTART.md) - Migration patterns

### Deployment
- [Deploy Now](docs/deployment/DEPLOY_NOW.md) - Quick deployment
- [Full Deployment Guide](docs/deployment/DEPLOY.md) - Complete guide
- [AWS Deployment](docs/deployment/AWS_DEPLOYMENT.md) - AWS-specific
- [Troubleshooting](docs/deployment/TROUBLESHOOT_LAMBDA.md) - Fix issues

### Publishing
- [Publishing Guide](docs/release/PUBLISHING_GUIDE.md) - How to publish
- [GitHub Setup](docs/release/GITHUB_SETUP_GUIDE.md) - GitHub config
- [Release Notes](docs/release/RELEASE_NOTES_v1.0.0.md) - v1.0.0

### Development
- [Contributing](CONTRIBUTING.md) - How to contribute
- [Project Structure](PROJECT_STRUCTURE.md) - Code organization
- [Source Code](src/redshift_migrate/) - Main package

## 🔍 Finding Specific Information

### Deployment Issues?
→ [docs/deployment/TROUBLESHOOT_LAMBDA.md](docs/deployment/TROUBLESHOOT_LAMBDA.md)

### How to use chat?
→ [docs/guides/START_CHATTING.md](docs/guides/START_CHATTING.md)

### Security setup?
→ [docs/guides/SECURE_ACCESS.md](docs/guides/SECURE_ACCESS.md)

### Want to publish?
→ [docs/release/PUBLISHING_GUIDE.md](docs/release/PUBLISHING_GUIDE.md)

### Need examples?
→ [examples/](examples/)

### Want to contribute?
→ [CONTRIBUTING.md](CONTRIBUTING.md)

## 💡 Tips

- **Quick commands**: Use `./chat` and `./deploy` from root
- **Documentation**: Everything is in `docs/`
- **Scripts**: All scripts are in `scripts/`
- **Source code**: Main package is in `src/redshift_migrate/`
- **Examples**: Check `examples/` for usage patterns

## 🆘 Still Lost?

1. Check [README.md](README.md) for overview
2. Check [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for layout
3. Open an issue on GitHub
4. Ask the agent: `./chat` and type "help"

---

**Everything is organized and easy to find!** 🎉
