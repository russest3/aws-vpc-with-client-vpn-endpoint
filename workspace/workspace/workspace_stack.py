import aws_cdk as cdk

from aws_cdk import (
    aws_lambda as _lambda,
    aws_eks as eks,
    aws_iam as iam,
    aws_ec2 as ec2,
    Stack,
)
from constructs import Construct
import os
import json

class WorkspaceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, "Vpc",
            max_azs=2,
            cidr="10.192.0.0/16",
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,             
                ),
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24, 
                )
            ]
        )

        cluster_admin_role = iam.Role(
            self, "EKSClusterAdminRole",
            # assumed_by=iam.AccountRootPrincipal(),  # change to a more secure principal if desired
            assumed_by="arn:aws:iam::014420964653:user/russest3"
            description="Role used as cluster admin (system:masters) for the EKS cluster"
        )

        cluster_admin_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSClusterPolicy")
        )

        cluster_admin_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSVPCResourceController")
        )

        my_layer = _lambda.LayerVersion(
            self, "MyLayer",
            code=_lambda.Code.from_asset("workspace/kubernetes_files.zip"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="A layer containing common Python dependencies"
        )

        cluster = eks.Cluster(
            self, "EKSCluster",
            vpc=vpc,
            cluster_name="custom-eks-cluster",
            version=eks.KubernetesVersion.of("1.32"),
            masters_role=cluster_admin_role,
            authentication_mode=eks.AuthenticationMode.API,
            endpoint_access=eks.EndpointAccess.PUBLIC_AND_PRIVATE,
            default_capacity=0,
            # Keep CDK from automatically removing the default networking addons (we will manage add-ons explicitly).
            # The default is True; leave it True if you want self-managed add-ons to be bootstrapped.
            bootstrap_self_managed_addons=True,
            # keep kubectl handler in the default configuration
            kubectl_layer=my_layer
        )

        # --- Ensure cluster uses STANDARD upgrade policy (CloudFormation property) ---
        # this reaches into the L1 (CfnCluster) resource and adds the UpgradePolicy.SupportType = "STANDARD"
        # cfn_cluster = cluster.node.default_child

        # CloudFormation expects Properties.UpgradePolicy.SupportType
        # depending on CDK versions the path is case-sensitive for the CloudFormation shape.
        # We add an override to set the upgrade policy to STANDARD.
        # cfn_cluster.add_override("Properties.UpgradePolicy.SupportType", "STANDARD")

        nodegroup = cluster.add_nodegroup_capacity(
            "worker-nodes",
            desired_size=2,
            min_size=1,
            max_size=3,
            instance_types=[ec2.InstanceType("t2.micro")],
            disk_size=20,
            labels={"role": "worker"},
        )

        cw_insights_role = iam.Role(
            self, "EKSCloudWatchInsightsRole",
            assumed_by=iam.ServicePrincipal("eks.amazonaws.com"),
            description="IAM role for CloudWatch Container Insights add-on"
        )

        cw_insights_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
        )

        cw_insights_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy")
        )

        cloudwatch_role = iam.Role(
            self, "EKSCloudWatchRole",
            assumed_by=iam.ServicePrincipal("eks.amazonaws.com"),
            description="IAM role for EKS add-ons that need CloudWatch logging/metrics access"
        )

        cloudwatch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy")
        )

        addon_names = [
            "coredns",
            "vpc-cni",                     # Amazon VPC CNI plugin
            "kube-proxy",
            "metrics-server",
            "eks-pod-identity-agent",
            "eks-node-monitoring-agent",   # Node Monitoring Agent
        ]

        for name in addon_names:
            if name in ["metrics-server", "eks-node-monitoring-agent"]:
                eks.CfnAddon(
                    self, f"Addon{name.replace('-', '').title()}",
                    addon_name=name,
                    cluster_name=cluster.cluster_name,
                    service_account_role_arn=cloudwatch_role.role_arn
                )
            else:
                eks.CfnAddon(
                    self, f"Addon{name.replace('-', '').title()}",
                    addon_name=name,
                    cluster_name=cluster.cluster_name,
                )

        eks.CfnAddon(
            self, "CloudWatchObservabilityAddon",
            addon_name="amazon-cloudwatch-observability",
            cluster_name=cluster.cluster_name,
            service_account_role_arn=cw_insights_role.role_arn
        )