import aws_cdk as cdk

from aws_cdk import (
    # aws_cloudformation as cfn,
    # aws_s3 as s3,
    # aws_ssm as ssm,
    # aws_rds as rds,
    # aws_ecs as ecs,
    # aws_autoscaling as autoscaling,
    # aws_sns as sns,
    aws_lambda as _lambda,
    aws_eks as eks,
    # aws_logs as logs,
    # aws_elasticloadbalancingv2_targets as elbv2_targets,
    aws_iam as iam,
    # aws_cloudwatch as cw,
    # aws_cloudwatch_actions as cw_actions,
    # aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2,
    # aws_autoscaling as asg,
    # aws_s3_assets as s3_assets,
    # aws_route53 as route53,
    # aws_s3_deployment as s3deploy,
    Stack,
    # CfnOutput,
    # Duration,
    # RemovalPolicy,
)
from constructs import Construct
import os
import json

class WorkspaceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # server_cert_arn = "arn:aws:acm:us-east-2:014420964653:certificate/60c3d9a4-b58d-41a6-805d-16a6c7e63239"
        # client_cert_arn = "arn:aws:acm:us-east-2:014420964653:certificate/3ac5cdf6-bba5-4e80-a86d-1537208250b4"
        # ami_id = "ami-0146e9e4109b2015a" # My pre-defined AMI
        # ami_id = "ami-011b1a624adc9b86d" # AWS Kubernetes AMI Provided Image, SUCKS!

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
            assumed_by=iam.AccountRootPrincipal(),  # change to a more secure principal if desired
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
            # Use the exact Kubernetes version you requested (CDK will synthesize this string).
            # WARNING: choose a supported version for real deployments.
            version=eks.KubernetesVersion.of("1.32"),
            # Give the IAM role cluster-admin access at creation time
            masters_role=cluster_admin_role,
            # Authentication via EKS API (API only) — uses EKS API authentication path
            authentication_mode=eks.AuthenticationMode.API,
            # Make API server accessible both publicly & privately
            endpoint_access=eks.EndpointAccess.PUBLIC_AND_PRIVATE,
            # Do not create default capacity (we'll create a managed node group)
            default_capacity=1,
            # Keep CDK from automatically removing the default networking addons (we will manage add-ons explicitly).
            # The default is True; leave it True if you want self-managed add-ons to be bootstrapped.
            bootstrap_self_managed_addons=True,
            # keep kubectl handler in the default configuration
            kubectl_layer=my_layer
        )

        # --- Ensure cluster uses STANDARD upgrade policy (CloudFormation property) ---
        # this reaches into the L1 (CfnCluster) resource and adds the UpgradePolicy.SupportType = "STANDARD"
        cfn_cluster = cluster.node.default_child

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






#####################################################################################################3
        # machine_image = ecs.EcsOptimizedImage.amazon_linux2023()

        # asg = autoscaling.AutoScalingGroup(
        #     self,
        #     "ECSAsg",
        #     vpc=vpc,
        #     instance_type=ec2.InstanceType("t2.micro"),
        #     machine_image=machine_image,
        #     role=instance_role,
        #     security_group=sg,
        #     desired_capacity=1,
        #     min_capacity=1,
        #     max_capacity=1,
        #     spot_price="0.005",  # cheap max price (USD/hr) for Spot
        #     block_devices=[
        #         autoscaling.BlockDevice(
        #             device_name="/dev/xvda",
        #             volume=autoscaling.BlockDeviceVolume.ebs(30)
        #         )
        #     ]
        # )


        # keyPair = ec2.KeyPair.from_key_pair_attributes(self, "KeyPair",
        #             key_pair_name="KubernetesKeyPair",
        #             type=ec2.KeyPairType.RSA
        #         )
        
        # ecs_role = iam.Role(self, "Ec2Role",
        #     assumed_by=iam.ServicePrincipal("ecs.amazonaws.com"),
        #     role_name="EcsRole"
        # )

        # for i in ["AmazonSSMManagedInstanceCore", "CloudWatchLogsFullAccess", "ElasticLoadBalancingFullAccess"]:
        #     ecs_role.add_managed_policy(
        #         iam.ManagedPolicy.from_aws_managed_policy_name(i)
        #     )

        # vpn_sg.add_ingress_rule(
        #     connection=ec2.Port.all_traffic(),
        #     peer=vpn_sg,
        # )

        # sg = ec2.SecurityGroup(
        #     self,
        #     "Ec2Sg",
        #     vpc=vpc,
        #     description="EC2 Security Group",
        #     allow_all_outbound=True,
        # )

        # sg.add_ingress_rule(
        #     connection=ec2.Port.all_traffic(),
        #     peer=sg,
        # )

        # sg.add_ingress_rule(
        #     connection=ec2.Port.all_traffic(),
        #     peer=vpn_sg,
        # )

        # c1_cp1_user_data = ec2.UserData.for_linux()
        # c1_cp1_user_data.add_commands(
        #     "hostname c1-cp1",
        #     "echo 'c1-cp1 > /etc/hostname'",
        #     "kubeadm init --kubernetes-version v1.30.5 --pod-network-cidr=10.244.0.0/16 --ignore-preflight-errors=NumCPU,Mem",
        #     "mkdir -p /home/ubuntu/.kube",
        #     "chown ubuntu:ubuntu /home/ubuntu/.kube",
        #     "cp /etc/kubernetes/admin.conf /home/ubuntu/.kube/config",
        #     "chown ubuntu:ubuntu /home/ubuntu/.kube/config",
        #     "wget https://get.helm.sh/helm-v3.15.3-linux-amd64.tar.gz",
        #     "tar -xvzf helm-v3.15.3-linux-amd64.tar.gz",
        #     "cp linux-amd64/helm /usr/bin/helm",
        #     "sudo su - ubuntu",
        #     "helm repo add eks https://aws.github.io/eks-charts",
        #     "helm repo update",
        #     "helm upgrade --install aws-vpc-cni eks/aws-vpc-cni --namespace kube-system --set enableNetworkPolicy=true",   
        #     "kubeadm token create --print-join-command",
        #     "wget https://raw.githubusercontent.com/russest3/aws-vpc-with-client-vpn-endpoint/refs/heads/main/workspace/workspace/ingress.yml"
        #     "kubectl apply -f ingress.yml",
        # )

        # c1_cp1 = ec2.Instance(self, "ControlNode",
        #     vpc=vpc,
        #     instance_name="c1-cp1",
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
        #     machine_image=ec2.MachineImage.generic_linux({"us-east-2": ami_id}),
        #     security_group=sg,
        #     role=ecs_role,
        #     user_data=c1_cp1_user_data,
        #     user_data_causes_replacement=True,
        # )

        # cdk.Tags.of(c1_cp1).add("Resource", "EC2 Instance")

        # c1_node1_user_data = ec2.UserData.for_linux()
        # c1_node1_user_data.add_commands(
        #     "hostname c1-node1",
        #     "echo 'c1-node1 > /etc/hostname'",
        # )

        # c1_node1 = ec2.Instance(self, "WorkerNode1",
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     instance_type=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
        #     machine_image=ec2.MachineImage.generic_linux({"us-east-2": ami_id}),
        #     instance_name="c1-node1",
        #     security_group=sg,
        #     role=ecs_role,
        #     user_data=c1_node1_user_data,
        #     user_data_causes_replacement=True,
        #     key_pair=keyPair,
        # )

        # cdk.Tags.of(c1_node1).add("Resource", "EC2 Instance")

        # c1_node2_user_data = ec2.UserData.for_linux()
        # c1_node2_user_data.add_commands(
        #     "hostname c1-node2",
        #     "echo 'c1-node2 > /etc/hostname'",
        # )

        # c1_node2 = ec2.Instance(self, "WorkerNode2",
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     instance_name="c1-node2",
        #     instance_type=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
        #     machine_image=ec2.MachineImage.generic_linux({"us-east-2": ami_id}),         
        #     security_group=sg,
        #     role=ecs_role,
        #     user_data=c1_node2_user_data,
        #     user_data_causes_replacement=True,
        #     key_pair=keyPair,
        # )

        # cdk.Tags.of(c1_node2).add("Resource", "EC2 Instance")

        # c1_node3_user_data = ec2.UserData.for_linux()
        # c1_node3_user_data.add_commands(
        #     "hostname c1-node3",
        #     "echo 'c1-node3 > /etc/hostname'",
        # )

        # c1_node3 = ec2.Instance(self, "WorkerNode3",
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     instance_type=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
        #     machine_image=ec2.MachineImage.generic_linux({"us-east-2": ami_id}),
        #     instance_name="c1-node3",
        #     security_group=sg,
        #     role=ecs_role,
        #     user_data=c1_node3_user_data,
        #     user_data_causes_replacement=True,
        #     key_pair=keyPair,
        # )

        # cdk.Tags.of(c1_node3).add("Resource", "EC2 Instance")

        # log_group = logs.LogGroup(self, "ClientVPNlogGroup",
        #     log_group_name="ClientVPNlogGroup",
        #     retention=logs.RetentionDays.ONE_DAY,
        #     removal_policy=RemovalPolicy.DESTROY,
        # )

        # log_stream = logs.LogStream(
        #     self,
        #     "ClientVpnLogStream",
        #     log_group=log_group,
        # )

        # cpu_credit_usage_metric = cw.Metric(
        #     metric_name="CPUCreditUsage",
        #     namespace="AWS/EC2",
        #     dimensions_map={"InstanceId": c1_cp1.instance_id},
        #     period=Duration.minutes(5),
        #     statistic="Average"
        # )

        # alarm = cw.Alarm(self, "BurstAlarm",
        #     metric=cpu_credit_usage_metric,
        #     threshold=10,  # The value that triggers the alarm
        #     evaluation_periods=3,  # Number of periods to evaluate
        #     datapoints_to_alarm=2, # Number of datapoints within evaluation_periods that must be breaching
        #     comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        #     alarm_description="Alarm for CPUCreditUsage",
        #     actions_enabled=True,
        # )

        # email_list = sns.Topic(self, "EmailList",
        #     topic_name="EmailList",
        #     display_name="EmailList",
        # )

        # alarm.add_alarm_action(cw_actions.SnsAction(topic=email_list))

        # email_list.apply_removal_policy(RemovalPolicy.DESTROY)

        # cw_to_sns_role = iam.Role(self, "CW2SNSrole",
        #     assumed_by=iam.ServicePrincipal("cloudwatch.amazonaws.com")
        # )

        # email_list.add_to_resource_policy(
        #     iam.PolicyStatement(
        #         actions=["sns:Publish"],
        #         principals=[cw_to_sns_role],
        #         resources=[email_list.topic_arn]
        #     )
        # )

        # client_vpn_endpoint = ec2.CfnClientVpnEndpoint(self, "ClientVpnEndpoint",
        #     authentication_options=[{
        #         "type": "certificate-authentication",
        #         "mutualAuthentication": {
        #             "clientRootCertificateChainArn": client_cert_arn
        #         }
        #     }],
        #     client_cidr_block="10.100.0.0/22",
        #     connection_log_options=ec2.CfnClientVpnEndpoint.ConnectionLogOptionsProperty(
        #         enabled=True,
        #         cloudwatch_log_group=log_group.log_group_name,
        #         cloudwatch_log_stream=log_stream.log_stream_name,
        #     ),
        #     server_certificate_arn=server_cert_arn,
        #     vpn_port=443,
        #     transport_protocol="tcp",
        #     description="Client VPN endpoint for secure remote access",
        #     split_tunnel=True,
        #     vpc_id=vpc.vpc_id,
        #     dns_servers=["8.8.8.8", "8.8.4.4"],
        #     security_group_ids=[sg.security_group_id],
        # )

        # cdk.Tags.of(client_vpn_endpoint).add("Resource", "VPN")

        # ec2.CfnClientVpnTargetNetworkAssociation(self, "ClientVpnAssociation",
        #     client_vpn_endpoint_id=client_vpn_endpoint.ref,
        #     subnet_id=vpc.private_subnets[0].subnet_id
        # )

        # ec2.CfnClientVpnAuthorizationRule(self, "ClientVpnAuthRule",
        #     client_vpn_endpoint_id=client_vpn_endpoint.ref,
        #     target_network_cidr=vpc.vpc_cidr_block,
        #     authorize_all_groups=True,
        #     description="Allow access to all networks"
        # )



############ Optional ###############################
        # ubuntu_ami = ec2.MachineImage.lookup(
        #     name="*ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server*",
        #     owners=["099720109477"],  # Canonical's owner ID
        #     filters={
        #         "root-device-type": ["ebs"],
        #         "virtualization-type": ["hvm"]
        #     }
        # )

        # local_s3_asset.grant_read(c1_cp1.role)

        # vpc.add_interface_endpoint( "SSMvpcEndpoint",
        #     subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     service=ec2.InterfaceVpcEndpointAwsService.SSM,
        # )

        # vpc.add_interface_endpoint(
        #     "SSMMessagesEndpoint",
        #     service=ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
        # )
        # vpc.add_interface_endpoint(
        #     "EC2MessagesEndpoint",
        #     service=ec2.InterfaceVpcEndpointAwsService.EC2_MESSAGES,
        # )

        # auto_scaling_group = asg.AutoScalingGroup(self, "ASG",
        #     launch_template=launch_template_worker_nodes,
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     max_capacity=2,
        #     min_capacity=1,
        # )

        # rds_database = rds.DatabaseInstance(self, "MySQLDB",
        #     engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_0_42),
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     instance_type='db.t3.micro'
        # )

        # load_balancer = elbv2.ApplicationLoadBalancer(self, "ALB",
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        #     internet_facing=True,
        # )

        # ec2_target_group = elbv2.ApplicationTargetGroup(self, "MyTargetGroup",
        #     vpc=vpc,
        #     port=80,  # The port your application listens on
        #     target_type=elbv2.TargetType.INSTANCE,
        #     targets=[
        #         elbv2_targets.InstanceTarget(c1_node1),
        #         elbv2_targets.InstanceTarget(c1_node2),
        #         elbv2_targets.InstanceTarget(c1_node3),
        #     ],
        #     health_check=elbv2.HealthCheck(
        #         path="/",
        #         interval=Duration.seconds(30),
        #         timeout=Duration.seconds(5),
        #         healthy_threshold_count=2,
        #         unhealthy_threshold_count=2,
        #         ),
        # )

        # listener = load_balancer.add_listener("Listener", 
        #     port=80,
        #     open=True
        # )

        # listener.add_target_groups("EC2TargetGroup", target_groups=[ec2_target_group])

        # c1_cp1_run_shell_ssm_association = ssm.CfnAssociation(self, "C1CP1SsmAssociation",
        #     name="AWS-RunShellScript",  # The name of the SSM Document to associate
        #     targets=[
        #         ssm.CfnAssociation.TargetProperty(
        #             key="InstanceIds",  # Or "tag:TagName" for dynamic targeting
        #             values=[c1_cp1_instance_id]
        #         )
        #     ],
        #     association_name="C1CP1SsmAssociation",
        #     parameters={
        #         "commands": [
        #             "echo " + c1_cp1.instance_private_ip + " c1-cp1 c1-cp1.example.com >> /etc/hosts",
        #             "echo " + c1_node1.instance_private_ip + " c1-node1 c1-node1.example.com >> /etc/hosts",
        #             "echo " + c1_node2.instance_private_ip + " c1-node2 c1-node2.example.com >> /etc/hosts",
        #             "echo " + c1_node3.instance_private_ip + " c1-node3 c1-node3.example.com >> /etc/hosts",
        #             "kubeadm init --kubernetes-version v1.30.5 --pod-network-cidr=10.244.0.0/16 --ignore-preflight-errors=NumCPU,Mem",
        #             "mkdir -p /home/ubuntu/.kube",
        #             "cp /home/ubuntu/.kube/config /etc/kubernetes/admin.conf",
        #             "wget https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml",
        #             "kubectl create -f /home/ubuntu/kube-flannel.yml",
        #             "sleep 60",
        #             "kubectl get nodes -A -o wide",
        #             "wget https://get.helm.sh/helm-v3.15.3-linux-amd64.tar.gz",
        #             "tar -xvzf helm-v3.15.3-linux-amd64.tar.gz",
        #             "cp helm-v3.15.3-linux-amd64/linux-amd64/helm /usr/bin/helm",
        #             "kubeadm token create --print-join-command",
        #         ]
        #     }
        # )

