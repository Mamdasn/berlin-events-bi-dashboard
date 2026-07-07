# Berlin Events BI Dashboard

Grafana OSS dashboards and a small FastAPI TOTP auth gateway for the Berlin
events deploy. The deploy repo serves this stack at `/dashboard/`.

The gateway auth code is intentionally copied from
`interactive-berlin-map-deploy/berlin-events-agent` at the time this scaffold was
created. Keep an eye on drift when curator auth changes.

## Services

- `bi-grafana`: Grafana 11.6.16 Ubuntu image with provisioned dashboards and UI edits disabled.
- `bi-auth-gateway`: password plus TOTP gateway for nginx `auth_request`.
