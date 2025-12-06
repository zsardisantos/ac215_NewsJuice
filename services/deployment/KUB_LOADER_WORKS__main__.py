"""
NewsJuice Infrastructure - Cloud Run + Optional GKE
Fully automated: Infrastructure + Kubernetes deployments
Optimized for e2-standard-2 nodes (2 CPUs each)
FIXED: Added DATABASE_URL to Kubernetes deployment
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
gke_machine_type = config.get("gke_machine_type") or "e2-medium"

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
# SERVICE ACCOUNT & IAM
# ============================================================================

loader_service_account = gcp.serviceaccount.Account(
    "loader-sa",
    account_id="newsjuice-loader-sa",
    display_name="NewsJuice Loader Service Account",
)

sql_client_binding = gcp.projects.IAMMember(
    "loader-sql-client",
    project=project,
    role="roles/cloudsql.client",
    member=loader_service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

storage_admin_binding = gcp.projects.IAMMember(
    "loader-storage-admin",
    project=project,
    role="roles/storage.objectAdmin",
    member=loader_service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

vertex_user_binding = gcp.projects.IAMMember(
    "loader-vertex-user",
    project=project,
    role="roles/aiplatform.user",
    member=loader_service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

# ============================================================================
# BUILD AND PUSH DOCKER IMAGE
# ============================================================================

docker_registry_address = f"{region}-docker.pkg.dev"
docker_access_token = get_gcloud_access_token()

loader_image = docker_build.Image(
    "loader-image",
    context=docker_build.BuildContextArgs(
        location="/loader_deployed",
    ),
    dockerfile=docker_build.DockerfileArgs(
        location="/loader_deployed/Dockerfile",
    ),
    push=True,
    tags=[pulumi.Output.concat(
        region, 
        "-docker.pkg.dev/",
        project,
        "/newsjuice/loader:latest"
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
# CLOUD RUN SERVICE (OPTIONAL)
# ============================================================================

connection_name = f"{project}:{region}:{db_instance_name}"

cloudrun_service = None
cloudrun_iam = None

if enable_cloudrun:
    cloudrun_service = gcp.cloudrun.Service(
        "loader-service",
        name="newsjuice-loader",
        location=region,
        template=gcp.cloudrun.ServiceTemplateArgs(
            spec=gcp.cloudrun.ServiceTemplateSpecArgs(
                service_account_name=loader_service_account.email,
                containers=[
                    gcp.cloudrun.ServiceTemplateSpecContainerArgs(
                        image=loader_image.ref,
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
            depends_on=[sql_client_binding, storage_admin_binding, vertex_user_binding, loader_image]
        ),
    )

    cloudrun_iam = gcp.cloudrun.IamMember(
        "loader-invoker",
        service=cloudrun_service.name,
        location=region,
        role="roles/run.invoker",
        member="allUsers",
    )

# ============================================================================
# GKE CLUSTER (OPTIONAL) + KUBERNETES DEPLOYMENT
# ============================================================================

gke_cluster = None
node_pool = None
k8s_provider = None
k8s_namespace = None
k8s_deployment = None
k8s_service = None
gke_service_url = None

if enable_gke:
    # GKE service account
    gke_sa = gcp.serviceaccount.Account(
        "gke-node-sa",
        account_id="newsjuice-gke-nodes",
        display_name="NewsJuice GKE Node Service Account",
    )

    # IAM bindings for GKE nodes
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

    # Create GKE cluster
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

    # Create node pool
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

    # Workload Identity IAM binding for Kubernetes SA
    workload_identity_binding = gcp.serviceaccount.IAMBinding(
        "workload-identity-binding",
        service_account_id=loader_service_account.name,
        role="roles/iam.workloadIdentityUser",
        members=[
            f"serviceAccount:{project}.svc.id.goog[newsjuice/newsjuice-loader-sa]"
        ],
        opts=pulumi.ResourceOptions(
            depends_on=[loader_service_account, gke_cluster]
        ),
    )

    # Create Kubernetes provider - uses gcloud credentials automatically
    k8s_provider = k8s.Provider(
        "gke-k8s",
        enable_server_side_apply=True,
        opts=pulumi.ResourceOptions(
            depends_on=[node_pool]
        ),
    )

    # Deploy application to Kubernetes automatically
    
    # Create namespace
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

    # Create secret
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

    # Create service account
    k8s_service_account = k8s.core.v1.ServiceAccount(
        "loader-k8s-sa",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="newsjuice-loader-sa",
            namespace="newsjuice",
            annotations={
                "iam.gke.io/gcp-service-account": loader_service_account.email,
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[k8s_namespace, workload_identity_binding]
        ),
    )

    # Create deployment with REDUCED resources for e2-standard-2 nodes
    k8s_deployment = k8s.apps.v1.Deployment(
        "loader-deployment",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="newsjuice-loader",
            namespace="newsjuice",
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            replicas=2,
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"app": "newsjuice-loader"},
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"app": "newsjuice-loader"},
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    service_account_name="newsjuice-loader-sa",
                    containers=[
                        # Loader container - REDUCED resources + FIXED: Added DATABASE_URL
                        k8s.core.v1.ContainerArgs(
                            name="loader",
                            image=loader_image.ref,
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
                                # FIXED: Added DATABASE_URL environment variable
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
                            ],
                            resources=k8s.core.v1.ResourceRequirementsArgs(
                                requests={"memory": "512Mi", "cpu": "250m"},
                                limits={"memory": "1Gi", "cpu": "500m"},
                            ),
                        ),
                        # Cloud SQL Proxy sidecar - REDUCED resources
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
            depends_on=[k8s_service_account, k8s_secret, loader_image]
        ),
    )

    # Create LoadBalancer service
    k8s_service = k8s.core.v1.Service(
        "loader-k8s-service",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="loader-service",
            namespace="newsjuice",
        ),
        spec=k8s.core.v1.ServiceSpecArgs(
            type="LoadBalancer",
            selector={"app": "newsjuice-loader"},
            ports=[
                k8s.core.v1.ServicePortArgs(
                    port=80,
                    target_port=8080,
                ),
            ],
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[k8s_deployment]
        ),
    )

    # Get external IP
    gke_service_url = k8s_service.status.apply(
        lambda status: f"http://{status.load_balancer.ingress[0].ip}" if status and status.load_balancer and status.load_balancer.ingress else "pending"
    )

# ============================================================================
# EXPORTS
# ============================================================================

# Always export these
pulumi.export("image_name", loader_image.ref)
pulumi.export("artifact_repo", artifact_repo.name)
pulumi.export("connection_name", connection_name)
pulumi.export("database_url_format", f"postgresql://USER:PASSWORD@/DATABASE?host=/cloudsql/{connection_name}")

# Cloud Run exports
if enable_cloudrun and cloudrun_service:
    pulumi.export("cloudrun_enabled", True)
    pulumi.export("cloudrun_url", cloudrun_service.statuses[0].url)
else:
    pulumi.export("cloudrun_enabled", False)

# GKE exports
if enable_gke and gke_cluster:
    pulumi.export("gke_enabled", True)
    pulumi.export("gke_cluster_name", gke_cluster.name)
    pulumi.export("gke_cluster_endpoint", gke_cluster.endpoint)
    pulumi.export("gke_zone", zone)
    pulumi.export("gke_service_url", gke_service_url or "deploying...")
    pulumi.export("gke_setup_command", f"gcloud container clusters get-credentials newsjuice-cluster --zone={zone} --project={project}")
else:
    pulumi.export("gke_enabled", False)

# Summary
pulumi.export("deployment_summary", Output.all(enable_cloudrun, enable_gke).apply(
    lambda args: f"Cloud Run: {'✅ Enabled' if args[0] else '❌ Disabled'}, GKE: {'✅ Enabled' if args[1] else '❌ Disabled'}"
))
