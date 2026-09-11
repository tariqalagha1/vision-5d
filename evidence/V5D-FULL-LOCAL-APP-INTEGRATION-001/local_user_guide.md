# Vision 5D — Local User Guide

## Prerequisites
- Windows 10/11
- Python 3.11 (C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe)
- Browser (Chrome, Edge, Firefox)

## Quick Start

### Start the application
```
C:\Users\admin\workspaces\vision-5d\start_vision5d_local.bat
```

This starts the API server on port 8000 and a static file server on port 8100.

### Open the dashboard
```
http://localhost:8100/index.html
```

### Login
The application uses demo authentication. Click "Sign In" and use Google as the provider.

### Configure AI
1. Navigate to AI Settings
2. Select a provider (OpenAI, Anthropic, DeepSeek, Google)
3. Enter your API key — it is encrypted and never stored in the browser
4. Select a vision-capable model

### Create a Project
1. Click "New Project"
2. Enter project name and type
3. The project appears immediately in the dashboard

### Upload a Photo
1. Open the project
2. Use the upload form (accepts PNG, JPEG, WebP)
3. The file is validated and hashed

### Studio
- Open Studio to view/edit 3D drafts
- Furniture library available
- Undo/redo supported
- Commit versions for immutable history

## Service Ports
| Service | Port | URL |
|---------|------|-----|
| API | 8000 | http://localhost:8000 |
| Static | 8100 | http://localhost:8100 |
| API Docs | 8000 | http://localhost:8000/docs |
| Health | 8000 | http://localhost:8000/health |

## Stop the Application
Press any key in the startup window, or:
```
taskkill /FI "WINDOWTITLE eq Vision5D-*" /F
```

## Restart
Run `start_vision5d_local.bat` again. All project data persists in the SQLite database.

## Output Locations
- Database: `vision5d.db`
- Evidence: `evidence/`
- Storage: `storage/`
- Test data: `test_data/`

## Troubleshooting
- **"Python deps missing"**: Run `pip install -e ".[dev]"`
- **Backend won't start**: Check port 8000 is free
- **Login fails**: Clear cookies and re-authenticate
- **Projects not showing**: Workspace auto-discovers on first load; may take a moment
