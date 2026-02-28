# 📁 BioTrust - Project Structure

## Directory Organization

```
BioTrust/
├── 📂 src/                          # Source code (core application)
│   ├── 📂 api/
│   │   └── api_server.py           # FastAPI REST API server
│   ├── 📂 core/
│   │   ├── risk_engine.py          # Transaction risk analysis
│   │   ├── liveness_detector.py    # Active liveness detection
│   │   ├── passive_liveness.py     # Passive liveness (rPPG)
│   │   └── transaction_logger.py   # Transaction logging system
│   └── payment_system.py           # Payment orchestrator (console)
│
├── 📂 web/                          # Frontend applications
│   ├── 📂 streamlit/
│   │   └── web_app.py             # Streamlit web interface
│   └── 📂 html/
│       └── index.html             # Standalone HTML/CSS/JS interface
│
├── 📂 demos/                        # Demo applications
│   ├── main_app.py                # Interactive console demo
│   ├── demo_liveness.py           # Liveness detection demo
│   ├── demo_presentation.py       # Automated presentation demo
│   └── demo_risk.py               # Risk engine demo
│
├── 📂 tests/                        # Test files
│   ├── test_integrated_liveness.py # Integration tests
│   ├── test_system.py             # System health check
│   └── 📂 legacy/                  # Legacy test files
│       ├── blink_mesh_test_v1.py
│       ├── face_mesh_test_v0.py
│       ├── iter_mesh_test_v2.py
│       └── upg_iter_mesh_test_v3.py
│
├── 📂 scripts/                      # Startup scripts
│   ├── start_all.bat              # Start API + Web interface
│   ├── start_api.bat              # Start API server only
│   ├── start_web.bat              # Start Streamlit only
│   └── start_html.bat             # Open HTML interface
│
├── 📂 docs/                         # Documentation
│   ├── GUIA_API_WEB.md            # API & Web guide (Portuguese)
│   ├── PASSIVE_LIVENESS_TECH.md   # rPPG technical documentation
│   ├── TESTE_COMPLETO.md          # Complete testing guide
│   └── PROJECT_STRUCTURE.md       # This file
│
├── 📂 data/                         # Data files
│   ├── transaction_log.json       # Transaction history
│   └── user_profiles.json         # User profile data
│
├── 📂 venv310/                      # Python virtual environment
│
├── 📄 .gitignore                    # Git ignore rules
├── 📄 LICENSE                       # MIT License
├── 📄 README.md                     # Main project documentation
└── 📄 requirements.txt              # Python dependencies

```

## 🚀 Quick Start

### Run Everything
```bash
.\scripts\start_all.bat
```

### Run Individual Components
```bash
# API Server
.\scripts\start_api.bat

# Web Interface (Streamlit)
.\scripts\start_web.bat

# HTML Interface
.\scripts\start_html.bat
```

### Run From Source
```bash
# API Server
.\venv310\Scripts\python.exe src\api\api_server.py

# Streamlit
.\venv310\Scripts\streamlit run web\streamlit\web_app.py

# Demos
.\venv310\Scripts\python.exe demos\main_app.py
.\venv310\Scripts\python.exe demos\demo_liveness.py

# Tests
.\venv310\Scripts\python.exe tests\test_system.py
.\venv310\Scripts\python.exe tests\test_integrated_liveness.py
```

## 📦 Module Structure

### Core Modules (`src/core/`)
- **risk_engine.py**: Analyzes transaction risk (0-100 score) based on amount, location, time, behavior
- **liveness_detector.py**: Active liveness via eye blinks + head movements
- **passive_liveness.py**: Passive liveness via rPPG (heart rate detection)
- **transaction_logger.py**: Logs all transactions to JSON file

### API Module (`src/api/`)
- **api_server.py**: FastAPI REST API with endpoints for risk analysis, liveness verification, and payment processing

### Web UIs (`web/`)
- **streamlit/web_app.py**: Full-featured Streamlit interface with multiple pages
- **html/index.html**: Lightweight standalone web interface

## 🔧 Development

### Adding New Features
- Core logic → `src/core/`
- API endpoints → `src/api/api_server.py`
- Web UI → `web/streamlit/web_app.py` or `web/html/index.html`
- Demos → `demos/`

### Running Tests
```bash
# Full system check
.\venv310\Scripts\python.exe tests\test_system.py

# Integrated liveness test
.\venv310\Scripts\python.exe tests\test_integrated_liveness.py
```

## 📊 Technology Stack

- **Python 3.10**: Core language
- **FastAPI + Uvicorn**: REST API
- **Streamlit**: Web interface
- **OpenCV 4.13**: Video processing
- **MediaPipe 0.10**: Face mesh detection
- **SciPy**: Signal processing (FFT for rPPG)
- **NumPy**: Numerical computing

## 🎯 Entry Points

| Purpose | File | Description |
|---------|------|-------------|
| **Production API** | `src/api/api_server.py` | FastAPI REST server |
| **Web Interface** | `web/streamlit/web_app.py` | Streamlit UI |
| **Console Demo** | `demos/main_app.py` | Interactive terminal UI |
| **Liveness Demo** | `demos/demo_liveness.py` | Liveness modes showcase |
| **Testing** | `tests/test_system.py` | System health check |

## 📝 Notes

- All scripts in `scripts/` should be run from project root
- Python imports use absolute paths from project root
- Data files in `data/` are auto-created if missing
- Legacy tests in `tests/legacy/` are for reference only

---

**Last Updated**: February 28, 2026  
**TecStorm '26** - Team BioTrust
