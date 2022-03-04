# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.


import argparse
import os
import sys
from retry.api import retry_call

import yaml

from git.git_repository import GitRepository
from manifests.bundle_manifest import BundleManifest
from system.temporary_directory import TemporaryDirectory
from system.working_directory import WorkingDirectory
from test_workflow.perf_test.perf_test_cluster import PerfTestCluster
from test_workflow.perf_test.perf_test_suite import PerfTestSuite


def get_infra_repo_url():
    if "GITHUB_TOKEN" in os.environ:
        return "https://${GITHUB_TOKEN}@github.com/kotwanikunal/opensearch-infra.git"
    return "https://github.com/kotwanikunal/opensearch-infra.git"


def main():
    """
        Entry point for Performance Test with bundle manifest, config file containing the required arguments for running
        rally test and the stack name for the cluster. Will call out in test.sh with perf as argument
    """
    parser = argparse.ArgumentParser(description="Test an OpenSearch Bundle")
    parser.add_argument("--bundle-manifest", type=argparse.FileType("r"), help="Bundle Manifest file.", required=True)
    parser.add_argument("--stack", dest="stack", help="Stack name for performance test")
    parser.add_argument("--config", type=argparse.FileType("r"), help="Config file.", required=True)
    parser.add_argument("--security", dest="security", action="store_true",
                        help="Security of the cluster should be True/False",
                        default=False)
    parser.add_argument("--keep", dest="keep", action="store_true", help="Do not delete the working temporary directory.")
    parser.add_argument("--workload", default="nyc_taxis", help="Mensor (internal client) param - Workload name from OpenSeach Benchmark Workloads")
    parser.add_argument("--workload-options", default="{}", help="Mensor (internal client) param - Json object with OpenSearch Benchmark arguments")
    parser.add_argument("--warmup-iters", default=0, help="Mensor (internal client) param - Number of times to run a workload before collecting data")
    parser.add_argument("--test-iters", default=1, help="Mensor (internal client) param - Number of times to run a workload")
    args = parser.parse_args()

    manifest = BundleManifest.from_file(args.bundle_manifest)
    config = yaml.safe_load(args.config)

    tests_dir = os.path.join(os.getcwd(), "test-results", "perf-test")
    os.makedirs(tests_dir, exist_ok=True)

    with TemporaryDirectory(keep=args.keep, chdir=True) as work_dir:
        current_workspace = os.path.join(work_dir.name, "infra")
        with GitRepository(get_infra_repo_url(), "perf-test-fix", current_workspace):
            with WorkingDirectory(current_workspace):
                with PerfTestCluster.create(manifest, config, args.stack, args.security, current_workspace) as (test_cluster_endpoint, test_cluster_port):
                    perf_test_suite = PerfTestSuite(manifest, test_cluster_endpoint, args.security,
                                                    current_workspace, tests_dir, args)
                    retry_call(perf_test_suite.execute, tries=1, delay=60, backoff=2)


if __name__ == "__main__":
    sys.exit(main())
