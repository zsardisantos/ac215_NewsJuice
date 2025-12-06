"""
NewsJuice Loader - Deploy to Cloud Run with existing Cloud SQL connection
"""

import pulumi
import pulumi_gcp as gcp
import pulumi_docker_build as docker_build
from pulumi import Output
import subprocess

# Configuration
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
region = gcp_config.get("region") or "us-central1"

# Database configuration - point to your existing Cloud SQL instance
db_instance_name = config.get("db_instance_name") or "newsjuice-db-instance"
db_name = config.get("db_name") or "newsjuice"
db_user = config.get("db_user") or "newsjuice_app"
db_password = config.require_secret("db_password")

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

# Create Artifact Registry repository (MUST be created FIRST)
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

# Service account for Cloud Run
loader_service_account = gcp.serviceaccount.Account(
    "loader-sa",
    account_id="newsjuice-loader-sa",
    display_name="NewsJuice Loader Service Account",
)

# Grant Cloud SQL Client role (required to connect via Unix socket)
sql_client_binding = gcp.projects.IAMMember(
    "loader-sql-client",
    project=project,
    role="roles/cloudsql.client",
    member=loader_service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

# Grant Storage Object Admin (if loader needs GCS access)
storage_admin_binding = gcp.projects.IAMMember(
    "loader-storage-admin",
    project=project,
    role="roles/storage.objectAdmin",
    member=loader_service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

# Grant Vertex AI User (if loader uses embeddings)
vertex_user_binding = gcp.projects.IAMMember(
    "loader-vertex-user",
    project=project,
    role="roles/aiplatform.user",
    member=loader_service_account.email.apply(lambda email: f"serviceAccount:{email}"),
)

# ============================================================================
# BUILD AND PUSH DOCKER IMAGE WITH AUTHENTICATION
# ============================================================================

# Get Docker registry credentials
docker_registry_address = f"{region}-docker.pkg.dev"
docker_access_token = get_gcloud_access_token()

# Build the loader image from /loader_deployed directory
# CRITICAL: This depends on artifact_repo being created first
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
    # EXPLICIT DOCKER AUTHENTICATION - bypasses config file
    registries=[
        docker_build.RegistryArgs(
            address=docker_registry_address,
            username="oauth2accesstoken",
            password=pulumi.Output.secret(docker_access_token) if docker_access_token else None,
        )
    ] if docker_access_token else None,
    # EXPLICIT DEPENDENCY: Wait for artifact registry to be created
    opts=pulumi.ResourceOptions(
        depends_on=[artifact_repo]
    ),
)

# ============================================================================
# CLOUD RUN SERVICE WITH CLOUD SQL CONNECTION
# ============================================================================

# Build connection name for Cloud SQL
connection_name = f"{project}:{region}:{db_instance_name}"

# Deploy loader to Cloud Run using v1 API
service = gcp.cloudrun.Service(
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

# Make the service publicly accessible
service_iam = gcp.cloudrun.IamMember(
    "loader-invoker",
    service=service.name,
    location=region,
    role="roles/run.invoker",
    member="allUsers",
)

# ============================================================================
# EXPORTS
# ============================================================================

pulumi.export("loader_url", service.statuses[0].url)
pulumi.export("image_name", loader_image.ref)
pulumi.export("artifact_repo", artifact_repo.name)
pulumi.export("connection_name", connection_name)
pulumi.export("database_url_format", f"postgresql://USER:PASSWORD@/DATABASE?host=/cloudsql/{connection_name}")
