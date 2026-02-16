#!/bin/bash
set -e  # Exit on any error

# =============================================================================
# NewsJuice Infrastructure Setup Script
# =============================================================================
# This script handles all manual setup steps that must be done BEFORE Pulumi
# =============================================================================

echo "=============================================="
echo "NewsJuice Infrastructure Setup"
echo "=============================================="
echo ""

# =============================================================================
# CONFIGURATION
# =============================================================================

export GCP_PROJECT="newsjuice-2"
export GCP_REGION="us-central1"
export GCP_ZONE="us-central1-a"
export SECRETS_DIR="../../../secrets"

# Static IP name (already exists)
export STATIC_IP_NAME="newsjuice-ip"

echo "Configuration:"
echo "  Project: $GCP_PROJECT"
echo "  Region: $GCP_REGION"
echo "  Zone: $GCP_ZONE"
echo "  Secrets Directory: $SECRETS_DIR"
echo ""

# =============================================================================
# PREFLIGHT CHECKS
# =============================================================================

echo "Step 0: Preflight Checks"
echo "----------------------------------------"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ ERROR: gcloud CLI is not installed"
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ ERROR: Not logged in to gcloud"
    echo "   Run: gcloud auth login"
    exit 1
fi

# Check if project exists
if ! gcloud projects describe $GCP_PROJECT &> /dev/null; then
    echo "❌ ERROR: Project $GCP_PROJECT does not exist or you don't have access"
    exit 1
fi

# Set the project
gcloud config set project $GCP_PROJECT

echo "✅ Preflight checks passed"
echo ""

# =============================================================================
# STEP 1: ENABLE REQUIRED APIs
# =============================================================================

echo "Step 1: Enabling Required GCP APIs"
echo "----------------------------------------"

REQUIRED_APIS=(
    "container.googleapis.com"              # GKE
    "storage.googleapis.com"                # Cloud Storage
    "artifactregistry.googleapis.com"       # Artifact Registry
    "sqladmin.googleapis.com"               # Cloud SQL
    "generativelanguage.googleapis.com"     # Gemini API
    "compute.googleapis.com"                # Compute Engine
    "servicenetworking.googleapis.com"      # Service Networking
    "cloudresourcemanager.googleapis.com"   # Resource Manager
    "iam.googleapis.com"                    # IAM
    "aiplatform.googleapis.com"             # Vertex AI (for Gemini)
)

echo "Enabling APIs (this may take 2-3 minutes)..."
gcloud services enable ${REQUIRED_APIS[@]} --project=$GCP_PROJECT

echo "✅ APIs enabled"
echo ""

# =============================================================================
# STEP 2: CREATE SECRETS DIRECTORY
# =============================================================================

echo "Step 2: Creating Secrets Directory"
echo "----------------------------------------"

if [ ! -d "$SECRETS_DIR" ]; then
    mkdir -p "$SECRETS_DIR"
    echo "✅ Created secrets directory: $SECRETS_DIR"
else
    echo "✅ Secrets directory already exists: $SECRETS_DIR"
fi
echo ""

# =============================================================================
# STEP 3: CREATE DEPLOYMENT SERVICE ACCOUNT
# =============================================================================

echo "Step 3: Creating Deployment Service Account"
echo "----------------------------------------"

SERVICE_ACCOUNT_NAME="newsjuice-deployer"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"

# Check if service account exists
if gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL --project=$GCP_PROJECT &> /dev/null; then
    echo "⚠️  Service account already exists: $SERVICE_ACCOUNT_EMAIL"
else
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --project=$GCP_PROJECT \
        --display-name="NewsJuice Deployment Account" \
        --description="Service account for Pulumi deployments"
    echo "✅ Created service account: $SERVICE_ACCOUNT_EMAIL"
fi

# Grant necessary roles
echo "Granting IAM roles..."

REQUIRED_ROLES=(
    "roles/owner"  # Simplified - grants all necessary permissions
)

for role in "${REQUIRED_ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $GCP_PROJECT \
        --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
        --role="$role" \
        --condition=None \
        --quiet
done

echo "✅ IAM roles granted"
echo ""

# =============================================================================
# STEP 4: CREATE SERVICE ACCOUNT KEY
# =============================================================================

echo "Step 4: Creating Service Account Key"
echo "----------------------------------------"

KEY_FILE="${SECRETS_DIR}/deployment.json"

if [ -f "$KEY_FILE" ]; then
    echo "⚠️  Key file already exists: $KEY_FILE"
    read -p "Do you want to create a new key? This will overwrite the existing one (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping key creation"
    else
        rm "$KEY_FILE"
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account="$SERVICE_ACCOUNT_EMAIL" \
            --project=$GCP_PROJECT
        echo "✅ Created new service account key: $KEY_FILE"
    fi
else
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$SERVICE_ACCOUNT_EMAIL" \
        --project=$GCP_PROJECT
    echo "✅ Created service account key: $KEY_FILE"
fi

# Set proper permissions on key file
chmod 600 "$KEY_FILE"

echo ""

# =============================================================================
# STEP 5: VERIFY EXISTING RESOURCES
# =============================================================================

echo "Step 5: Verifying Existing Resources"
echo "----------------------------------------"

# Check static IP
if gcloud compute addresses describe $STATIC_IP_NAME --global --project=$GCP_PROJECT &> /dev/null; then
    STATIC_IP=$(gcloud compute addresses describe $STATIC_IP_NAME --global --project=$GCP_PROJECT --format="value(address)")
    echo "✅ Static IP exists: $STATIC_IP_NAME ($STATIC_IP)"
else
    echo "❌ Static IP not found: $STATIC_IP_NAME"
    echo "   You may need to create it manually"
fi

# Check database instance
DB_INSTANCES=$(gcloud sql instances list --project=$GCP_PROJECT --format="value(name)" 2>/dev/null)
if [ -n "$DB_INSTANCES" ]; then
    echo "✅ Found database instance(s):"
    echo "$DB_INSTANCES" | while read instance; do
        echo "   - $instance"
    done
else
    echo "⚠️  No database instances found"
    echo "   You may need to create one manually"
fi

echo ""

# =============================================================================
# STEP 6: GEMINI SERVICE ACCOUNT SETUP
# =============================================================================
echo "Step 6: Gemini Service Account"
echo "----------------------------------------"

GEMINI_SA_NAME="newsjuice-gemini-sa"
GEMINI_SA_EMAIL="${GEMINI_SA_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"
GEMINI_KEY_FILE="$SECRETS_DIR/gemini_service_account.json"

# Check if service account already exists
if gcloud iam service-accounts describe $GEMINI_SA_EMAIL --project=$GCP_PROJECT &> /dev/null; then
    echo "⚠️  Gemini service account already exists: $GEMINI_SA_EMAIL"
    
    # Check if key file exists
    if [ -f "$GEMINI_KEY_FILE" ]; then
        echo "✅ Key file already exists: $GEMINI_KEY_FILE"
        read -p "Create a new key anyway? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            gcloud iam service-accounts keys create $GEMINI_KEY_FILE \
                --iam-account=$GEMINI_SA_EMAIL \
                --project=$GCP_PROJECT
            echo "✅ Created new key: $GEMINI_KEY_FILE"
        fi
    else
        echo "Creating key for existing service account..."
        gcloud iam service-accounts keys create $GEMINI_KEY_FILE \
            --iam-account=$GEMINI_SA_EMAIL \
            --project=$GCP_PROJECT
        echo "✅ Created key: $GEMINI_KEY_FILE"
    fi
else
    # Service account doesn't exist, offer to create it
    read -p "Create Gemini service account automatically? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating service account..."
        
        # Create service account
        gcloud iam service-accounts create $GEMINI_SA_NAME \
            --display-name="NewsJuice Gemini Service Account" \
            --project=$GCP_PROJECT
        echo "✅ Created service account: $GEMINI_SA_EMAIL"
        
        # Grant Vertex AI User role
        echo "Granting Vertex AI User role..."
        gcloud projects add-iam-policy-binding $GCP_PROJECT \
            --member="serviceAccount:$GEMINI_SA_EMAIL" \
            --role="roles/aiplatform.user" \
            --quiet
        echo "✅ Granted roles"
        
        # Create and download key
        echo "Creating JSON key..."
        gcloud iam service-accounts keys create $GEMINI_KEY_FILE \
            --iam-account=$GEMINI_SA_EMAIL \
            --project=$GCP_PROJECT
        
        if [ -f "$GEMINI_KEY_FILE" ]; then
            chmod 600 "$GEMINI_KEY_FILE"
            echo "✅ Service account created successfully!"
            echo "✅ Key saved to: $GEMINI_KEY_FILE"
        else
            echo "❌ Failed to create key file"
        fi
    else
        echo "Skipping automatic creation"
        echo ""
        echo "MANUAL STEPS:"
        echo "1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts"
        echo "2. Create service account with Vertex AI User role"
        echo "3. Download JSON key"
        echo "4. Save to: $GEMINI_KEY_FILE"
    fi
fi

echo ""

# Final check
if [ -f "$GEMINI_KEY_FILE" ]; then
    echo "✅ Gemini service account file exists: $GEMINI_KEY_FILE"
else
    echo "❌ Gemini service account file NOT found: $GEMINI_KEY_FILE"
fi
echo ""

# =============================================================================
# STEP 7: DNS CONFIGURATION CHECK
# =============================================================================

echo "Step 7: DNS Configuration Status"
echo "----------------------------------------"

# Check current DNS
echo "Current DNS status:"
CURRENT_IP=$(nslookup www.newsjuiceapp.com 2>/dev/null | grep -A1 "Name:" | grep "Address:" | tail -1 | awk '{print $2}')

if [ -n "$CURRENT_IP" ]; then
    echo "  www.newsjuiceapp.com → $CURRENT_IP"
    
    if [ -n "$STATIC_IP" ] && [ "$CURRENT_IP" == "$STATIC_IP" ]; then
        echo "  ✅ DNS already pointing to correct static IP!"
    else
        echo "  ⚠️  DNS status:"
        echo "     Current: $CURRENT_IP"
        if [ -n "$STATIC_IP" ]; then
            echo "     Expected: $STATIC_IP"
            echo "     Update your DNS A record at domain.com if needed"
        fi
    fi
else
    echo "  ❌ Unable to resolve DNS"
fi

echo ""

# =============================================================================
# SUMMARY
# =============================================================================

echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "📋 Summary of Setup:"
echo "  ✅ APIs Enabled"
echo "  ✅ Secrets Directory: $SECRETS_DIR"
echo "  ✅ Deployment Service Account: $SERVICE_ACCOUNT_EMAIL"
echo "  ✅ Deployment Service Account Key: ${SECRETS_DIR}/deployment.json"
if [ -f "$GEMINI_KEY_FILE" ]; then
    echo "  ✅ Gemini Service Account: $GEMINI_KEY_FILE"
else
    echo "  ⚠️  Gemini Service Account: Not created (manual step required)"
fi
if [ -n "$STATIC_IP" ]; then
    echo "  ✅ Static IP: $STATIC_IP_NAME ($STATIC_IP)"
fi
echo ""

echo "🔐 Saved Credentials:"
echo "  - Deployment key: ${SECRETS_DIR}/deployment.json"
if [ -f "$GEMINI_KEY_FILE" ]; then
    echo "  - Gemini service account: $GEMINI_KEY_FILE"
else
    echo "  - Gemini service account: ❌ NOT SET (see Step 6 above)"
fi
echo ""

echo "📝 Next Steps:"
echo ""
echo "1. Verify Gemini Service Account (if not done in Step 6):"
echo "   - Should exist at: $GEMINI_KEY_FILE"
echo "   - If missing, create manually at: https://console.cloud.google.com/iam-admin/serviceaccounts"
echo ""

echo "2. Get database password:"
echo "   - You should have this from your existing database instance"
echo "   - You'll need it for Pulumi config in step 4"
echo ""

echo "3. Update your code files (if needed):"
echo "   - docker-shell.sh: Verify GCP_PROJECT='newsjuice-2'"
echo "   - __main__.py: Verify correct bucket names and remove any hardcoded API keys"
echo ""

echo "4. Configure Pulumi:"
echo "   cd deployment"
echo "   pulumi stack init newsjuice-prod  # if stack doesn't exist"
echo "   pulumi config set gcp:project newsjuice-2"
echo "   pulumi config set gcp:region us-central1"
echo "   pulumi config set gcp:zone us-central1-a"
echo "   pulumi config set enable_gke true"
echo "   pulumi config set enable_cloudrun false"
echo "   pulumi config set --secret db_password YOUR_DB_PASSWORD"
echo ""

echo "5. Set environment variable for deployment:"
echo "   export GOOGLE_APPLICATION_CREDENTIALS=${SECRETS_DIR}/deployment.json"
echo ""

echo "6. Deploy with Pulumi:"
echo "   ./docker-shell.sh"
echo "   # Inside container:"
echo "   pulumi up"
echo ""

echo "7. After deployment, wait ~15 minutes for SSL certificate provisioning:"
echo "   kubectl describe managedcertificate newsjuice-cert -n newsjuice"
echo "   # Look for 'Status: Active'"
echo ""

echo "8. Verify deployment:"
echo "   curl https://www.newsjuiceapp.com"
echo ""

echo "=============================================="
echo "Setup script completed successfully!"
echo "=============================================="