##  Need CloudWatch Alarm to trigger AG sizing  Logstreams not working???
## Need to create State Manager in AWS SSM to run Ansible playbooks
## AWS-ApplyAnsiblePlaybooks SSM Documentq

from aws_cdk import (
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_rds as rds,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2,
    aws_autoscaling as asg,
    aws_route53 as route53,
    aws_s3_deployment as s3deploy,
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy
)
from constructs import Construct
import os

class WorkspaceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # c1_node1_bucket = s3.Bucket(self, "C1Node1Bucket",
        #     auto_delete_objects=True,
        #     # block_public_access=True,
        #     versioned=True,
        #     bucket_name="russest3-c1-node1-bucket",
        #     removal_policy=RemovalPolicy.DESTROY,
        #     website_index_document="kube-flannel.yml",
        # )

        # c1_node1_bucket_policy = iam.PolicyStatement(
        #     actions=["s3:GetObject"],
        #     resources=[c1_node1_bucket.arn_for_objects("*")],
        #     principals=[iam.ServicePrincipal('ssm.amazonaws.com')],
        # )

        vpc = ec2.Vpc(self, "Vpc",
            max_azs=2,
            cidr="10.192.0.0/16",
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,                    
                ),
            ]
        )

        ssm_role = iam.Role(self, "SSMrole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        
        for i in ["AmazonSSMManagedInstanceCore", "CloudWatchLogsFullAccess"]:
            ssm_role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(i)
            )

        sg = ec2.SecurityGroup(
            self,
            "Ec2Sg",
            vpc=vpc,
            description="Allow EC2 to use SSM",
            allow_all_outbound=True,
        )

        # Look up the latest Ubuntu 22.04 LTS AMI
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
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ubuntu_ami,
            user_data=ec2.UserData.custom(c1_cp1_script),
            security_group=sg,
            role=ssm_role,
            user_data_causes_replacement=True
        )

        # with open('workspace/c1-node1.sh', 'r') as f:
        #     c1_node1_script = f.read()
        # f.close()

        # c1_node1 = ec2.Instance(self, "WorkerNode1",
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        #     instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
        #     machine_image=ubuntu_ami,            
        #     security_group=sg,
        #     role=ssm_role,
        #     user_data=ec2.UserData.custom(c1_node1_script),
        #     user_data_causes_replacement=True
        # )

        # with open('workspace/c1-node2.sh', 'r') as f:
        #     c1_node2_script = f.read()
        # f.close()

        # c1_node2 = ec2.Instance(self, "WorkerNode2",
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        #     instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
        #     machine_image=ubuntu_ami,            
        #     security_group=sg,
        #     role=ssm_role,
        #     user_data=ec2.UserData.custom(c1_node2_script),
        #     user_data_causes_replacement=True
        # )

        # with open('workspace/c1-node3.sh', 'r') as f:
        #     c1_node3_script = f.read()
        # f.close()

        # c1_node3 = ec2.Instance(self, "WorkerNode3",
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        #     instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
        #     machine_image=ubuntu_ami,            
        #     security_group=sg,
        #     role=ssm_role,
        #     user_data=ec2.UserData.custom(c1_node3_script),
        #     user_data_causes_replacement=True
        # )

        # auto_scaling_group = asg.AutoScalingGroup(self, "ASG",
        #     launch_template=launch_template_worker_nodes,
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        #     max_capacity=2,
        #     min_capacity=1,
        # )

        # rds_database = rds.DatabaseInstance(self, "MySQLDB",
        #     engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_0_42),
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
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

        vpc.add_interface_endpoint( "SSMvpcEndpoint",
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            service=ec2.InterfaceVpcEndpointAwsService.SSM,
        )

        vpc.add_interface_endpoint(
            "SSMMessagesEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
        )
        vpc.add_interface_endpoint(
            "EC2MessagesEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.EC2_MESSAGES,
        )

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
                    # "echo " + c1_node1.instance_private_ip + " c1-node1 c1-node1.example.com >> /etc/hosts",
                    # "echo " + c1_node2.instance_private_ip + " c1-node2 c1-node2.example.com >> /etc/hosts",
                    # "echo " + c1_node3.instance_private_ip + " c1-node3 c1-node3.example.com >> /etc/hosts",
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

