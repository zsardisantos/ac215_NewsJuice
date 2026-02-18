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
    "firebase.googleapis.com"               # Firebase (for Auth)
    "identitytoolkit.googleapis.com"        # Firebase Identity Toolkit (for token verification)
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
# STEP 3: CREATE PULUMI STATE BUCKET
# =============================================================================

echo "Step 3: Creating Pulumi State Bucket"
echo "----------------------------------------"

PULUMI_BUCKET_NAME="${GCP_PROJECT}-pulumi-state-bucket"

# Check if bucket exists
if gsutil ls -b gs://$PULUMI_BUCKET_NAME &> /dev/null; then
    echo "✅ Pulumi state bucket already exists: gs://$PULUMI_BUCKET_NAME"
else
    echo "Creating Pulumi state bucket..."
    gsutil mb -p $GCP_PROJECT -l $GCP_REGION gs://$PULUMI_BUCKET_NAME
    
    # Enable versioning for safety (keeps history of state changes)
    gsutil versioning set on gs://$PULUMI_BUCKET_NAME
    
    echo "✅ Created Pulumi state bucket: gs://$PULUMI_BUCKET_NAME"
    echo "✅ Enabled versioning for state history"
fi

echo ""

# =============================================================================
# STEP 4: CREATE DEPLOYMENT SERVICE ACCOUNT
# =============================================================================

echo "Step 4: Creating Deployment Service Account"
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
# STEP 5: CREATE SERVICE ACCOUNT KEY
# =============================================================================

echo "Step 5: Creating Service Account Key"
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
# STEP 6: VERIFY EXISTING RESOURCES
# =============================================================================

echo "Step 6: Verifying Existing Resources"
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
# STEP 7: GEMINI SERVICE ACCOUNT SETUP
# =============================================================================
echo "Step 7: Gemini Service Account"
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
# STEP 8: FIREBASE SETUP
# =============================================================================

echo "Step 8: Firebase Authentication Setup"
echo "----------------------------------------"
echo "Firebase is used for user authentication (login/registration)."
echo "The backend uses Workload Identity - no JSON key file needed."
echo ""

# The GKE service account that needs Firebase permissions
GKE_SA_EMAIL="newsjuice-services-sa@${GCP_PROJECT}.iam.gserviceaccount.com"

echo "Granting Firebase Admin role to GKE service account..."
echo "(This allows the chatter service to verify Firebase tokens)"
echo ""

# Grant Firebase SDK Admin role to the GKE workload service account
# This is needed for firebase_admin.initialize_app() to work with ADC
# NOTE: This service account is created by Pulumi, so it might not exist yet
if gcloud iam service-accounts describe $GKE_SA_EMAIL --project=$GCP_PROJECT &> /dev/null; then
    gcloud projects add-iam-policy-binding $GCP_PROJECT \
        --member="serviceAccount:${GKE_SA_EMAIL}" \
        --role="roles/firebase.sdkAdminServiceAgent" \
        --condition=None \
        --quiet
    echo "✅ Granted roles/firebase.sdkAdminServiceAgent to $GKE_SA_EMAIL"
else
    echo "⚠️  Service account $GKE_SA_EMAIL does not exist yet"
    echo "   This is normal - it will be created by Pulumi deployment"
    echo "   After running 'pulumi up', run this command manually:"
    echo ""
    echo "   gcloud projects add-iam-policy-binding $GCP_PROJECT \\"
    echo "       --member=\"serviceAccount:${GKE_SA_EMAIL}\" \\"
    echo "       --role=\"roles/firebase.sdkAdminServiceAgent\""
    echo ""
fi
echo ""

# Remind user about Firebase console setup (can't be automated via gcloud)
echo "⚠️  MANUAL STEP REQUIRED - Firebase Console Setup:"
echo "   The following must be done manually in the Firebase Console:"
echo ""
echo "   1. Go to: https://console.firebase.google.com"
echo "   2. Click 'Add project'"
echo "   3. Select 'Add Firebase to existing Google Cloud project'"
echo "   4. Select project: $GCP_PROJECT"
echo "   5. Go to Authentication → Get Started"
echo "   6. Enable 'Email/Password' sign-in method"
echo "   7. Go to Project Settings → Your apps"
echo "   8. Add a Web app and copy the firebaseConfig"
echo "   9. Paste the config into your frontend firebase.js file"
echo ""
echo "   If Firebase project is already set up, skip steps 1-4."
echo ""

echo "✅ Firebase IAM setup complete"
echo ""

# =============================================================================
# STEP 9: DNS CONFIGURATION CHECK
# =============================================================================

echo "Step 9: DNS Configuration Status"
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
echo "  ✅ APIs Enabled (including Firebase + Identity Toolkit)"
echo "  ✅ Secrets Directory: $SECRETS_DIR"
echo "  ✅ Pulumi State Bucket: gs://${GCP_PROJECT}-pulumi-state-bucket"
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
echo "  ✅ Firebase IAM role granted to GKE service account"
echo "  ⚠️  Firebase Console setup: Manual step required (see Step 8)"
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
echo "1. Complete Firebase Console setup (Step 8 above):"
echo "   https://console.firebase.google.com"
echo ""

echo "2. Verify Gemini Service Account (if not done in Step 7):"
echo "   - Should exist at: $GEMINI_KEY_FILE"
echo "   - If missing, create manually at: https://console.cloud.google.com/iam-admin/serviceaccounts"
echo ""

echo "3. Get database password:"
echo "   - You should have this from your existing database instance"
echo "   - You'll need it for Pulumi config in step 4"
echo ""

echo "4. Update your code files (if needed):"
echo "   - docker-shell.sh: Verify GCP_PROJECT='newsjuice-2'"
echo "   - __main__.py: Verify correct bucket names and remove any hardcoded API keys"
echo ""

echo "5. Configure Pulumi:"
echo "   cd deployment"
echo "   pulumi stack init newsjuice-prod  # if stack doesn't exist"
echo "   pulumi config set gcp:project newsjuice-2"
echo "   pulumi config set gcp:region us-central1"
echo "   pulumi config set gcp:zone us-central1-a"
echo "   pulumi config set enable_gke true"
echo "   pulumi config set enable_cloudrun false"
echo "   pulumi config set --secret db_password YOUR_DB_PASSWORD"
echo ""

echo "6. Set environment variable for deployment:"
echo "   export GOOGLE_APPLICATION_CREDENTIALS=${SECRETS_DIR}/deployment.json"
echo ""

echo "7. Deploy with Pulumi:"
echo "   ./docker-shell.sh"
echo "   # Inside container:"
echo "   pulumi up"
echo ""

echo "8. After deployment, wait ~15 minutes for SSL certificate provisioning:"
echo "   kubectl describe managedcertificate newsjuice-cert -n newsjuice"
echo "   # Look for 'Status: Active'"
echo ""

echo "9. Verify deployment:"
echo "   curl https://www.newsjuiceapp.com"
echo ""

echo "=============================================="
echo "Setup script completed successfully!"
echo "=============================================="
