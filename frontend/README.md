# JobPilot frontend

React + TypeScript + Vite frontend for JobPilot AI.

See the [repository README](../README.md) for setup, environment variables, API configuration, and the full workflow, and the [Sprint 1 report](../docs/SPRINT_1_REPORT.md) for implemented changes.

```sh
npm ci
npm run dev -- --host 127.0.0.1
npm test
npm run lint
npm run build
```

Configure `VITE_API_URL` in `.env` using `.env.example`. The local backend normally runs on port 8001.
