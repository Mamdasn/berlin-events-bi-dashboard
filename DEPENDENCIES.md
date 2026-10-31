# Gateway runtime dependency updates

Use Python 3.12. `requirements.txt` contains direct pins; `requirements.lock`
contains the complete runtime resolution with package hashes. Docker and CI
install the lock with `pip install --require-hashes -r requirements.lock`.

After editing the direct pins, regenerate in a Linux Python 3.12 environment with
`pip-tools==7.6.2`:

```sh
pip-compile --generate-hashes --strip-extras --no-emit-index-url \
  --no-emit-trusted-host --output-file requirements.lock requirements.txt
pip-audit --strict --disable-pip --no-deps -r requirements.lock
```

Install into a fresh environment, run `pip check` before installing test tools,
then run `pytest -q` and build the gateway Dockerfile. Runtime workers now use
`uvicorn_worker.UvicornWorker` and the maintained external worker package.

This update publishes gateway image tag `0.2.1` after merge through the existing
Docker publish workflow. The parent deployment must select that tag to use these
fixes. The separately built Grafana image is unchanged.
