# RNSVG Android (Phase 0 scaffold)

This directory is inherited from MeshChatX and will be adapted for RNSVG in Phase 6.

## Phase 0 status

- Project structure and Chaquopy wiring are present
- Backend entry will be `rnsvg` (not `meshchatx.meshchat`)
- LXMF/LXST wheels are **not** required for RNSVG — wheel scripts will be updated in Phase 6

## Planned build (Phase 6+)

```bash
# From repo root, after Python backend is finalized:
bash scripts/build-android-wheels-local.sh
cd android
./gradlew :app:assembleDebug
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk`

## Native audio plan

RNSVG will use **AAudio** / platform audio + Opus via Python/`opuslib` in Chaquopy — not LXST Telephone.

## Phase 0

Use desktop `run.sh` / web UI for development. Android APK is not validated in Phase 0.