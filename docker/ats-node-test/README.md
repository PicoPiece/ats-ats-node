# ATS Node Test Execution Container

> **Docker container that owns ALL hardware interaction for ATS testing**

## 🎯 Purpose

This container is the **execution brain** of the ATS platform. It centralizes all hardware interaction logic so that:

- **Jenkins is "dumb"** - only runs this container, doesn't know about USB ports, GPIO, or flashing
- **Hardware logic is isolated** - all USB detection, flashing, and hardware access happens here
- **Test runner is decoupled** - test logic (ats-test-esp32-demo) doesn't need to know about hardware

## 📋 Responsibilities

This container:

1. **Loads manifest** from `/workspace/ats-manifest.yaml`
2. **Detects hardware** (USB ports, GPIO access)
3. **Flashes firmware** to ESP32
4. **Invokes test runner** (ats-test-esp32-demo)
5. **Writes structured results** to `/workspace/results/`

## 🏗️ Architecture

```
Jenkins (dumb)
    ↓
    docker run ats-node-test:latest
    ↓
ats-node-test container:
    ├── Load manifest
    ├── Flash firmware (hardware.py + flash_esp32.py)
    ├── Run tests (executor.py → ats-test-esp32-demo)
    └── Write results (results.py)
```

## 📁 Structure

```
docker/ats-node-test/
├── Dockerfile              # Container definition
├── entrypoint.sh          # Main entrypoint
└── ats_node_test/         # Python execution logic
    ├── __init__.py
    ├── manifest.py         # Load & validate manifest
    ├── hardware.py         # USB/GPIO detection
    ├── flash_esp32.py      # Firmware flashing
    ├── executor.py         # Main orchestrator
    └── results.py          # Result generation
```

## 🚀 Usage

### Build

```bash
cd ats-ats-node/docker/ats-node-test
docker build -t ats-node-test:latest .
```

### Run (from Jenkins)

```bash
docker run --rm --privileged \
  -v /dev:/dev \
  -v /sys/class/gpio:/sys/class/gpio:ro \
  -v /dev/gpiomem:/dev/gpiomem \
  -v $WORKSPACE:/workspace \
  ats-node-test:latest
```

### Expected Workspace Structure

```
/workspace/
├── ats-manifest.yaml      # Required: test manifest
├── firmware-esp32.bin     # Required: firmware artifact
├── ats-test-esp32-demo/   # Optional: test runner repo
└── results/               # Output: test results
    ├── ats-summary.json
    ├── junit.xml
    ├── meta.yaml
    └── serial.log
```

## 📊 Output Contract

Results are written to `/workspace/results/`:

- **`ats-summary.json`**: Test summary with status and test results
- **`junit.xml`**: JUnit XML format for CI consumption
- **`meta.yaml`**: Execution metadata
- **`serial.log`**: UART logs (if captured)

## 🔒 Security

- Container requires `--privileged` for hardware access
- USB devices mounted via `-v /dev:/dev`
- GPIO access via `/sys/class/gpio` and `/dev/gpiomem`

## 🔗 Integration

This container is invoked by:
- **Jenkins test pipeline** (Jenkinsfile.test)
- **Direct execution** on ATS node (Raspberry Pi)

## 📝 Notes

- Container exit code reflects test pass/fail (0 = pass, non-zero = fail)
- All hardware detection is automatic (no hardcoded ports)
- Test runner (ats-test-esp32-demo) is invoked as subprocess
