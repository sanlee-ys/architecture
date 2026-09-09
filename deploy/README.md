# Local deploy

Operate the three services on one machine. This is not a public cloud deploy.
The host binds loopback only. The SYS-010 trust model does not change.
Do not add Ingress to the public internet.

The classifier Dockerfile is on `defense-news-classifier` main.
`notes-api` and `kb-agent` Dockerfiles land in those repos. Compose fails
to build a service until that Dockerfile exists.

## 1. Clone the app repos as siblings

The parent directory is the folder that holds `architecture/`.

```bash
git clone https://github.com/sanlee-ys/notes-api.git
git clone https://github.com/sanlee-ys/defense-news-classifier.git
git clone https://github.com/sanlee-ys/kb-agent.git
```

The kb-agent clone is optional. You need it only for `--profile agent`.

Confirm the layout:

```bash
ls ../notes-api ../defense-news-classifier
```

## 2. Set the API key

Copy the example env file. Then put your key in `.env`. Do not commit `.env`.

```bash
cp .env.example .env
```

Edit `.env` and set `ANTHROPIC_API_KEY`. Then start the two required services:

```bash
docker compose up --build
```

Run that command from this `deploy/` directory so Compose reads `.env`.

## 3. Hit /health

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8081/health
```

Each response is `{"status":"ok"}`. Host ports bind `127.0.0.1` only.

notes-api stores SQLite in the `notes-data` volume. It calls
`http://classifier:8080` for enrichment.

## 4. Optional kb-agent

```bash
docker compose --profile agent up --build
```

Then:

```bash
curl -sS http://127.0.0.1:7860/health
```

The image must serve `GET /health` on port 7860. Point `projects.yaml`
endpoints at `http://classifier:8080` and `http://notes-api:8081` inside
the container. Compose sets `KB_ALLOWED_HOSTS=classifier,notes-api` so
the SSRF guard accepts those Docker DNS names.

## 5. Load kind (or k3d)

Create a local cluster:

```bash
kind create cluster --name local-system
```

Build the two required images, then load them into kind:

```bash
docker compose build
kind load docker-image notes-api:local --name local-system
kind load docker-image classifier:local --name local-system
```

Create the namespace and the key Secret. Do not commit a real key.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl -n local-system create secret generic classifier \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
```

Apply the manifests. There is no Ingress object.

```bash
kubectl apply -k k8s
```

Forward ClusterIP services to loopback:

```bash
kubectl -n local-system port-forward svc/classifier 8080:8080
```

In a second terminal:

```bash
kubectl -n local-system port-forward svc/notes-api 8081:8081
```

Then repeat the `/health` curls from step 3.

k3d uses the same manifests. Load images with `k3d image import` instead
of `kind load docker-image`.

## What this is not

Pods listen on `0.0.0.0` inside the cluster network so kube-proxy can
reach them. Access from the host is `kubectl port-forward` to `127.0.0.1`.
That is still local. It is not a production SaaS.
