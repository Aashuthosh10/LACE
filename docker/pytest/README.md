# Approved pytest image

`lace-pytest:3.12-v1` is provisioned by an administrator, never by a LACE run.

```powershell
docker build --pull=false --platform linux/amd64 --tag lace-pytest:3.12-v1 docker/pytest
docker image inspect lace-pytest:3.12-v1
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges `
  --user 65534:65534 lace-pytest:3.12-v1 python -m pytest --version
```

The Dockerfile pins the official Python 3.12.12 amd64 manifest. `requirements.lock` pins every wheel by version and SHA-256. Provisioning is the only stage allowed to contact the package index. Execution never pulls an image, installs dependencies, or accepts repository-provided commands or Docker flags. Rebuild deliberately after reviewing base and dependency updates; do not move this tag to an unreviewed image.
