"""
Required below velero version installed on deploy runner.

Client:
    Version: v1.4.2

Wrapper commands around velero that does things like.

- Installing velero on to the targeted cluster
- Perform backups, restore and backup creation.
- Setting S3 Policies for backup buckets that are created.

"""
import json
import logging
import os
import shutil
import sys

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from subprocess import CalledProcessError, PIPE, run

import boto3

REQUIRED_VELERO_VERSION = "v1.4.2"


class VeleroCommand:
    """Base class for running Velero commands."""

    def __init__(self, args):
        """Initializing class for the VeleroCommands."""
        self.log = logging.getLogger(os.path.basename(__file__))
        self.profile = args.profile
        self.log.info("Setting AWS profile to {}".format(self.profile))
        self.session = boto3.session.Session(profile_name=self.profile)

    def _check_roles(self):
        """Check if the velero role exits in the IAM user list."""
        iam = self.session.client("iam")
        users = []
        for user in iam.list_users()["Users"]:
            users.append(user["UserName"])
        if "velero" in users:
            self.log.info("User velero exists under {} profile".format(self.profile))
            return True
        else:
            self.log.error("velero user doesn't exist under profile {}".format(self.profile))
            sys.exit(2)


class DescribeCommand:
    """Wrapper around `velero describe`."""

    def __init__(self, args):
        """Command that describes the existing backup on the cluster.

        Args:
            args (argparse.Namespace): Args returned by ArgumentParser.parse_args().
        """
        self.log = logging.getLogger(os.path.basename(__file__))
        self.backup_name = args.backup_name
        self.state = args.state

        self._construct_command()

    def __call__(self):
        """Run `velero describe` checks for existing bucket."""
        self.log.info("Running describe command: %s", " ".join(self.command))
        try:
            run(self.command, check=True)
        except CalledProcessError as e:
            self.log.error("Cannot fetch {} {} \n {}".format(self.backup_name, self.state, e))

    def _construct_command(self):
        """Construct `velero describe` command, save as self.command."""
        command = [
            "velero",
            "{}".format(self.state),
            "describe",
            "{}".format(self.backup_name),
            "--details",
        ]
        self.log.debug("Constructed describe command: %s", " ".join(command))
        self.command = command


class BackupCommand:
    """Wrapper around `velero backup`."""

    def __init__(self, args):
        """Command that perform backup on the cluster.

        Args:
            args (argparse.Namespace): Args returned by ArgumentParser.parse_args().
        """
        self.log = logging.getLogger(os.path.basename(__file__))
        self.backup_name = args.backup_name
        self.exclude_namespaces = ",".join(args.exclude_namespaces)
        self._construct_command()

    def __call__(self):
        """Run `velero backup` checks for existing bucket."""
        self.log.info("Running backup command: %s", " ".join(self.command))

        try:
            run(" ".join(self.command), check=True, shell=True)
        except Exception as e:
            self.log.error("{} backup cannot be created \n {}".format(self.backup_name, e))

    def _construct_command(self):
        """Construct `velero backup` command, save as self.command."""
        command = [
            "velero",
            "backup",
            "create",
            "{}".format(self.backup_name),
            "--exclude-namespaces {}".format(self.exclude_namespaces),
            "--wait",
        ]
        self.log.debug("Constructed backup command: %s", " ".join(command))
        self.command = command


class ScheduleCommand:
    """Warpper around `velero schedule create @value --ttl @value`."""

    def __init__(self, args):
        """Command that schedule backups based on cron provided."""
        """Args:
            args (argparse.Namespace): Args returned by ArgumentParser.parse_args().
        """
        self.log = logging.getLogger(os.path.basename(__file__))
        self.schedule_name = args.schedule_name
        self.include_namespaces = ",".join(args.include_namespaces)
        self.cron = args.cron
        self.ttl = args.ttl
        self._construct_command()

    def __call__(self):
        """Run `velero schedule` to perform scheduled backups."""
        self.log.info("Running schedule command: %s", " ".join(self.command))
        try:
            run(" ".join(self.command), check=True, shell=True)
        except Exception as e:
            self.log.error(
                "Schedule command cannot be performed for {} \n {}".format(self.schedule_name, e)
            )

    def _construct_command(self):
        """Construct `velero schedule` command, save as self.command."""
        command = [
            "velero",
            "create",
            "schedule",
            "{}".format(self.schedule_name),
            '--schedule="@every {}h"'.format(self.cron),
            "--include-namespaces {}".format(self.include_namespaces),
            "--ttl {}h".format(self.ttl),
        ]
        self.log.debug("Constructed schedule command: %s", " ".join(command))
        self.command = command


class RestoreCommand:
    """Wrapper around `velero restore`."""

    def __init__(self, args):
        """Command that restores from the existing backup on the cluster.

        Args:
            args (argparse.Namespace): Args returned by ArgumentParser.parse_args().
        """
        self.log = logging.getLogger(os.path.basename(__file__))
        self.backup_name = args.backup_name

        self._construct_command()

    def __call__(self):
        """Run `velero restore` checks for existing bucket."""
        self.log.info("Running restore command: %s", " ".join(self.command))
        try:
            run(" ".join(self.command), check=True, shell=True)
        except Exception as e:
            self.log.error("Restore cannot be performed from {} \n {}".format(self.backup_name, e))

    def _construct_command(self):
        """Construct `velero restore` command, save as self.command."""
        command = [
            "velero",
            "restore",
            "create",
            "--from-backup {}".format(self.backup_name),
            "--wait",
        ]
        self.log.debug("Constructed restore command: %s", " ".join(command))
        self.command = command


class InstallCommand(VeleroCommand):
    """Wrapper around `velero install`."""

    def __init__(self, args):
        """Command to install and setup velero on the cluster.

        Args:
            args (argparse.Namespace): Args returned by ArgumentParser.parse_args().
        """
        super(InstallCommand, self).__init__(args)
        self.bucket = args.bucket
        self.backup_region = args.backup_region
        self.snapshot_region = args.snapshot_region
        self.secret = args.secret
        self.create_bucket = args.create_bucket
        self._construct_command()

    def __call__(self):
        """Run `velero install` checks for existing bucket."""
        if self.create_bucket:
            self.create_backup_bucket()
            self.assign_bucket_policy()
        else:
            self._check_bucket_exists()
        self.log.info("Running install command: %s", " ".join(self.command))
        run([" ".join(self.command)], shell=True)

    def _construct_command(self):
        """Construct `velero install` command, save as self.command."""
        command = [
            "velero",
            "install",
            "--provider aws",
            "--plugins velero/velero-plugin-for-aws:v1.1.0",
            "--bucket {}".format(self.bucket),
            "--backup-location-config region={}".format(self.backup_region),
            "--snapshot-location-config region={}".format(self.snapshot_region),
            "--secret-file ./{}".format(self.secret),
        ]
        self.log.debug("Constructed install command: %s", " ".join(command))
        self.command = command

    def create_backup_bucket(self):
        """Create a new backup bucket during fresh setup of velero."""
        s3 = self.session.resource("s3")
        if s3.Bucket("{}".format(self.bucket)) in s3.buckets.all():
            self.log.error(
                "Unable to create Bucket {}. It already exists under {} region".format(
                    self.bucket, self.backup_region
                )
            )
            sys.exit(1)
        else:
            self.log.info(
                "Creating {} bucket under {} region".format(self.bucket, self.backup_region)
            )
            try:
                s3.create_bucket(
                    Bucket="{}".format(self.bucket),
                    CreateBucketConfiguration={
                        "LocationConstraint": "{}".format(self.backup_region)
                    },
                )
            except Exception as e:
                self.log.error("Unable to create bucket due to below exception \n {}".format(e))
                sys.exit(1)

    def assign_bucket_policy(self):
        """Method assigns velero s3 policy for bucket."""
        self.log.info("Assigning velero user policy to {}".format(self.bucket))
        velero_bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:DescribeVolumes",
                        "ec2:DescribeSnapshots",
                        "ec2:CreateTags",
                        "ec2:CreateVolume",
                        "ec2:CreateSnapshot",
                        "ec2:DeleteSnapshot",
                    ],
                    "Resource": "*",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:DeleteObject",
                        "s3:PutObject",
                        "s3:AbortMultipartUpload",
                        "s3:ListMultipartUploadParts",
                    ],
                    "Resource": ["arn:aws:s3:::{}/*".format(self.bucket)],
                },
                {
                    "Effect": "Allow",
                    "Action": ["s3:ListBucket"],
                    "Resource": ["arn:aws:s3:::{}".format(self.bucket)],
                },
            ],
        }
        try:
            iam = self.session.client("iam")
            iam.put_user_policy(
                UserName="velero",
                PolicyName="velero",
                PolicyDocument=json.dumps(velero_bucket_policy),
            )
        except Exception as e:
            self.log.error("Error while attaching policy to {}. \n {}".format(self.bucket, e))
            sys.exit(0)

    def _check_bucket_exists(self):
        """Exit with error if the s3 backup dont exist."""
        s3 = self.session.resource("s3")
        self.log.info("Checking if {} bucket exists".format(self.bucket))
        if not s3.Bucket("{}".format(self.bucket)) in s3.buckets.all():
            self.log.error(
                "Bucket {} doesn't exists under {} region".format(self.bucket, self.backup_region)
            )
            sys.exit(1)


class CommandLine:
    """Class to implement the command line interface, like argument parsing."""

    def __init__(self):
        """Initialize the CLI, parse args, and config logging."""
        self._parse_args()
        logging.basicConfig(level=getattr(logging, self.args.log_level.upper(), None))
        self.log = logging.getLogger(os.path.basename(__file__))
        self.log.debug("Parsed args: %s", self.args)

    def __call__(self):
        """Run commands for velero by calling."""
        if self.args.command == "describe":
            self._check_velero_version()
            describe = DescribeCommand(self.args)
            describe()
        elif self.args.command == "backup":
            self._check_velero_version()
            backup = BackupCommand(self.args)
            backup()
        elif self.args.command == "install":
            self._check_velero_version()
            install = InstallCommand(self.args)
            install()
        elif self.args.command == "restore":
            self._check_velero_version()
            restore = RestoreCommand(self.args)
            restore()
        elif self.args.command == "schedule":
            self._check_velero_version()
            schedule = ScheduleCommand(self.args)
            schedule()
        elif self.args.command == "required-version":
            self._required_version()
        else:
            self.arg_parser.print_help()

        sys.exit(0)

    def _velero_version(self):
        """Return the velero version installed, or None if not found."""
        velero_path = shutil.which("velero")
        if not velero_path:
            return None
        version_output = run(["velero", "version"], check=True, stdout=PIPE).stdout.decode().strip()
        self.log.debug("Velero version output: %s", version_output)
        version = version_output.split()[2]
        self.log.debug("Current Velero version is %s", version)

        return version

    def _check_velero_version(self):
        """Exit with error if installed version does not match the required version."""
        version = self._velero_version()
        if version != REQUIRED_VELERO_VERSION:
            self.log.error(
                "Wrong Velero version. Found %s, require %s", version, REQUIRED_VELERO_VERSION
            )
            sys.exit(3)

    def _required_version(self):
        """Print the required version and found version of Velero, and exit."""
        print("Required Velero version:", REQUIRED_VELERO_VERSION)
        print("Velero version found:", self._velero_version())
        sys.exit(0)

    def _parse_args(self):
        """Parse command line args and set self.args."""
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument(
            "--log-level",
            dest="log_level",
            choices=set(["critical", "error", "warning", "info", "debug"]),
            default="info",
            help="Log level",
        )
        parser.add_argument(
            "--profile",
            dest="profile",
            choices=set(["cv2", "default", "sdwan"]),
            default="default",
            help="AWS profile name. Else default profile will be considered.",
        )
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("required-version", formatter_class=ArgumentDefaultsHelpFormatter)
        describe_parser = subparsers.add_parser(
            "describe", formatter_class=ArgumentDefaultsHelpFormatter
        )
        describe_parser.add_argument(
            "--state",
            dest="state",
            required=True,
            choices=set(["backup", "restore"]),
            help="Provide the name of existing backup or restore",
        )
        describe_parser.add_argument(
            "--backup_name",
            dest="backup_name",
            required=True,
            help="Provide the name of existing backup",
        )
        install_parser = subparsers.add_parser(
            "install", formatter_class=ArgumentDefaultsHelpFormatter
        )
        install_parser.add_argument(
            "--bucket",
            dest="bucket",
            required=True,
            help="Provide a name for new backup installation",
        )
        install_parser.add_argument(
            "--backup_region",
            dest="backup_region",
            required=True,
            help="Provide the region for new backups",
        )
        install_parser.add_argument(
            "--snapshot_region",
            dest="snapshot_region",
            required=True,
            help="Provide the region for new snapshots",
        )
        install_parser.add_argument(
            "--secret", dest="secret", required=True, help="Velero user creds for installing",
        )
        install_parser.add_argument(
            "--create_bucket",
            dest="create_bucket",
            action="store_true",
            help="Check if there is a bucket, else create a bucket",
        )
        backup_parser = subparsers.add_parser(
            "backup", formatter_class=ArgumentDefaultsHelpFormatter
        )
        backup_parser.add_argument(
            "--backup_name",
            dest="backup_name",
            required=True,
            help="Provide the name of backup to get created",
        )
        backup_parser.add_argument(
            "--exclude_namespaces",
            dest="exclude_namespaces",
            type=str,
            action="append",
            default=["default", "kube-system", "kube-public", "kube-node-lease", "velero"],
            help="Provide the namespaces to get excluded from backup",
        )
        restore_parser = subparsers.add_parser(
            "restore", formatter_class=ArgumentDefaultsHelpFormatter
        )
        restore_parser.add_argument(
            "--backup_name",
            dest="backup_name",
            required=True,
            help="Provide the name of backup to get created",
        )
        schedule_parser = subparsers.add_parser(
            "schedule", formatter_class=ArgumentDefaultsHelpFormatter
        )
        schedule_parser.add_argument(
            "--schedule_name",
            dest="schedule_name",
            required=True,
            help="Provide the name of backup schedule to create",
        )
        schedule_parser.add_argument(
            "--include_namespaces",
            dest="include_namespaces",
            type=str,
            action="append",
            default=["default"],
            help="Provide the namespaces to get included in scheduled backup",
        )
        schedule_parser.add_argument(
            "--cron",
            dest="cron",
            type=int,
            required=True,
            help="Provide the cron schedule for backups",
        )
        schedule_parser.add_argument(
            "--ttl",
            dest="ttl",
            type=int,
            required=True,
            help="Provide the TTL (Time to live) for scheduled backups",
        )
        args = parser.parse_args()
        self.arg_parser = parser
        self.args = args


if __name__ == "__main__":
    cli = CommandLine()
    cli()
