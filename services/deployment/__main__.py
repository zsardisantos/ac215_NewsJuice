"""
NewsJuice Infrastructure - Multi-Service Deployment with Scheduler
===================================================================
Deploys: Loader + Scraper + Chatter + Frontend to Cloud Run + GKE
Includes: Cloud Scheduler for automated daily triggers
Includes: HTTPS Ingress with managed certificate
Includes: WebSocket support via BackendConfig
===================================================================
"""

import pulumi
import pulumi_gcp as gcp
import pulumi_docker_build as docker_build
import pulumi_kubernetes as k8s
from pulumi import Output
import subprocess

# Configuration
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
region = gcp_config.get("region") or "us-central1"
zone = gcp_config.get("zone") or "us-central1-a"

# Database configuration
db_instance_name = config.get("db_instance_name") or "newsjuice-db-instance"
db_name = config.get("db_name") or "newsjuice"
db_user = config.get("db_user") or "newsjuice_app"
db_password = config.require_secret("db_password")

# Deployment options
enable_cloudrun = config.get_bool("enable_cloudrun") or True
enable_gke = config.get_bool("enable_gke") or False
gke_node_count = config.get_int("gke_node_count") or 2
gke_machine_type = config.get("gke_machine_type") or "e2-standard-2"

# ============================================================================
# SERVICES CONFIGURATION - Define all services here
# ============================================================================
SERVICES = [
    {
        "name": "loader",
        "display_name": "NewsJuice Loader",
        "source_dir": "/loader_deployed",
        "extra_envs": [],
    },
    {
        "name": "scraper",
        "display_name": "NewsJuice Scraper",
        "source_dir": "/scraper_deployed",
        "extra_envs": [],
    },
    {
        "name": "chatter",
        "display_name": "NewsJuice Chatter",
        "source_dir": "/chatter_deployed",
        "extra_envs": [
            ("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://34.28.40.119,https://www.newsjuiceapp.com,https://newsjuiceapp.com"),
            ("AUDIO_BUCKET", "newsjuice-123456-audio-bucket"),
            ("GCS_PREFIX", "podcasts/"),
            ("GOOGLE_API_KEY", "AIzaSyA3rhw0aA-NvMtnG3F6Ivv5UIdYZdUhc1I"),
        ],
    },
    {
        "name": "frontend",
        "display_name": "NewsJuice Frontend",
        "source_dir": "/frontend",
        "extra_envs": [],
    },
]

# ============================================================================
# HELPER FUNCTION FOR DOCKER AUTHENTICATION
# ============================================================================

def get_gcloud_access_token():
    """Get gcloud access token for Docker authentication"""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        pulumi.log.warn(f"Failed to get gcloud token: {e}")
        return None

# ============================================================================
# ARTIFACT REGISTRY REPOSITORY
# ============================================================================

artifact_repo = gcp.artifactregistry.Repository(
    "newsjuice-repo",
    repository_id="newsjuice",
    location=region,
    format="DOCKER",
    description="NewsJuice container images",
)

# ============================================================================
# SHARED SERVICE ACCOUNT FOR ALL SERVICES
# ============================================================================

service_account = gcp.serviceaccount.Account(
    "newsjuice-sa",
    account_id="newsjuice-services-sa",
    display_name="NewsJuice Services Service Account",
)

sql_client_binding = gcp.projects.IAMMember(
    "sql-client",
    project=project,
    role="roles/cloudsql.client",
    member=service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

storage_admin_binding = gcp.projects.IAMMember(
    "storage-admin",
    project=project,
    role="roles/storage.objectAdmin",
    member=service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

vertex_user_binding = gcp.projects.IAMMember(
    "vertex-user",
    project=project,
    role="roles/aiplatform.user",
    member=service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

# ============================================================================
# AUDIO BUCKET PUBLIC ACCESS
# ============================================================================

audio_bucket = gcp.storage.Bucket(
    "audio-bucket",
    name=f"{project}-audio-bucket",
    location=region,
    uniform_bucket_level_access=True,
    force_destroy=False,
    opts=pulumi.ResourceOptions(
        retain_on_delete=True
    ),
)

audio_bucket_public = gcp.storage.BucketIAMMember(
    "audio-bucket-public",
    bucket=audio_bucket.name,
    role="roles/storage.objectViewer",
    member="allUsers",
)

# ============================================================================
# BUILD DOCKER IMAGES FOR ALL SERVICES
# ============================================================================

docker_registry_address = f"{region}-docker.pkg.dev"
docker_access_token = get_gcloud_access_token()

service_images = {}

for service in SERVICES:
    service_images[service["name"]] = docker_build.Image(
        f"{service['name']}-image",
        context=docker_build.BuildContextArgs(
            location=service["source_dir"],
        ),
        dockerfile=docker_build.DockerfileArgs(
            location=f"{service['source_dir']}/Dockerfile",
        ),
        push=True,
        tags=[pulumi.Output.concat(
            region,
            "-docker.pkg.dev/",
            project,
            f"/newsjuice/{service['name']}:latest"
        )],
        platforms=[docker_build.Platform.LINUX_AMD64],
        registries=[
            docker_build.RegistryArgs(
                address=docker_registry_address,
                username="oauth2accesstoken",
                password=pulumi.Output.secret(docker_access_token) if docker_access_token else None,
            )
        ] if docker_access_token else None,
        opts=pulumi.ResourceOptions(
            depends_on=[artifact_repo]
        ),
    )

# ============================================================================
# DEPLOY ALL SERVICES TO CLOUD RUN
# ============================================================================

connection_name = f"{project}:{region}:{db_instance_name}"
cloudrun_services = {}

if enable_cloudrun:
    for service in SERVICES:
        cloudrun_services[service["name"]] = gcp.cloudrun.Service(
            f"{service['name']}-cloudrun",
            name=f"newsjuice-{service['name']}",
            location=region,
            template=gcp.cloudrun.ServiceTemplateArgs(
                spec=gcp.cloudrun.ServiceTemplateSpecArgs(
                    service_account_name=service_account.email,
                    containers=[
                        gcp.cloudrun.ServiceTemplateSpecContainerArgs(
                            image=service_images[service["name"]].ref,
                            ports=[gcp.cloudrun.ServiceTemplateSpecContainerPortArgs(
                                container_port=8080,
                            )],
                            resources=gcp.cloudrun.ServiceTemplateSpecContainerResourcesArgs(
                                limits={
                                    "cpu": "2000m",
                                    "memory": "2Gi",
                                },
                            ),
                            envs=[
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="DB_HOST",
                                    value=f"/cloudsql/{connection_name}",
                                ),
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="DB_NAME",
                                    value=db_name,
                                ),
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="DB_USER",
                                    value=db_user,
                                ),
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="DB_PASSWORD",
                                    value=db_password,
                                ),
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="DB_PORT",
                                    value="5432",
                                ),
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="DATABASE_URL",
                                    value=Output.all(db_user, db_password, db_name).apply(
                                        lambda args: f"postgresql://{args[0]}:{args[1]}@/{args[2]}?host=/cloudsql/{connection_name}"
                                    ),
                                ),
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="GCP_PROJECT",
                                    value=project,
                                ),
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="GCP_REGION",
                                    value=region,
                                ),
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name="GOOGLE_CLOUD_PROJECT",
                                    value=project,
                                ),
                            ] + [
                                gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                    name=env_name,
                                    value=env_value,
                                ) for env_name, env_value in service.get("extra_envs", [])
                            ],
                        )
                    ],
                ),
                metadata=gcp.cloudrun.ServiceTemplateMetadataArgs(
                    annotations={
                        "run.googleapis.com/cloudsql-instances": connection_name,
                        "autoscaling.knative.dev/maxScale": "5",
                        "autoscaling.knative.dev/minScale": "0",
                    },
                ),
            ),
            traffics=[gcp.cloudrun.ServiceTrafficArgs(
                percent=100,
                latest_revision=True,
            )],
            opts=pulumi.ResourceOptions(
                depends_on=[sql_client_binding, storage_admin_binding, vertex_user_binding, service_images[service["name"]]]
            ),
        )

        gcp.cloudrun.IamMember(
            f"{service['name']}-invoker",
            service=cloudrun_services[service["name"]].name,
            location=region,
            role="roles/run.invoker",
            member="allUsers",
        )

# ============================================================================
# CLOUD SCHEDULER - Trigger services on a schedule
# ============================================================================

if enable_cloudrun:
    scheduler_sa = gcp.serviceaccount.Account(
        "scheduler-sa",
        account_id="newsjuice-scheduler-sa",
        display_name="NewsJuice Scheduler Service Account",
    )

    for service in SERVICES:
        gcp.cloudrun.IamMember(
            f"{service['name']}-scheduler-invoker",
            service=cloudrun_services[service["name"]].name,
            location=region,
            role="roles/run.invoker",
            member=scheduler_sa.email.apply(lambda email: f"serviceAccount:{email}"),
        )

    scraper_scheduler = gcp.cloudscheduler.Job(
        "scraper-scheduler",
        name="newsjuice-scraper-daily",
        description="Trigger scraper daily at 6 AM UTC",
        schedule="0 6 * * *",
        time_zone="UTC",
        http_target=gcp.cloudscheduler.JobHttpTargetArgs(
            uri=cloudrun_services["scraper"].statuses[0].url.apply(
                lambda url: f"{url}/process"
            ),
            http_method="POST",
            oidc_token=gcp.cloudscheduler.JobHttpTargetOidcTokenArgs(
                service_account_email=scheduler_sa.email,
            ),
        ),
        opts=pulumi.ResourceOptions(
            depends_on=[cloudrun_services["scraper"]]
        ),
    )

    loader_scheduler = gcp.cloudscheduler.Job(
        "loader-scheduler",
        name="newsjuice-loader-daily",
        description="Trigger loader daily at 7 AM UTC (after scraper)",
        schedule="0 7 * * *",
        time_zone="UTC",
        http_target=gcp.cloudscheduler.JobHttpTargetArgs(
            uri=cloudrun_services["loader"].statuses[0].url.apply(
                lambda url: f"{url}/process"
            ),
            http_method="POST",
            oidc_token=gcp.cloudscheduler.JobHttpTargetOidcTokenArgs(
                service_account_email=scheduler_sa.email,
            ),
        ),
        opts=pulumi.ResourceOptions(
            depends_on=[cloudrun_services["loader"]]
        ),
    )

# ============================================================================
# GKE CLUSTER + KUBERNETES DEPLOYMENT
# ============================================================================

gke_cluster = None
node_pool = None
k8s_provider = None
k8s_namespace = None
k8s_deployments = {}
k8s_services = {}

if enable_gke:
    gke_sa = gcp.serviceaccount.Account(
        "gke-node-sa",
        account_id="newsjuice-gke-nodes",
        display_name="NewsJuice GKE Node Service Account",
    )

    gke_storage_binding = gcp.projects.IAMMember(
        "gke-storage-reader",
        project=project,
        role="roles/storage.objectViewer",
        member=gke_sa.email.apply(lambda email: f"serviceAccount:{email}"),
    )

    gke_logs_binding = gcp.projects.IAMMember(
        "gke-logs-writer",
        project=project,
        role="roles/logging.logWriter",
        member=gke_sa.email.apply(lambda email: f"serviceAccount:{email}"),
    )

    gke_metrics_binding = gcp.projects.IAMMember(
        "gke-metrics-writer",
        project=project,
        role="roles/monitoring.metricWriter",
        member=gke_sa.email.apply(lambda email: f"serviceAccount:{email}"),
    )

    gke_sql_binding = gcp.projects.IAMMember(
        "gke-sql-client",
        project=project,
        role="roles/cloudsql.client",
        member=gke_sa.email.apply(lambda email: f"serviceAccount:{email}"),
    )

    gke_artifact_binding = gcp.projects.IAMMember(
        "gke-artifact-reader",
        project=project,
        role="roles/artifactregistry.reader",
        member=gke_sa.email.apply(lambda email: f"serviceAccount:{email}"),
    )

    gke_cluster = gcp.container.Cluster(
        "newsjuice-cluster",
        name="newsjuice-cluster",
        location=zone,
        initial_node_count=1,
        remove_default_node_pool=True,
        deletion_protection=False,
        workload_identity_config=gcp.container.ClusterWorkloadIdentityConfigArgs(
            workload_pool=f"{project}.svc.id.goog",
        ),
    )

    node_pool = gcp.container.NodePool(
        "newsjuice-node-pool",
        name="newsjuice-pool",
        location=zone,
        cluster=gke_cluster.name,
        node_count=gke_node_count,
        node_config=gcp.container.NodePoolNodeConfigArgs(
            machine_type=gke_machine_type,
            service_account=gke_sa.email,
            oauth_scopes=[
                "https://www.googleapis.com/auth/cloud-platform",
            ],
            workload_metadata_config=gcp.container.NodePoolNodeConfigWorkloadMetadataConfigArgs(
                mode="GKE_METADATA",
            ),
        ),
        opts=pulumi.ResourceOptions(
            depends_on=[
                gke_storage_binding,
                gke_logs_binding,
                gke_metrics_binding,
                gke_sql_binding,
                gke_artifact_binding,
            ]
        ),
    )

    workload_identity_binding = gcp.serviceaccount.IAMBinding(
        "workload-identity-binding",
        service_account_id=service_account.name,
        role="roles/iam.workloadIdentityUser",
        members=[
            f"serviceAccount:{project}.svc.id.goog[newsjuice/newsjuice-services-sa]"
        ],
        opts=pulumi.ResourceOptions(
            depends_on=[service_account, gke_cluster]
        ),
    )

    k8s_provider = k8s.Provider(
        "gke-k8s",
        enable_server_side_apply=True,
        opts=pulumi.ResourceOptions(
            depends_on=[node_pool]
        ),
    )

    k8s_namespace = k8s.core.v1.Namespace(
        "newsjuice-namespace",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="newsjuice",
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[k8s_provider]
        ),
    )

    k8s_secret = k8s.core.v1.Secret(
        "db-credentials",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="db-credentials",
            namespace="newsjuice",
        ),
        string_data={
            "DB_PASSWORD": db_password,
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[k8s_namespace]
        ),
    )

    k8s_service_account = k8s.core.v1.ServiceAccount(
        "services-k8s-sa",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="newsjuice-services-sa",
            namespace="newsjuice",
            annotations={
                "iam.gke.io/gcp-service-account": service_account.email,
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[k8s_namespace, workload_identity_binding]
        ),
    )

    # Deploy all services to Kubernetes
    for service in SERVICES:
        k8s_deployments[service["name"]] = k8s.apps.v1.Deployment(
            f"{service['name']}-deployment",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name=f"newsjuice-{service['name']}",
                namespace="newsjuice",
            ),
            spec=k8s.apps.v1.DeploymentSpecArgs(
                replicas=2,
                selector=k8s.meta.v1.LabelSelectorArgs(
                    match_labels={"app": f"newsjuice-{service['name']}"},
                ),
                template=k8s.core.v1.PodTemplateSpecArgs(
                    metadata=k8s.meta.v1.ObjectMetaArgs(
                        labels={"app": f"newsjuice-{service['name']}"},
                    ),
                    spec=k8s.core.v1.PodSpecArgs(
                        service_account_name="newsjuice-services-sa",
                        containers=[
                            k8s.core.v1.ContainerArgs(
                                name=service["name"],
                                image=service_images[service["name"]].ref,
                                ports=[k8s.core.v1.ContainerPortArgs(container_port=8080)],
                                env=[
                                    k8s.core.v1.EnvVarArgs(name="DB_HOST", value="127.0.0.1"),
                                    k8s.core.v1.EnvVarArgs(name="DB_NAME", value=db_name),
                                    k8s.core.v1.EnvVarArgs(name="DB_USER", value=db_user),
                                    k8s.core.v1.EnvVarArgs(
                                        name="DB_PASSWORD",
                                        value_from=k8s.core.v1.EnvVarSourceArgs(
                                            secret_key_ref=k8s.core.v1.SecretKeySelectorArgs(
                                                name="db-credentials",
                                                key="DB_PASSWORD",
                                            ),
                                        ),
                                    ),
                                    k8s.core.v1.EnvVarArgs(name="DB_PORT", value="5432"),
                                    k8s.core.v1.EnvVarArgs(
                                        name="DATABASE_URL",
                                        value=Output.all(db_user, db_password, db_name).apply(
                                            lambda args: f"postgresql://{args[0]}:{args[1]}@127.0.0.1:5432/{args[2]}"
                                        ),
                                    ),
                                    k8s.core.v1.EnvVarArgs(name="GCP_PROJECT", value=project),
                                    k8s.core.v1.EnvVarArgs(name="GCP_REGION", value=region),
                                    k8s.core.v1.EnvVarArgs(name="GOOGLE_CLOUD_PROJECT", value=project),
                                    k8s.core.v1.EnvVarArgs(name="GOOGLE_CLOUD_REGION", value=region),
                                ] + [
                                    k8s.core.v1.EnvVarArgs(name=env_name, value=env_value)
                                    for env_name, env_value in service.get("extra_envs", [])
                                ],
                                resources=k8s.core.v1.ResourceRequirementsArgs(
                                    requests={"memory": "512Mi", "cpu": "250m"},
                                    limits={"memory": "1Gi", "cpu": "500m"},
                                ),
                            ),
                            k8s.core.v1.ContainerArgs(
                                name="cloud-sql-proxy",
                                image="gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.8.0",
                                args=[
                                    "--structured-logs",
                                    "--port=5432",
                                    connection_name,
                                ],
                                security_context=k8s.core.v1.SecurityContextArgs(
                                    run_as_non_root=True,
                                ),
                                resources=k8s.core.v1.ResourceRequirementsArgs(
                                    requests={"memory": "64Mi", "cpu": "50m"},
                                ),
                            ),
                        ],
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(
                provider=k8s_provider,
                depends_on=[k8s_service_account, k8s_secret, service_images[service["name"]]]
            ),
        )

        # Create LoadBalancer service for each service
        k8s_services[service["name"]] = k8s.core.v1.Service(
            f"{service['name']}-k8s-service",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name=f"{service['name']}-service",
                namespace="newsjuice",
                annotations={
                    "cloud.google.com/backend-config": '{"default": "websocket-config"}'
                } if service["name"] == "chatter" else {},
            ),
            spec=k8s.core.v1.ServiceSpecArgs(
                type="LoadBalancer",
                selector={"app": f"newsjuice-{service['name']}"},
                ports=[
                    k8s.core.v1.ServicePortArgs(
                        port=80,
                        target_port=8080,
                    ),
                ],
            ),
            opts=pulumi.ResourceOptions(
                provider=k8s_provider,
                depends_on=[k8s_deployments[service["name"]]]
            ),
        )

# ============================================================================
# HTTPS INGRESS WITH MANAGED CERTIFICATE
# ============================================================================

if enable_gke:
    # Backend config for WebSocket support
    backend_config = k8s.apiextensions.CustomResource(
        "chatter-websocket-config",
        api_version="cloud.google.com/v1",
        kind="BackendConfig",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="websocket-config",
            namespace="newsjuice",
        ),
        spec={
            "timeoutSec": 3600,
            "connectionDraining": {
                "drainingTimeoutSec": 60,
            },
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[k8s_namespace]
        ),
    )

    managed_cert = k8s.apiextensions.CustomResource(
        "managed-cert",
        api_version="networking.gke.io/v1",
        kind="ManagedCertificate",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="newsjuice-cert",
            namespace="newsjuice",
        ),
        spec={
            "domains": ["www.newsjuiceapp.com"],
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[k8s_namespace]
        ),
    )

    ingress = k8s.networking.v1.Ingress(
        "newsjuice-ingress",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="newsjuice-ingress",
            namespace="newsjuice",
            annotations={
                "kubernetes.io/ingress.global-static-ip-name": "newsjuice-ip",
                "networking.gke.io/managed-certificates": "newsjuice-cert",
                "kubernetes.io/ingress.class": "gce",
            },
        ),
        spec=k8s.networking.v1.IngressSpecArgs(
            rules=[
                k8s.networking.v1.IngressRuleArgs(
                    host="www.newsjuiceapp.com",
                    http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                        paths=[
                            k8s.networking.v1.HTTPIngressPathArgs(
                                path="/api/*",
                                path_type="ImplementationSpecific",
                                backend=k8s.networking.v1.IngressBackendArgs(
                                    service=k8s.networking.v1.IngressServiceBackendArgs(
                                        name="chatter-service",
                                        port=k8s.networking.v1.ServiceBackendPortArgs(number=80),
                                    ),
                                ),
                            ),
                            k8s.networking.v1.HTTPIngressPathArgs(
                                path="/ws/*",
                                path_type="ImplementationSpecific",
                                backend=k8s.networking.v1.IngressBackendArgs(
                                    service=k8s.networking.v1.IngressServiceBackendArgs(
                                        name="chatter-service",
                                        port=k8s.networking.v1.ServiceBackendPortArgs(number=80),
                                    ),
                                ),
                            ),
                            k8s.networking.v1.HTTPIngressPathArgs(
                                path="/*",
                                path_type="ImplementationSpecific",
                                backend=k8s.networking.v1.IngressBackendArgs(
                                    service=k8s.networking.v1.IngressServiceBackendArgs(
                                        name="frontend-service",
                                        port=k8s.networking.v1.ServiceBackendPortArgs(number=80),
                                    ),
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[managed_cert, backend_config]
        ),
    )

    pulumi.export("ingress_url", "https://www.newsjuiceapp.com")

# ============================================================================
# EXPORTS
# ============================================================================

pulumi.export("artifact_repo", artifact_repo.name)
pulumi.export("connection_name", connection_name)
pulumi.export("database_url_format", f"postgresql://USER:PASSWORD@/DATABASE?host=/cloudsql/{connection_name}")

for service in SERVICES:
    pulumi.export(f"{service['name']}_image", service_images[service["name"]].ref)

if enable_cloudrun:
    pulumi.export("cloudrun_enabled", True)
    for service in SERVICES:
        pulumi.export(
            f"cloudrun_{service['name']}_url",
            cloudrun_services[service["name"]].statuses[0].url
        )
    pulumi.export("scraper_schedule", "Daily at 6 AM UTC")
    pulumi.export("loader_schedule", "Daily at 7 AM UTC")
else:
    pulumi.export("cloudrun_enabled", False)

if enable_gke and gke_cluster:
    pulumi.export("gke_enabled", True)
    pulumi.export("gke_cluster_name", gke_cluster.name)
    pulumi.export("gke_cluster_endpoint", gke_cluster.endpoint)
    pulumi.export("gke_zone", zone)
    pulumi.export("gke_setup_command", f"gcloud container clusters get-credentials newsjuice-cluster --zone={zone} --project={project}")
    
    for service in SERVICES:
        pulumi.export(
            f"gke_{service['name']}_url",
            k8s_services[service["name"]].status.apply(
                lambda status: f"http://{status.load_balancer.ingress[0].ip}" if status and status.load_balancer and status.load_balancer.ingress else "pending"
            )
        )
else:
    pulumi.export("gke_enabled", False)

pulumi.export("deployment_summary", Output.all(enable_cloudrun, enable_gke).apply(
    lambda args: f"Cloud Run: {'✅ Enabled' if args[0] else '❌ Disabled'}, GKE: {'✅ Enabled' if args[1] else '❌ Disabled'} | Services: {', '.join([s['name'] for s in SERVICES])}"
))