# RNSVG

**Reticulum-native communication** with the MeshChatX user interface — built on **raw RNS only** (no LXMF, no LXST).

| | |
|---|---|
| **Version** | 0.3.3 (Phase 2) |
| **UI** | MeshChatX Vue 3 frontend (rebranded) |
| **Transport** | Reticulum Network Stack (`rns`) |
| **Status** | Identity, discovery, and text messaging over raw RNS packets |

## What is RNSVG?

RNSVG takes the polished MeshChatX frontend (chat layout, file UI, call UI, settings, multi-identity shell) and replaces the LXMF/LXST backend with a clean **raw Reticulum** implementation.

**Included now:**
- MeshChatX Vue UI (Nomad Network tab removed, RNSVG branding)
- `rnsvg` Python backend on raw RNS (no LXMF/LXST)
- Multi-identity management with persistent storage
- Peer discovery via `rnsvg.node` announces
- Text messaging over `RNS.Packet` to `rnsvg.inbox` destinations
- WebSocket push for new messages (`lxmf.delivery`, `lxmf_message_created`)
- Share folder scaffold, telephony scaffold, interface management
- Run-from-source scripts for Linux, macOS, Windows

**Not included yet (planned):**
- Peer file transfer over `RNS.Resource` (unlimited size, link speed)
- Full voice/video over `RNS.Buffer` + Opus
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

## Architecture

```
meshchatx/src/frontend/   Vue 3 UI (from MeshChatX, rebranded)
        │
        │  HTTP /api/v1/*  +  WebSocket /ws
        ▼
rnsvg/                    Python backend
  ├── server.py           Entry point
  ├── router.py           API routes (MeshChatX-compatible shapes)
  ├── messaging.py        Text messages via RNS.Packet → rnsvg.inbox
  ├── discovery.py        Peer announces (rnsvg.node)
  ├── identity_manager.py Persistent identities
  └── rns_transport.py    Reticulum init + destinations
        │
        ▼
   Reticulum Network
```

The legacy `meshchatx/meshchat.py` LXMF backend is **not used**. It remains in the tree as reference during migration.

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
| **0** | Import MeshChatX UI, strip LXMF/LXST backend, stub API, boot | Done |
| **1** | RNS core, identities, peer discovery | Done |
| **2** | Text messaging via `RNS.Packet` | **Current (v0.3.3)** |
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