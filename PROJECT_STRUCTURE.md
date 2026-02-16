# Project Structure

Clean, organized structure for the Redshift Migration Agent project.

## Directory Layout

```
redshift-migration-agent/
├── README.md                    # Main project documentation
├── LICENSE                      # MIT License
├── CONTRIBUTING.md              # Contribution guidelines
├── CHANGELOG.md                 # Version history
│
├── docs/                        # 📚 All documentation
│   ├── deployment/              # Deployment guides
│   │   ├── DEPLOY.md           # Complete deployment guide
│   │   ├── DEPLOY_NOW.md       # Quick deployment
│   │   ├── AWS_DEPLOYMENT.md   # AWS-specific deployment
│   │   └── TROUBLESHOOT_LAMBDA.md
│   ├── guides/                  # User guides
│   │   ├── START_CHATTING.md   # Quick start for chat
│   │   ├── CHAT_GUIDE.md       # Complete chat guide
│   │   ├── SECURE_ACCESS.md    # Security setup
│   │   └── QUICKSTART.md       # General quick start
│   ├── release/                 # Release & publishing
│   │   ├── PUBLISHING_GUIDE.md # How to publish
│   │   ├── RELEASE_NOTES_v1.0.0.md
│   │   └── GITHUB_SETUP_GUIDE.md
│   └── archive/                 # Old/redundant docs
│
├── scripts/                     # 🔧 All executable scripts
│   ├── deployment/              # Deployment scripts
│   │   ├── quick_deploy.sh     # One-command deploy
│   │   ├── deploy_to_aws.sh    # AWS deployment
│   │   └── redeploy.sh         # Redeploy after changes
│   ├── chat/                    # Chat interface
│   │   ├── chat.sh             # Simple chat wrapper
│   │   ├── chat_with_agent.py  # Basic chat interface
│   │   └── chat_advanced.py    # Advanced chat with history
│   └── utils/                   # Utility scripts
│       ├── fix_lambda.sh       # Lambda diagnostics
│       ├── check_lambda_logs.sh
│       └── test_chat.sh
│
├── src/                         # 📦 Source code
│   └── redshift_migrate/        # Python package
│       ├── extractors/          # Config extractors
│       ├── transformers/        # Config transformers
│       └── appliers/            # Config appliers
│
├── examples/                    # 💡 Example scripts
│   ├── simple_migration.py
│   ├── basic_migration.py
│   ├── advanced_migration.py
│   └── secure_client.py
│
├── tests/                       # 🧪 Test files
│   ├── test_extractor.py
│   └── test_parameter_groups.py
│
├── aws_deploy/                  # ☁️ AWS deployment configs
│   ├── deploy-to-ecs.sh
│   ├── deploy-to-lambda.sh
│   └── ecs-task-definition.json
│
├── .kiro/                       # 🤖 Kiro agent config
│   └── agents/
│       └── redshift-migration.md
│
├── template.yaml                # SAM/CloudFormation template
├── samconfig.toml              # SAM configuration
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Python project config
├── Dockerfile                  # Container image
├── docker-compose.yml          # Docker Compose config
│
├── lambda_handler.py           # Lambda entry point
├── redshift_agent.py           # Agent implementation
└── api_server.py               # FastAPI server
```

## Quick Navigation

### 🚀 Getting Started
- **Deploy**: `docs/deployment/DEPLOY_NOW.md`
- **Chat**: `docs/guides/START_CHATTING.md`
- **Quick Start**: `docs/QUICKSTART.md`

### 📖 Documentation
- **Deployment**: `docs/deployment/`
- **User Guides**: `docs/guides/`
- **API Docs**: `docs/`

### 🔧 Scripts
- **Deploy**: `scripts/deployment/quick_deploy.sh`
- **Chat**: `scripts/chat/chat.sh`
- **Utils**: `scripts/utils/`

### 💻 Development
- **Source**: `src/redshift_migrate/`
- **Tests**: `tests/`
- **Examples**: `examples/`

## File Purposes

### Root Files

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `LICENSE` | MIT License |
| `CONTRIBUTING.md` | How to contribute |
| `CHANGELOG.md` | Version history |
| `template.yaml` | SAM/CloudFormation template |
| `lambda_handler.py` | Lambda function entry point |
| `redshift_agent.py` | Agent implementation |
| `api_server.py` | FastAPI REST API server |

### Documentation (`docs/`)

| Directory | Contents |
|-----------|----------|
| `deployment/` | Deployment guides and troubleshooting |
| `guides/` | User guides (chat, security, quick start) |
| `release/` | Publishing and release documentation |
| `archive/` | Old/redundant documentation |

### Scripts (`scripts/`)

| Directory | Contents |
|-----------|----------|
| `deployment/` | Deployment and setup scripts |
| `chat/` | Chat interface scripts |
| `utils/` | Utility and diagnostic scripts |

### Source Code (`src/`)

| Directory | Contents |
|-----------|----------|
| `redshift_migrate/` | Main Python package |
| `extractors/` | Extract config from provisioned |
| `transformers/` | Transform config for serverless |
| `appliers/` | Apply config to serverless |

## Common Tasks

### Deploy the Agent
```bash
scripts/deployment/quick_deploy.sh
```

### Start Chatting
```bash
scripts/chat/chat.sh
```

### Check Logs
```bash
scripts/utils/check_lambda_logs.sh
```

### Run Tests
```bash
pytest tests/
```

### Build Package
```bash
sam build --use-container
```

## Documentation Index

### For Users
1. **Getting Started**: `docs/guides/START_CHATTING.md`
2. **Deployment**: `docs/deployment/DEPLOY_NOW.md`
3. **Chat Guide**: `docs/guides/CHAT_GUIDE.md`
4. **Security**: `docs/guides/SECURE_ACCESS.md`

### For Developers
1. **Contributing**: `CONTRIBUTING.md`
2. **Architecture**: `docs/ARCHITECTURE.md` (if exists)
3. **API Reference**: `docs/API_REFERENCE.md` (if exists)
4. **Testing**: `tests/README.md` (if exists)

### For Publishers
1. **Publishing Guide**: `docs/release/PUBLISHING_GUIDE.md`
2. **Release Notes**: `docs/release/RELEASE_NOTES_v1.0.0.md`
3. **GitHub Setup**: `docs/release/GITHUB_SETUP_GUIDE.md`

## Maintenance

### Adding New Documentation
- Deployment docs → `docs/deployment/`
- User guides → `docs/guides/`
- Release docs → `docs/release/`

### Adding New Scripts
- Deployment scripts → `scripts/deployment/`
- Chat scripts → `scripts/chat/`
- Utility scripts → `scripts/utils/`

### Archiving Old Files
- Move to `docs/archive/`
- Update references in other docs
- Add note in CHANGELOG.md

## Benefits of This Structure

✅ **Clear Organization**: Easy to find what you need
✅ **Logical Grouping**: Related files together
✅ **Scalable**: Easy to add new files
✅ **Clean Root**: Only essential files in root
✅ **Standard Layout**: Follows Python project conventions

## Migration from Old Structure

If you have old paths in scripts or docs:

| Old Path | New Path |
|----------|----------|
| `./DEPLOY.md` | `docs/deployment/DEPLOY.md` |
| `./chat_with_agent.py` | `scripts/chat/chat_with_agent.py` |
| `./quick_deploy.sh` | `scripts/deployment/quick_deploy.sh` |
| `./CHAT_GUIDE.md` | `docs/guides/CHAT_GUIDE.md` |

## Questions?

- Check `README.md` for overview
- Check `docs/guides/` for user guides
- Check `docs/deployment/` for deployment help
- Open an issue on GitHub

---

**Clean, organized, and easy to navigate!** 🎉
