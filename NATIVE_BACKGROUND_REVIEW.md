# Native background tracking review

The previous implementation had no verifiable generated Android project in the repository: Android is created transiently in CI, and there was no local APK to inspect. The web call in `driverDash` was present, but source alone did not prove plugin registration, manifest merger output, or service execution.

This build now performs explicit post-`cap add` verification and APK permission verification. The service starts foreground before location requests, persists session credentials, requests both GPS and network LocationManager updates, holds a partial wake lock, and keeps a diagnostic persistent notification showing provider/permission, callback count, last coordinates, and publish errors. Battery optimization request is launched only after starting the foreground service.

Physical test remains required. The persistent notification distinguishes: permission pending; no provider; provider listening but no callbacks (OS/device restriction); GPS callback count advancing but publish errors; and successful publish.
