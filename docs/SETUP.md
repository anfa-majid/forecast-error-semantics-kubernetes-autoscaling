# Environment setup

## 1. Choose the reproduction level

Analysis-only reproduction needs Python and approximately 100 MB of free disk
space. A live example additionally needs Docker, kind, kubectl, Helm,
PowerShell 7, and sufficient resources for a three-node local cluster.

The original study used three amd64 Azure nodes running Ubuntu 24.04.4 LTS,
Kubernetes `v1.36.1+k3s1`, and containerd `2.2.3-k3s1`. A kind deployment is a
functional reproduction environment, not a performance-equivalent substitute.

## 2. Clone and create a Python environment

PowerShell:

```powershell
git clone <repository-url>
Set-Location <repository-directory>
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

POSIX shell:

```bash
git clone <repository-url>
cd <repository-directory>
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the environment check:

```powershell
& .\scripts\check-environment.ps1
```

## 3. Optional controller toolchain

For native tests, install Go 1.24.6. Docker can build both Go components without
a host Go installation because their Dockerfiles pin the builder and runtime
images by digest.

```powershell
docker build -t forecast-error-study/benchmark-app:0.1.0 .\app
docker build -t forecast-error-study/predictive-autoscaler:1.1.2 .\controller
```

## 4. Optional local Kubernetes toolchain

The documented local example was prepared with:

- Docker Engine/Desktop 29.1.3;
- kind 0.32.0;
- kind node image `kindest/node:v1.34.0`;
- kubectl 1.34.1;
- Helm 4.2.3;
- kube-prometheus-stack chart 88.0.1.

The study’s exact versions remain recorded in `versions.lock.yml`. Minor client
version differences are usually acceptable for functional reproduction, but
must be reported in any direct replication.

## 5. Credentials and paths

No password, token, private key, kubeconfig, public IP, or user-specific path is
stored in this repository. Cloud runner parameters must be supplied explicitly.
Never commit credentials; `.gitignore` excludes common credential filenames.

Before any cluster-changing command, inspect the active context:

```powershell
kubectl config current-context
kubectl cluster-info
```
