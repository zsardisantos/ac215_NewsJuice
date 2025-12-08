# NewsJuice Deployment Guide

Please find a detailed Deployment Architecture diagam below.

The NewsJuice app is now fully deployed via pulumi and on GKE (kubernetes) and up and running.

Final URLs:

Production: https://www.newsjuiceapp.com ✅  
GKE Frontend: http://34.28.40.119  
GKE Chatter: http://136.113.170.71  

Features working:

✅ User registration/login (Firebase Auth)  
✅ Preferences saving  
✅ Daily Brief generation & playback  
✅ Microphone/voice Q&A  
✅ SSL certificate (Google-managed, auto-renews)  

Infrastructure:

✅ GKE cluster with Ingress
✅ Cloud SQL
✅ Pulumi IaC (fully repeatable)


## Prerequisites

- Docker installed locally  
- GCP project with billing enabled (newsjuice-123456)  
- Service account key (`deployment.json` in **secrets** folder in the parent folder of the app) with permissions:  
  - Cloud Run Admin  
  - Kubernetes Engine Admin  
  - Cloud SQL Admin  
  - Artifact Registry Admin  
  - Service Account Admin  
  - IAM Admin  

## Directory Structure

```
services/
├── deployment/
│   ├── __main__.py           # Pulumi infrastructure code
│   ├── Pulumi.yaml           # Pulumi project config
│   ├── Pulumi.dev.yaml       # Environment config (secrets)
│   ├── pyproject.toml        # Python dependencies for Pulumi
│   ├── Dockerfile            # Deployment container
│   ├── docker-shell.sh       # Start deployment container
│   └── docker-entrypoint.sh  # Container setup script
├── loader_deployed/          # Loader service code
│   ├── main.py               # FastAPI app
│   ├── Dockerfile            # Loader container image
│   ├── pyproject.toml        # Python dependencies
│   └── ...
├── scraper_deployed/         # Scraper service code
│   ├── main.py               # FastAPI app
│   ├── Dockerfile            # Scraper container image
│   ├── pyproject.toml        # Python dependencies
│   └── ...
├── chatter_deployed/         # Chatter service code (API + WebSocket)
│   ├── main.py               # FastAPI app + WebSocket handlers
│   ├── Dockerfile            # Chatter container image
│   ├── pyproject.toml        # Python dependencies
│   └── ...
└── frontend/                 # Frontend React app
    ├── src/
    │   ├── pages/
    │   │   └── Podcast.jsx   # WebSocket connection (⚠️ hardcoded URL to fix)
    │   └── ...
    ├── Dockerfile            # Nginx + React build
    ├── nginx.conf            # Nginx config (listen :8080)
    ├── package.json          # Node dependencies
    └── ...
```

## Quick Start

### 1. Configure Secrets

Create `Pulumi.dev.yaml` in `services/deployment/`:

```yaml
config:
  gcp:project: YOUR-PROJECT-ID
  gcp:region: us-central1
  gcp:zone: us-central1-a
  newsjuice-loader:db_instance_name: newsdb-instance
  newsjuice-loader:db_name: newsdb
  newsjuice-loader:db_user: postgres
  newsjuice-loader:db_password:
    secure: YOUR-ENCRYPTED-PASSWORD
  newsjuice-loader:enable_cloudrun: true
  newsjuice-loader:enable_gke: true
  newsjuice-loader:gke_node_count: 2
  newsjuice-loader:gke_machine_type: e2-standard-2
```

To encrypt password (for GC SQL database):
```bash
pulumi config set --secret db_password YOUR_PASSWORD
```

### 2. Start Deployment Container

```bash
cd services/deployment
sh docker-shell.sh
```

### 3. Deploy Infrastructure

Inside container:
```bash
cd /app
pulumi up --yes
```

## Deployment Outputs

After successful deployment:

View all outputs:
```bash
pulumi stack output
```

## Common Commands

### Check Status 
```bash
# Cloud Run services
gcloud run services list --region=us-central1

# GKE pods
kubectl get pods -n newsjuice

# GKE services (get external IPs)
kubectl get svc -n newsjuice
```

### View Logs
```bash
# Cloud Run
gcloud run services logs read newsjuice-loader --region=us-central1 --limit=50

# GKE
kubectl logs -n newsjuice -l app=newsjuice-loader -c loader --tail=50
```

### Update Deployment
```bash
# After code changes, redeploy
pulumi up

# After aborts
pulumi refresh
pulumi up
```

### Destroy Infrastructure
```bash
pulumi destroy
```

## Troubleshooting

### Kubernetes cluster unreachable
```bash
gcloud container clusters get-credentials newsjuice-cluster \
    --zone=us-central1-a \
    --project=YOUR-PROJECT-ID
```

### Pulumi state out of sync
```bash
pulumi refresh
pulumi up
```

### Pods stuck in Pending
Check node resources:
```bash
kubectl describe pod POD-NAME -n newsjuice | grep -A 10 Events
```

If "Insufficient cpu", upgrade to larger nodes (`e2-standard-2` or higher).

### Container crash loops
Check logs:
```bash
kubectl logs POD-NAME -n newsjuice -c loader --tail=50
```

Common fixes:
- Missing environment variables (DATABASE_URL)
- Database connection issues
- Missing dependencies

## Cost Estimates

```
| Component                      | Monthly Cost |
|--------------------------------|--------------|
| GKE Cluster                    | ~$75         |
| GKE Nodes (2x e2-standard-2)   | ~$100        |
| Cloud SQL                      | ~$10-50      |
| Load Balancers (2)             | ~$40         |
| Artifact Registry              | ~$1-5        |
| Cloud Storage (audio)          | ~$1-5        |
| Vertex AI (embeddings)         | ~$5-20       |
| Firebase Auth                  | Free tier    |
| **Total (GKE)**                | **~$230-295**|
```

## Adding New Services

Edit `SERVICES` list in `__main__.py`:

```python
SERVICES = [
    {"name": "loader", "display_name": "NewsJuice Loader", "source_dir": "/loader_deployed"},
    {"name": "scraper", "display_name": "NewsJuice Scraper", "source_dir": "/scraper_deployed"},
    {"name": "newservice", "display_name": "New Service", "source_dir": "/newservice_deployed"},
]
```

Add volume mount in `docker-shell.sh`:
```bash
-v "$BASE_DIR/../newservice_deployed":/newservice_deployed \
```

Run `pulumi up` to deploy.


To get into the deplyment container:

```bash
docker exec -it newsjuice-app-deployment bash
```

## Winding down everthing:

Inside your deployment container:

1. Destroy all Pulumi-managed infrastructure
```bash
cd /app
pulumi destroy
```
Type yes to confirm. This deletes:  

✅ GKE cluster + nodes + pods  
✅ Load balancers  
✅ Service accounts + IAM bindings  
✅ Artifact Registry images  
  
What stays (not managed by Pulumi):  

* Cloud SQL database (~$10-50/month)  
* Pulumi state bucket  

Start Fresh Deployment  
After destroying:  

### Exit container
```bash
exit
```

### Restart container
```bash
./docker-shell.sh
```

### Inside container
```bash
cd /app
pulumi up
```

### Test schduler manually
```bash
gcloud scheduler jobs run newsjuice-scraper-daily --location=us-central1
gcloud scheduler jobs run newsjuice-loader-daily --location=us-central1
```

### Check logs
```bash
gcloud run services logs read newsjuice-scraper --region=us-central1 --limit=20
gcloud run services logs read newsjuice-loader --region=us-central1 --limit=20
```


## HTTPS setup

1. Obtain domain name (e.g. www.domain.com)  
2. Reserve a static IP
```bash
gcloud compute addresses create newsjuice-ip --global
```
Check status (provisioning/active)  
```bash
kubectl describe managedcertificate newsjuice-cert -n newsjuice | grep Status
```
3. Configure DNS at domain registrar  
* type = a  
* name = wwww  
* value = 136.110.164.121 (NewsJuice static IP)  

4. Include managed certificate in pulumi __main__  
5. INnress with SSL in pulumi __main__  


## Quick Verification Checklist
**HTTPS**

 Static IP reserved  
 DNS A record configured  
 Certificate status is Active  
 https://www.newsjuiceapp.com loads without warnings  

**Firebase Auth**  
  
 Firebase project created  
 Google Sign-in enabled  
 Authorized domains added  
 Frontend Firebase SDK configured  
 Backend JWT validation working  
 GKE service account has Firebase Admin role  


# Exploring Kubernetes deployment

### Pods

```bash
root@e0d820fde2c9:/app# kubectl get pods -n newsjuice
NAME                                  READY   STATUS    RESTARTS   AGE
newsjuice-chatter-6fbcf5b8bd-d2v5f    2/2     Running   0          53m
newsjuice-chatter-6fbcf5b8bd-vrkhk    2/2     Running   0          53m
...
```
```bash
kubectl logs -n newsjuice <pod-name> -c <container-name>
```

### Deployment

```bash
root@e0d820fde2c9:/app# kubectl get deployments -n newsjuice
NAME                 READY   UP-TO-DATE   AVAILABLE   AGE
newsjuice-chatter    2/2     2            2           8h
...
```

### Services

```bash
kubectl get svc -n newsjuice
```

### Services
```bash
root@e0d820fde2c9:/app# kubectl get svc -n newsjuice
NAME               TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)        AGE
chatter-service    LoadBalancer   34.118.238.5     136.113.170.71   80:32185/TCP   8h
...
```

### Ingress
```bash
root@e0d820fde2c9:/app# kubectl get ingress -n newsjuice
NAME                CLASS    HOSTS                  ADDRESS           PORTS   AGE
newsjuice-ingress   <none>   www.newsjuiceapp.com   136.110.164.121   80      59m
```

### Certification
```bash
kubectl describe managedcertificate newsjuice-cert -n newsjuice
```

### Watch pods in real time
```bash
 kubectl get pods -n newsjuice -w
 ```

### All resources
```bash
kubectl get all -n newsjuice
```

### Testing CronJobs for scraper and loader

1. List CronJobs
```bash
kubectl get cronjobs -n newsjuice
```
2. List Jobs (created by CronJobs)
```bash
kubectl get jobs -n newsjuice
```
3. List Pods (created by Jobs)
```bash
kubectl get pods -n newsjuice
```
4. Manually trigger a test
```bash
kubectl create job --from=cronjob/newsjuice-scraper test-scraper3 -n newsjuice
```
5. Watch pods
```bash
kubectl get pods -n newsjuice -w
```
6. Check logs
```bash
kubectl logs -l job-name=test-scraper3 -n newsjuice -c scraper
```

## Deployment diagrams


```
Users
  │
  ▼
GKE Ingress (www.newsjuiceapp.com)
  │
  ├── /api/* ──→ Chatter (FastAPI + SQL Proxy) ──→ Cloud SQL
  ├── /ws/*  ──→ Chatter (WebSockets)          ──→ Cloud SQL
  └── /*     ──→ Frontend (Nginx + React)
  
CronJobs (scheduled, not always-on):
  ├── Scraper (6 AM UTC) ──→ Cloud SQL
  └── Loader  (7 AM UTC) ──→ Cloud SQL + Vertex AI
```

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              NEWSJUICE DEPLOYMENT ARCHITECTURE                          │
│                                  (with Firebase Auth)                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────┐
                                    │    USERS     │
                                    │   Browser    │
                                    └──────┬───────┘
                                           │
                         ┌─────────────────┼─────────────────┐
                         │                 │                 │
                         ▼                 │                 │
              ┌────────────────────┐       │                 │
              │   FIREBASE AUTH    │       │                 │
              │   (Google Cloud)   │       │                 │
              │                    │       │                 │
              │  - Google Sign-in  │       │                 │
              │  - Email/Password  │       │                 │
              │  - JWT Tokens      │       │                 │
              └─────────┬──────────┘       │                 │
                        │                  │                 │
                        │ JWT Token        │                 │
                        ▼                  │                 │
              ┌────────────────────┐       │                 │
              │  localStorage      │       │                 │
              │  (auth_token)      │───────┘                 │
              └────────────────────┘                         │
                                                             │
                                           │ HTTPS :443      │
                                           │ + JWT Token     │
                                           ▼                 │
                              ┌────────────────────────┐     │
                              │  www.newsjuiceapp.com  │     │
                              │     (DNS → GKE IP)     │     │
                              │    136.110.164.121     │     │
                              └────────────┬───────────┘     │
                                           │                 │
                                           ▼                 │
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                    GOOGLE KUBERNETES ENGINE                              │
│                                    (newsjuice-cluster)                                   │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              GKE INGRESS (GCE Load Balancer)                       │  │
│  │                         + Managed SSL Certificate (newsjuice-cert)                 │  │
│  │                                   :443 (HTTPS/WSS)                                 │  │
│  │  ┌──────────────────┬────────────────────────┬──────────────────────────────────┐  │  │
│  │  │    /api/*        │        /ws/*           │            /*                    │  │  │
│  │  │                  │    (WebSockets)        │                                  │  │  │
│  │  └────────┬─────────┴───────────┬────────────┴─────────────────┬────────────────┘  │  │
│  └───────────┼─────────────────────┼──────────────────────────────┼───────────────────┘  │
│              │                     │                              │                      │
│              ▼                     ▼                              ▼                      │
│  ┌─────────────────────────────────────────────┐    ┌─────────────────────────────────┐  │
│  │           CHATTER SERVICE :80               │    │      FRONTEND SERVICE :80       │  │
│  │           (LoadBalancer)                    │    │      (LoadBalancer)             │  │
│  │           + WebSocket BackendConfig         │    │                                 │  │
│  └─────────────────┬───────────────────────────┘    └───────────────────┬─────────────┘  │
│                    │                                                    │                │
│                    ▼                                                    ▼                │
│  ┌─────────────────────────────────────────────┐    ┌─────────────────────────────────┐  │
│  │         CHATTER DEPLOYMENT                  │    │     FRONTEND DEPLOYMENT         │  │
│  │         (2 replicas)                        │    │     (2 replicas)                │  │
│  │  ┌───────────────────────────────────────┐  │    │  ┌───────────────────────────┐  │  │
│  │  │ Pod :8080                             │  │    │  │ Pod :8080                 │  │  │
│  │  │ ┌─────────────┐  ┌─────────────────┐  │  │    │  │ ┌─────────────────────┐   │  │  │
│  │  │ │  FastAPI    │  │ Cloud SQL Proxy │  │  │    │  │ │   Nginx             │   │  │  │
│  │  │ │  Uvicorn    │  │   (sidecar)     │  │  │    │  │ │   Static files      │   │  │  │
│  │  │ │             │  │   :5432         │  │  │    │  │ │   React SPA         │   │  │  │
│  │  │ │ ┌─────────┐ │  └────────┬────────┘  │  │    │  │ │   + Firebase SDK    │   │  │  │
│  │  │ │ │Validates│ │           │           │  │    │  │ └─────────────────────┘   │  │  │
│  │  │ │ │JWT Token│ │           │           │  │    │  └───────────────────────────┘  │  │
│  │  │ │ └─────────┘ │           │           │  │    └─────────────────────────────────┘  │
│  │  │ └──────┬──────┘           │           │  │                                         │
│  │  └────────┼──────────────────┼───────────┘  │                                         │
│  └───────────┼──────────────────┼──────────────┘                                         │
│              │                  │                                                        │
│              │                  │ ┌─────────────────────────────────────────────────────┐│
│              │                  │ │              CRONJOBS (Scheduled)                   ││
│              │                  │ │                                                     ││
│              │                  │ │  ┌─────────────────────┐ ┌─────────────────────┐    ││
│              │                  │ │  │  SCRAPER CRONJOB    │ │  LOADER CRONJOB      │   ││
│              │                  │ │  │  Schedule: 6AM UTC  │ │  Schedule: 7AM UTC  │    ││
│              │                  │ │  │  Pod :8080          │ │  Pod :8080          │    ││
│              │                  │ │  │  + SQL Proxy :5432  │ │  + SQL Proxy :5432  │    ││
│              │                  │ │  └──────────┬──────────┘ └──────────┬──────────┘    ││
│              │                  │ └─────────────┼────────────────────────┼──────────────┘│
│              │                  │               │                        │               │
└──────────────┼──────────────────┼───────────────┼────────────────────────┼───────────────┘
               │                  │               │                        │
               │                  └───────────────┼────────────────────────┘
               │                                  │
               │                                  ▼
               │                  ┌─────────────────────────────────────┐
               │                  │         CLOUD SQL (PostgreSQL)      │
               │                  │         newsdb-instance :5432       │
               │                  │         + pgvector extension        │
               └──────────────────│                                     │
                                  │  ┌─────────────┐  ┌──────────────┐  │
                                  │  │  articles   │  │chunks_vector │  │
                                  │  │   table     │  │   table      │  │
                                  │  └─────────────┘  └──────────────┘  │
                                  └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   OTHER GCP SERVICES                                    │
│                                                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │  Artifact Registry  │  │   Cloud Storage     │  │       Vertex AI                 │  │
│  │  (Docker images)    │  │   (Audio bucket)    │  │   (Embeddings API)              │  │
│  │                     │  │   Podcast files     │  │   text-embedding-004            │  │
│  │  - loader:latest    │  │                     │  │                                 │  │
│  │  - scraper:latest   │  │                     │  │                                 │  │
│  │  - chatter:latest   │  │                     │  │                                 │  │
│  │  - frontend:latest  │  │                     │  │                                 │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              AUTHENTICATION FLOW                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  ┌────────┐      ┌──────────────┐      ┌──────────────┐      ┌─────────────┐
  │  User  │      │   Frontend   │      │ Firebase Auth│      │   Chatter   │
  └───┬────┘      └──────┬───────┘      └──────┬───────┘      └──────┬──────┘
      │                  │                     │                     │
      │  1. Click Login  │                     │                     │
      │─────────────────>│                     │                     │
      │                  │                     │                     │
      │                  │  2. Redirect to     │                     │
      │                  │     Firebase        │                     │
      │                  │────────────────────>│                     │
      │                  │                     │                     │
      │                  │  3. User signs in   │                     │
      │                  │     (Google/Email)  │                     │
      │<─────────────────────────────────────> │                     │
      │                  │                     │                     │
      │                  │  4. Return JWT      │                     │
      │                  │<────────────────────│                     │
      │                  │                     │                     │
      │                  │  5. Store token in  │                     │
      │                  │     localStorage    │                     │
      │                  │                     │                     │
      │  6. Connect WebSocket                  │                     │
      │     wss://...?token=JWT                │                     │
      │─────────────────────────────────────────────────────────────>│
      │                  │                     │                     │
      │                  │                     │  7. Validate JWT    │
      │                  │                     │<────────────────────│
      │                  │                     │────────────────────>│
      │                  │                     │                     │
      │  8. WebSocket connected (authenticated)│                     │
      │<─────────────────────────────────────────────────────────────│
      │                  │                     │                     │


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA FLOW                                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  1. SCRAPER (6 AM UTC)
     └─→ Fetches articles from Harvard news sources
     └─→ Stores raw articles in PostgreSQL (articles table)

  2. LOADER (7 AM UTC)
     └─→ Reads new articles from PostgreSQL
     └─→ Chunks text + generates embeddings via Vertex AI
     └─→ Stores vectors in PostgreSQL (chunks_vector table with pgvector)

  3. CHATTER (On-demand, authenticated)
     └─→ User connects via WebSocket with JWT token
     └─→ Backend validates token with Firebase
     └─→ User sends voice/text query
     └─→ Semantic search on chunks_vector (pgvector similarity)
     └─→ RAG: Retrieved context + LLM generates response
     └─→ TTS generates audio → stored in Cloud Storage
     └─→ Audio URL returned to user

  4. FRONTEND (Always-on)
     └─→ React SPA served by Nginx
     └─→ Firebase SDK handles authentication UI
     └─→ WebSocket connection to Chatter for real-time chat


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PORTS SUMMARY                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  | Component      | External Port | Internal Port |
  |----------------|---------------|---------------|
  | Ingress        | :443 (HTTPS)  | -             |
  | Services       | :80           | :8080         |
  | All containers | -             | :8080         |
  | SQL Proxy      | -             | :5432         |
  | Cloud SQL      | -             | :5432         |

```


```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              NEWSJUICE PORTS DIAGRAM                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘


                                    ┌──────────────┐
                                    │    USERS     │
                                    └──────┬───────┘
                                           │
                         ┌─────────────────┴─────────────────┐
                         │                                   │
                         ▼                                   │
              ┌────────────────────┐                         │
              │   FIREBASE AUTH    │                         │
              │   (Google Cloud)   │                         │
              │                    │                         │
              │   Returns JWT      │                         │
              └─────────┬──────────┘                         │
                        │                                    │
                        │ JWT Token                          │
                        ▼                                    │
              ┌────────────────────┐                         │
              │  localStorage      │                         │
              │  (auth_token)      │─────────────────────────┘
              └────────────────────┘
                                           │
                                           │ :443 (HTTPS/WSS + JWT)
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                GKE INGRESS                                               │
│                          (Google Cloud Load Balancer)                                    │
│                          + Managed SSL Certificate                                       │
│                                                                                          │
│   External IP: 136.110.164.121                                                           │
│   Listening:   :443 (HTTPS/WSS) ──→ SSL Termination                                      │
│                :80  (HTTP → redirects to HTTPS)                                          │
└────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          │ /api/*                   │ /ws/*                    │ /*
          │                          │                          │
          ▼                          ▼                          ▼
┌──────────────────────────────────────────────┐    ┌─────────────────────────────────────┐
│         CHATTER-SERVICE (K8s Service)        │    │   FRONTEND-SERVICE (K8s Service)   │
│         Type: LoadBalancer                   │    │   Type: LoadBalancer                │
│                                              │    │                                     │
│   External: :80  ───────┐                    │    │   External: :80  ───────┐           │
│                         │                    │    │                         │           │
│   targetPort: 8080 ◄────┘                    │    │   targetPort: 8080 ◄────┘           │
└──────────────────────────┬───────────────────┘    └───────────────────────┬─────────────┘
                           │                                                │
                           ▼                                                ▼
┌──────────────────────────────────────────────┐    ┌─────────────────────────────────────┐
│              CHATTER POD                     │    │          FRONTEND POD               │
│  ┌─────────────────────────────────────────┐ │    │  ┌───────────────────────────────┐  │
│  │          CHATTER CONTAINER              │ │    │  │      FRONTEND CONTAINER       │  │
│  │                                         │ │    │  │                               │  │
│  │   FastAPI + Uvicorn                     │ │    │  │   Nginx                       │  │
│  │   Listening: :8080                      │ │    │  │   Listening: :8080            │  │
│  │                                         │ │    │  │   (configured in nginx.conf)  │  │
│  │   ┌─────────────────────────────────┐   │ │    │  │                               │  │
│  │   │  JWT Validation (Firebase)      │   │ │    │  │   Serves:                     │  │
│  │   │  on /api/* and /ws/* requests   │   │ │    │  │   - Static React files        │  │
│  │   └─────────────────────────────────┘   │ │    │  │   - Firebase SDK              │  │
│  │                                         │ │    │  │   - SPA routing (/* → index)  │  │
│  │   Endpoints:                            │ │    │  │                               │  │
│  │   - POST /api/chat                      │ │    │  └───────────────────────────────┘  │
│  │   - WS   /ws/chat?token=JWT             │ │    │                                     │
│  │   - POST /process                       │ │    └─────────────────────────────────────┘
│  │   - GET  /health                        │ │
│  └────────────────────┬────────────────────┘ │
│                       │                      │
│                       │ localhost:5432       │
│                       ▼                      │
│  ┌─────────────────────────────────────────┐ │
│  │       CLOUD-SQL-PROXY CONTAINER         │ │
│  │       (sidecar)                         │ │
│  │                                         │ │
│  │   Listening: :5432                      │ │
│  │   Connects to Cloud SQL via IAM         │ │
│  └────────────────────┬────────────────────┘ │
└───────────────────────┼──────────────────────┘
                        │
                        │ :5432 (PostgreSQL protocol)
                        │ (via private Google network)
                        ▼
┌──────────────────────────────────────────────┐
│              CLOUD SQL                       │
│              (PostgreSQL + pgvector)         │
│                                              │
│   Instance: newsdb-instance                  │
│   Listening: :5432                           │
│   Database: newsjuice                        │
└──────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              CRONJOB PODS (Scheduled)                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐    ┌─────────────────────────────────────┐
│              SCRAPER POD                     │    │            LOADER POD               │
│              (Created at 6 AM UTC)           │    │            (Created at 7 AM UTC)    │
│  ┌─────────────────────────────────────────┐ │    │  ┌───────────────────────────────┐  │
│  │          SCRAPER CONTAINER              │ │    │  │       LOADER CONTAINER        │  │
│  │                                         │ │    │  │                               │  │
│  │   FastAPI + Uvicorn                     │ │    │  │   FastAPI + Uvicorn           │  │
│  │   Listening: :8080                      │ │    │  │   Listening: :8080            │  │
│  │                                         │ │    │  │                               │  │
│  │   Triggered by:                         │ │    │  │   Triggered by:               │  │
│  │   curl POST localhost:8080/process      │ │    │  │   curl POST localhost:8080/   │  │
│  │                                         │ │    │  │        process                │  │
│  │   Fetches articles from:                │ │    │  │                               │  │
│  │   - Harvard Gazette                     │ │    │  │   Calls:                      │  │
│  │   - Harvard Crimson                     │ │    │  │   - Vertex AI (embeddings)    │  │
│  │   - Harvard Magazine etc.               │ │    │  │                               │  │
│  └────────────────────┬────────────────────┘ │    │  └──────────────┬────────────────┘  │
│                       │                      │    │                 │                   │
│                       │ localhost:5432       │    │                 │ localhost:5432    │
│                       ▼                      │    │                 ▼                   │
│  ┌─────────────────────────────────────────┐ │    │  ┌───────────────────────────────┐  │
│  │       CLOUD-SQL-PROXY CONTAINER         │ │    │  │   CLOUD-SQL-PROXY CONTAINER   │  │
│  │       (sidecar)                         │ │    │  │   (sidecar)                   │  │
│  │       Listening: :5432                  │ │    │  │   Listening: :5432            │  │
│  └────────────────────┬────────────────────┘ │    │  └──────────────┬────────────────┘  │
└───────────────────────┼──────────────────────┘    └─────────────────┼───────────────────┘
                        │                                             │
                        └──────────────────┬──────────────────────────┘
                                           │
                                           │ :5432
                                           ▼
                              ┌────────────────────────┐
                              │       CLOUD SQL        │
                              │       :5432            │
                              └────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              PORTS SUMMARY TABLE                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  | Component        | External Port  | Internal Port | Notes                            |
  |------------------|----------------|---------------|----------------------------------|
  | Firebase Auth    | :443 (HTTPS)   | -             | Google-managed                   |
  | GKE Ingress      | :443/:80       | -             | SSL termination + routing        |
  | chatter-service  | :80            | :8080         | LoadBalancer → Pod               |
  | frontend-service | :80            | :8080         | LoadBalancer → Pod               |
  | Chatter container| -              | :8080         | FastAPI + JWT validation         |
  | Frontend container| -             | :8080         | Nginx + React + Firebase SDK     |
  | Scraper container| -              | :8080         | FastAPI (CronJob)                |
  | Loader container | -              | :8080         | FastAPI (CronJob)                |
  | Cloud SQL Proxy  | -              | :5432         | Sidecar in each pod              |
  | Cloud SQL        | -              | :5432         | PostgreSQL (private network)     |
  | Vertex AI        | :443 (HTTPS)   | -             | Google-managed API               |


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST FLOWS WITH PORTS                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

Authentication:
  User → Firebase :443 → JWT Token → localStorage

HTTPS API Request:
  User :443 + JWT → Ingress :443 → chatter-service :80 → chatter-pod :8080 (validate JWT) → SQL-proxy :5432 → CloudSQL :5432

WebSocket Connection:
  User :443 (wss + JWT) → Ingress :443 → chatter-service :80 → chatter-pod :8080 (validate JWT, upgrade to WS)

Static Files:
  User :443 → Ingress :443 → frontend-service :80 → frontend-pod :8080 (nginx)

CronJob Scraper (6 AM UTC):
  Scheduler → Create Pod → uvicorn :8080 & curl localhost:8080/process → SQL-proxy :5432 → CloudSQL :5432

CronJob Loader (7 AM UTC):
  Scheduler → Create Pod → uvicorn :8080 & curl localhost:8080/process → Vertex AI :443 + SQL-proxy :5432 → CloudSQL :5432
```

## Appendix 1 Firebase Authentication Setup


Firebase Console (console.firebase.google.com)

Create/select project → link to GCP project newsjuice-123456
Authentication → Sign-in method → Enable Google and/or Email/Password
Authentication → Settings → Authorized domains → Add www.newsjuiceapp.com
Project Overview → Add app → Web → Copy config

Frontend

npm install firebase
Create src/firebase.js with config + auth functions
Store JWT token: user.getIdToken() → localStorage.setItem('auth_token', token)
Pass token in WebSocket: wss://...?token=${token}

Backend (Chatter)

pip install firebase-admin
Initialize: firebase_admin.initialize_app() (uses GKE credentials)
Validate JWT: auth.verify_id_token(token)

GCP IAM

Grant roles/firebase.admin to GKE service account



## LOAD TEST

Terminal 1.
kubectl top pods -n newsjuice --use-protocol-buffers
Terminal 2.
k9s -n newsjuice
Terminal 3.
hey -z 60s -c 50 https://www.newsjuiceapp.com/api/health