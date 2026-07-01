# RNSVG

**Reticulum-native communication** with the MeshChatX user interface — built on **raw RNS only** (no LXMF, no LXST).

| | |
|---|---|
| **Version** | 0.1.0 (Phase 0) |
| **UI** | MeshChatX Vue 3 frontend (rebranded) |
| **Transport** | Reticulum Network Stack (`rns`) |
| **Status** | UI boots with stub backend — messaging/calls coming in Phase 1+ |

## What is RNSVG?

RNSVG takes the polished MeshChatX frontend (chat layout, file UI, call UI, settings, multi-identity shell) and replaces the LXMF/LXST backend with a clean **raw Reticulum** implementation.

**Included in Phase 0:**
- MeshChatX Vue UI (Nomad Network tab removed)
- New `rnsvg` Python backend (stub API + minimal RNS init)
- Run-from-source scripts for Linux, macOS, Windows
- Android project scaffold (APK build path documented)

**Not included yet (planned):**
- Real text messaging over `RNS.Packet`
- Peer file transfer over `RNS.Resource` (unlimited size, link speed)
- Voice/video over `RNS.Buffer` + Opus
- Electron desktop builds (deferred)

## Quick Start

### Arch Linux

```bash
sudo pacman -S python python-pip nodejs pnpm
git clone https://github.com/narl3yyy-svg/RNSVG.git
cd RNSVG
./run.sh
```

Open **http://127.0.0.1:8787**

### Ubuntu / Debian

```bash
sudo apt install python3 python3-venv python3-pip nodejs npm
sudo npm install -g pnpm
git clone https://github.com/narl3yyy-svg/RNSVG.git
cd RNSVG
./run.sh
```

### macOS

```bash
brew install python node pnpm
git clone https://github.com/narl3yyy-svg/RNSVG.git
cd RNSVG
./run.sh
```

### Windows

```cmd
git clone https://github.com/narl3yyy-svg/RNSVG.git
cd RNSVG
run.bat
```

Then open **http://127.0.0.1:8787** in your browser.

## Manual Run

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pnpm install --frozen-lockfile
pnpm run build-frontend
python -m rnsvg --headless --host 127.0.0.1 --port 8787
```

### CLI options

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--host` | `RNSVG_HOST` | `127.0.0.1` | Bind address |
| `--port` | `RNSVG_PORT` | `8000` | HTTP port (`run.sh` uses 8787) |
| `--headless` | — | off | Do not open browser |

## Reticulum Configuration

RNSVG stores data in `~/.rnsvg/`:

```
~/.rnsvg/
├── .reticulum/config    # Isolated RNS config (AutoInterface, no LXMF discovery)
└── identity             # RNS identity (created in Phase 1)
```

To use your existing Reticulum network (e.g. WireGuard interfaces), copy your interface blocks from `~/.reticulum/config` into `~/.rnsvg/.reticulum/config`, or set:

```bash
export RNSVG_DATA_DIR=~/.rnsvg
# Edit ~/.rnsvg/.reticulum/config with your TCP/WireGuard interfaces
```

## Architecture (Phase 0)

```
meshchatx/src/frontend/   Vue 3 UI (from MeshChatX, rebranded)
        │
        │  HTTP /api/v1/*  +  WebSocket /ws
        ▼
rnsvg/                    New Python backend
  ├── server.py           Entry point
  ├── stub_router.py      API compatibility layer (stub responses)
  ├── responses.py        JSON shapes matching MeshChatX contracts
  └── rns_transport.py    Minimal RNS.Reticulum init
        │
        ▼
   Reticulum Network
```

The legacy `meshchatx/meshchat.py` and LXMF backend are **not used** in Phase 0. They remain in the tree only as reference during migration and will be removed in later phases.

## File Transfer (planned — Phase 3)

Files will transfer **directly between connected peers** using `RNS.Link` + `RNS.Resource`:

- No LXMF 100 MB cap
- Speed limited only by the link to the peer
- Progress events wired to the existing MeshChatX file UI

## Android APK

See [android/README.md](android/README.md). Phase 0 keeps the MeshChatX Android scaffold; full Chaquopy integration is planned for Phase 6.

```bash
bash scripts/build-android-wheels-local.sh   # when backend deps are finalized
cd android && ./gradlew :app:assembleDebug
```

## Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| **0** | Import MeshChatX UI, strip LXMF/LXST backend, stub API, boot | **Current** |
| **1** | RNS core, identities, peer discovery | Planned |
| **2** | Text messaging via `RNS.Packet` | Planned |
| **3** | File transfer via `RNS.Resource` | Planned |
| **4** | Voice calls via `RNS.Buffer` + Opus | Planned |
| **5** | Video + screen sharing | Planned |
| **6** | Android APK + packaging polish | Planned |

## Requirements

- Python **3.11+**
- Node.js **24+** and **pnpm 11.1.2** (for frontend build)
- `rns` Python package (installed via `requirements.txt`)

## License

Based on MeshChatX (0BSD/MIT). See [LICENSE](LICENSE) and upstream attribution.