# -ATS_Center-Ats-ats-node

ats-ats-node/
├── README.md
├── agent/
│   ├── flash_fw.py
│   ├── power_control.py
│   ├── uart_logger.py
│   ├── gpio_reader.py
│   ├── camera_capture.py
│   ├── ai_validator.py
│   └── test_runner.py
├── exporters/
│   └── prometheus_exporter.py
└── tests/
    └── test_gpio_oled.py

## Role of the ATS Node
The ATS node is the execution and observation plane of the ATS platform. It is intentionally separated from CI infrastructure to ensure deterministic hardware access, reliable test execution, and reproducible results on real devices.
