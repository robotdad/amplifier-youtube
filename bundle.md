---
bundle:
  name: youtube
  version: 2.0.0
  description: YouTube assistant — download audio/video, search with rich filters, and access account feeds

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: youtube:behaviors/youtube
---

# YouTube Assistant

@youtube:context/instructions.md

---

@foundation:context/shared/common-system-base.md
