from aws_cdk import (
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_rds as rds,
    aws_logs as logs,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2,
    aws_autoscaling as asg,
    aws_route53 as route53,
    aws_s3_deployment as s3deploy,
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
)
from constructs import Construct
import os

class WorkspaceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        server_cert_arn = "arn:aws:acm:us-east-2:014420964653:certificate/60c3d9a4-b58d-41a6-805d-16a6c7e63239"
        client_cert_arn = "arn:aws:acm:us-east-2:014420964653:certificate/3ac5cdf6-bba5-4e80-a86d-1537208250b4"

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

        keyPair = ec2.KeyPair.from_key_pair_attributes(self, "KeyPair",
                    key_pair_name="KubernetesKeyPair",
                    type=ec2.KeyPairType.RSA
                )
        
        ssm_role = iam.Role(self, "Ec2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            role_name="Ec2Role"
        )
        
        for i in ["AmazonSSMManagedInstanceCore", "CloudWatchLogsFullAccess"]:
            ssm_role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(i)
            )

        vpn_sg = ec2.SecurityGroup(
            self,
            "VPNsg",
            vpc=vpc,
            description="VPN Security Group",
            allow_all_outbound=True,
        )

        vpn_sg.add_ingress_rule(
            connection=ec2.Port.all_traffic(),
            peer=vpn_sg,
        )

        # vpn_sg.add_ingress_rule(
        #     peer=ec2.Peer.any_ipv4(),
        #     connection=ec2.Port.tcp(22),
        #     description="Allow SSH access from anywhere"
        # )

        # vpn_sg.add_ingress_rule(
        #     peer=ec2.Peer.any_ipv4(),
        #     connection=ec2.Port.tcp(443),
        #     description="Allow SSH access from anywhere"
        # )

        sg = ec2.SecurityGroup(
            self,
            "Ec2Sg",
            vpc=vpc,
            description="EC2 Security Group",
            allow_all_outbound=True,
        )

        sg.add_ingress_rule(
            connection=ec2.Port.all_traffic(),
            peer=sg,
        )

        sg.add_ingress_rule(
            connection=ec2.Port.all_traffic(),
            peer=vpn_sg,
        )

        # sg.add_ingress_rule(
        #     peer=ec2.Peer.any_ipv4(),
        #     connection=ec2.Port.tcp(22),
        #     description="Allow SSH access from anywhere"
        # )

        # sg.add_ingress_rule(
        #     peer=ec2.Peer.any_ipv4(),
        #     connection=ec2.Port.tcp(6443),
        #     description="Allow SSH access from anywhere"
        # )

        ubuntu_ami = ec2.MachineImage.lookup(
            name="*ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server*",
            owners=["099720109477"],  # Canonical's owner ID
            filters={
                "root-device-type": ["ebs"],
                "virtualization-type": ["hvm"]
            }
        )

        with open('workspace/c1-cp1.sh', 'r') as f:
            c1_cp1_script = f.read()
        f.close()

        c1_cp1 = ec2.Instance(self, "ControlNode",
            vpc=vpc,
            instance_name="c1-cp1",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ubuntu_ami,
            user_data=ec2.UserData.custom(c1_cp1_script),
            security_group=sg,
            role=ssm_role,
            user_data_causes_replacement=True,
            key_pair=keyPair,
        )

        with open('workspace/c1-node1.sh', 'r') as f:
            c1_node1_script = f.read()
        f.close()

        c1_node1 = ec2.Instance(self, "WorkerNode1",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ubuntu_ami,
            instance_name="c1-node1",
            security_group=sg,
            role=ssm_role,
            user_data=ec2.UserData.custom(c1_node1_script),
            user_data_causes_replacement=True,
            key_pair=keyPair,
        )

        with open('workspace/c1-node2.sh', 'r') as f:
            c1_node2_script = f.read()
        f.close()

        c1_node2 = ec2.Instance(self, "WorkerNode2",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_name="c1-node2",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ubuntu_ami,            
            security_group=sg,
            role=ssm_role,
            user_data=ec2.UserData.custom(c1_node2_script),
            user_data_causes_replacement=True,
            key_pair=keyPair,
        )

        with open('workspace/c1-node3.sh', 'r') as f:
            c1_node3_script = f.read()
        f.close()

        c1_node3 = ec2.Instance(self, "WorkerNode3",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ubuntu_ami, 
            instance_name="c1-node3",
            security_group=sg,
            role=ssm_role,
            user_data=ec2.UserData.custom(c1_node3_script),
            user_data_causes_replacement=True,
            key_pair=keyPair,
        )

        log_group = logs.LogGroup(self, "ClientVPNlogGroup",
            log_group_name="ClientVPNlogGroup",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
        )

        log_stream = logs.LogStream(
            self,
            "ClientVpnLogStream",
            log_group=log_group,
        )

        # connection_log_options_property = ec2.CfnClientVpnEndpoint.ConnectionLogOptionsProperty(
        #     enabled=True,

        #     # the properties below are optional
        #     cloudwatch_log_group="ClientVPNlogGroup",
        #     cloudwatch_log_stream="cloudwatchLogStream"
        # )

        client_vpn_endpoint = ec2.CfnClientVpnEndpoint(self, "ClientVpnEndpoint",
            authentication_options=[{
                "type": "certificate-authentication",
                "mutualAuthentication": {
                    "clientRootCertificateChainArn": client_cert_arn
                }
            }],
            client_cidr_block="10.100.0.0/22",
            connection_log_options=ec2.CfnClientVpnEndpoint.ConnectionLogOptionsProperty(
                enabled=True,
                cloudwatch_log_group=log_group.log_group_name,
                cloudwatch_log_stream=log_stream.log_stream_name,
            ),
            server_certificate_arn=server_cert_arn,
            vpn_port=443,
            transport_protocol="tcp",
            description="Client VPN endpoint for secure remote access",
            split_tunnel=True,
            vpc_id=vpc.vpc_id,
            dns_servers=["8.8.8.8", "8.8.4.4"],
            security_group_ids=[vpn_sg.security_group_id],
        )

        ec2.CfnClientVpnTargetNetworkAssociation(self, "ClientVpnAssociation",
            client_vpn_endpoint_id=client_vpn_endpoint.ref,
            subnet_id=vpc.private_subnets[0].subnet_id
        )

        ec2.CfnClientVpnAuthorizationRule(self, "ClientVpnAuthRule",
            client_vpn_endpoint_id=client_vpn_endpoint.ref,
            # target_network_cidr="0.0.0.0/0",
            target_network_cidr=vpc.vpc_cidr_block,
            authorize_all_groups=True,
            description="Allow access to all networks"
        )

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

        # c1_node1_bucket = s3.Bucket(self, "russest3-C1Node1Bucket",
        #     auto_delete_objects=True,
        #     block_public_access=True,
        #     versioned=True,
        #     bucket_name="russest3-c1-node1-bucket",
        #     removal_policy=RemovalPolicy.DESTROY,
        # )

        # c1_node1_bucket_policy = iam.PolicyStatement(
        #     actions=["s3:GetObject"],
        #     resources=[c1_node1_bucket.arn_for_objects("*")],
        #     principals=[iam.ServicePrincipal('ssm.amazonaws.com')],
        # )

        # s3_endpoint = s3.CfnAccessPoint(self, "S3AccessPoint",
        #     bucket="russest3-C1Node1Bucket"
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

        # listener = load_balancer.add_listener("Listener", 
        #     port=80,
        #     open=True
        # )

        # listener.add_targets("ASGtargets",
        #     targets=[],
        #     port=80
        # )

        # Get Instance Ids
        # c1_cp1_instance_id = c1_cp1.instance_id
        # c1_node1_instance_id = c1_node1.instance_id
        # c1_node2_instance_id = c1_node2.instance_id
        # c1_node3_instance_id = c1_node3.instance_id

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

