# What is velero

Velero is a popular open-source tool that can provide Kubernetes cluster disaster recovery, data migration, and data protection. Velero can back up Kubernetes cluster resources and persistent volumes to externally supported storage backend on demand or by schedule.

# velero-wrapper
Cli wrapper for velero for performing backups on K8 cluster running on AWS. 

# Velero Wrapper CLI for AWS + Kops Kubernetes Clusters

A Python-based CLI tool to simplify the deployment and management of [Velero](https://velero.io/) on Kubernetes clusters provisioned with [kops](https://kops.sigs.k8s.io/) and hosted on AWS.

This wrapper handles Velero installation, backup scheduling, restoration, and S3 bucket policy configuration, making it easier to run disaster recovery operations without manually dealing with complex Velero commands.

## ⚙️ Features

- ✅ Installs Velero with required AWS plugins and secrets
- 💾 Creates on-demand backups (with namespace exclusion)
- 🔄 Restores from existing backups
- 📅 Schedules recurring backups using cron-based TTLs
- 📂 Describes backup and restore states
- 🛡️ Sets up S3 bucket and IAM policies for Velero automation
- 🔍 Validates required Velero version before execution

## 🧰 Prerequisites

- Python 3.7+
- Velero CLI installed with **version `v1.4.2`**
- Kubernetes cluster deployed with **kops** on AWS
- AWS CLI configured with appropriate profiles and IAM permissions
- Valid AWS credentials (for Velero user)
- IAM user named `velero` must exist (or will be validated during install)

## 📦 Installation

```bash
git clone https://github.com/alapatipavan/velero-wrapper.git
cd velero-wrapper
pip install -r requirements.txt  # Optional, if dependencies like boto3 are added
```

🚀 Usage
```python velero.py <command> [OPTIONS]```

🔍 Check Required Velero Version
```python velero.py required-version```

🛠 Install Velero
```
python velero.py install \
  --bucket my-backup-bucket \
  --backup_region us-west-2 \
  --snapshot_region us-west-2 \
  --secret credentials-velero \
  --create_bucket \
  --profile default
```

💾 Create Backup
```
python velero.py backup \
  --backup_name my-backup \
  --exclude_namespaces kube-system \
  --profile default
```

🔄 Restore from Backup
```
python velero.py restore \
  --backup_name my-backup \
  --profile default
```

📅 Schedule Recurring Backups
```
python velero.py schedule \
  --schedule_name daily-backup \
  --include_namespaces default \
  --cron 24 \
  --ttl 72 \
  --profile default
```

📑 Describe Backup or Restore
```
python velero.py describe \
  --state backup \
  --backup_name my-backup \
  --profile default
```

🛡 AWS IAM Policy (Auto-attached to velero user)

The install command assigns a strict S3 and EC2 policy required by Velero to function correctly. This includes permissions for:
	•	EC2 volumes/snapshots
	•	S3 object access and lifecycle
	•	Velero restore/backup access

🧪 Example AWS Setup for Secrets
```
Ensure your credentials-velero file is in this format:
[default]
aws_access_key_id=<ACCESS_KEY>
aws_secret_access_key=<SECRET_KEY>
```
📂 Project Structure
```
velero.py            # Main CLI logic and subcommands
README.md            # This file
```
🧱 Dependencies
	•	boto3: Used for AWS IAM and S3 interactions
	•	argparse: CLI parsing
	•	subprocess: Interface with velero CLI

🧼 Logging

Adjust verbosity using --log-level:
```
--log-level debug|info|warning|error|critical
```
🛠 Contribution

Feel free to fork and enhance! Submit issues or PRs for bugs, improvements, or new features.
