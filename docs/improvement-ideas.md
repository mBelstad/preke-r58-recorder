# Simplification & Optimization Ideas

## Pipelines (`src/pipelines.py`)

- **Duplicate HDMI branches**: Both `build_r58_pipeline` and `build_r58_preview_pipeline` now share the same HDMI source or conversion stages. Consider extracting a helper (e.g., `build_hdmi_source(device, resolution, target_fps)`) so we only describe the rk_hdmirx quirks once.
- **Static framerate assumptions**: Pipelines currently hardcode `framerate=60/1` for capture and `videorate` down to 30fps. Exposing these as config options (declare in `config.yml`) would let us match the actual camera output and avoid unnecessary `videorate` conversions when sources are already 30fps.
- **Encoder selection**: Preview and recording both use software `x264enc` with similar parameters. A single helper to build encoder/caps strings (passing bitrate + latency profile) would reduce errors and make it easier to toggle to hardware encoders later.

## Preview Manager (`src/preview.py`)

- **Hard dependency on global `recorder`**: `start_preview` imports `recorder` from `src.main` at runtime, creating a circular dependency. Passing a recorder stop callback (or injecting the recorder manager) would simplify testing and avoid surprises if we restructure `src.main`.
- **Per-camera threads**: We start/stop GStreamer pipelines synchronously for each camera. If the HDMI node is the only active capture, we could lazily start preview only for configured devices that are actually present to avoid repeated format-negotiation failures.

## Mixer Core (`src/mixer/core.py`)

- **Subprocess cleanup**: `_cleanup_stuck_pipelines` shells out to `pkill gst-launch-1.0`. Replacing this with in-process tracking (or at least limiting it to our own helper scripts) would make the mixer less invasive on the host.
- **Large monolithic methods**: `start()` handles scene selection, cleanup, pipeline build, bus wiring, and error reporting. Breaking these into smaller helpers (scene selection, pipeline creation, error-to-user-message) would make it easier to maintain and to add metrics.

## Deployment

- `deploy.sh` always stages & commits everything (`git add .`). Exposing a `--skip-git` flag or limiting staging to known files would avoid unintended commits during rapid testing.
- Requirements that rely on apt packages (PyGObject) should move out of `requirements.txt` so `pip install -r requirements.txt` succeeds on the device without attempting to compile GI from source.

These items don’t block the current release but will pay off once we stabilize the hardware mapping. Feel free to turn any bullet into a tracked issue when we plan the next sprint.

