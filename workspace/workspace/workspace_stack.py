##  Need CloudWatch Alarm to trigger AG sizing  Logstreams not working???

from aws_cdk import (
    aws_ssm as ssm,
    aws_rds as rds,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2,
    aws_autoscaling as asg,
    aws_route53 as route53,
    Stack,
    CfnOutput,
    Duration,
)
from constructs import Construct
import os

class WorkspaceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, "Vpc",
            max_azs=2,
            cidr="10.192.0.0/16",
            nat_gateways=0,
            subnet_configuration=[
                # ec2.SubnetConfiguration(
                #     name="Private",
                #     subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                #     cidr_mask=24,
                    
                # ),
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
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

        # Look up the latest Ubuntu AMI
        ubuntu_ami = ec2.MachineImage.lookup(
            name="ubuntu/images/hvm-ssd/ubuntu-focal-24.04-amd64-server-*",
            owners=["099720109477"] # Canonical's owner ID
        )

        c1_cp1 = ec2.Instance(self, "ControlNode",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ubuntu_ami,
            user_data=ec2.UserData.custom("""
                #!/bin/bash
                hostname c1-cp1
                echo 'c1-cp1' > /etc/hostname
                add-apt-repository -y ppa:deadsnakes/ppa
                apt install -y python3.10 python3-pip python3-apt containerd apt-transport-https ca-certificates curl gpg net-tools
                apt update -y
                apt upgrade -y
                sed -i 's/^#\s*PasswordAuthentication.*$/PasswordAuthentication yes/' /etc/ssh/sshd_config
                sed -i 's/^KbdInteractiveAuthentication.*$/#KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
                systemctl restart sshd
                printf 'overlay\nbr_netfilter' > /etc/modules-load.d/k8s.conf
                modprobe overlay
                modprobe br_netfilter
                echo 'net.bridge.bridge-nf-call-iptables=1' | tee -a /etc/sysctl.conf
                echo 'net.bridge.bridge-nf-call-ip6tables=1' | tee -a /etc/sysctl.conf
                sed -i 's/^#net.ipv4.ip_forward.*$/net.ipv4.ip_forward=1/' /etc/sysctl.conf
                sysctl -p
                mkdir /etc/containerd
                containerd config default | tee /etc/containerd/config.toml
                sed -i 's/            SystemdCgroup = false/            SystemdCgroup = true/' /etc/containerd/config.toml
                curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
                echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
                apt update -y
                apt install -y kubelet kubeadm kubectl
                apt-mark hold kubelet kubeadm kubectl containerd
                reboot
                """
            ),
            security_group=sg,
            role=ssm_role,
        )

        c1_node1 = ec2.Instance(self, "WorkerNode1",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_ubuntu(),            
            security_group=sg,
            role=ssm_role,
            user_data=ec2.UserData.custom("""
                hostname c1-node1
                echo 'c1-node1' > /etc/hostname
                add-apt-repository -y ppa:deadsnakes/ppa
                apt install -y python3.10 python3-pip python3-apt containerd apt-transport-https ca-certificates curl gpg
                apt update -y
                apt upgrade -y
                sed -i 's/^#\s*PasswordAuthentication.*$/PasswordAuthentication yes/' /etc/ssh/sshd_config
                sed -i 's/^KbdInteractiveAuthentication.*$/#KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
                systemctl restart sshd
                printf 'overlay\nbr_netfilter' > /etc/modules-load.d/k8s.conf
                modprobe overlay
                modprobe br_netfilter
                echo 'net.bridge.bridge-nf-call-iptables=1' | tee -a /etc/sysctl.conf
                echo 'net.bridge.bridge-nf-call-ip6tables=1' | tee -a /etc/sysctl.conf
                sed -i 's/^#net.ipv4.ip_forward.*$/net.ipv4.ip_forward=1/' /etc/sysctl.conf
                sysctl -p
                mkdir /etc/containerd
                containerd config default | tee /etc/containerd/config.toml
                sed -i 's/            SystemdCgroup = false/            SystemdCgroup = true/' /etc/containerd/config.toml
                curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
                echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
                apt update -y
                apt install -y kubelet kubeadm kubectl
                apt-mark hold kubelet kubeadm kubectl containerd
                reboot
            """
            )
        )

        c1_node2 = ec2.Instance(self, "WorkerNode2",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_ubuntu(),            
            security_group=sg,
            role=ssm_role,
            user_data=ec2.UserData.custom("""
                hostname c1-node2
                echo 'c1-node2' > /etc/hostname
                add-apt-repository -y ppa:deadsnakes/ppa
                apt install -y python3.10 python3-pip python3-apt containerd apt-transport-https ca-certificates curl gpg
                apt update -y
                apt upgrade -y
                sed -i 's/^#\s*PasswordAuthentication.*$/PasswordAuthentication yes/' /etc/ssh/sshd_config
                sed -i 's/^KbdInteractiveAuthentication.*$/#KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
                systemctl restart sshd
                printf 'overlay\nbr_netfilter' > /etc/modules-load.d/k8s.conf
                modprobe overlay
                modprobe br_netfilter
                echo 'net.bridge.bridge-nf-call-iptables=1' | tee -a /etc/sysctl.conf
                echo 'net.bridge.bridge-nf-call-ip6tables=1' | tee -a /etc/sysctl.conf
                sed -i 's/^#net.ipv4.ip_forward.*$/net.ipv4.ip_forward=1/' /etc/sysctl.conf
                sysctl -p
                mkdir /etc/containerd
                containerd config default | tee /etc/containerd/config.toml
                sed -i 's/            SystemdCgroup = false/            SystemdCgroup = true/' /etc/containerd/config.toml
                curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
                echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
                apt update -y
                apt install -y kubelet kubeadm kubectl
                apt-mark hold kubelet kubeadm kubectl containerd
                reboot
            """
            )
        )

        c1_node3 = ec2.Instance(self, "WorkerNode3",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_ubuntu(),            
            security_group=sg,
            role=ssm_role,
            user_data=ec2.UserData.custom("""
                hostname c1-node3
                echo 'c1-node3' > /etc/hostname
                add-apt-repository -y ppa:deadsnakes/ppa
                apt install -y python3.10 python3-pip python3-apt containerd apt-transport-https ca-certificates curl gpg
                apt update -y
                apt upgrade -y
                sed -i 's/^#\s*PasswordAuthentication.*$/PasswordAuthentication yes/' /etc/ssh/sshd_config
                sed -i 's/^KbdInteractiveAuthentication.*$/#KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
                systemctl restart sshd
                printf 'overlay\nbr_netfilter' > /etc/modules-load.d/k8s.conf
                modprobe overlay
                modprobe br_netfilter
                echo 'net.bridge.bridge-nf-call-iptables=1' | tee -a /etc/sysctl.conf
                echo 'net.bridge.bridge-nf-call-ip6tables=1' | tee -a /etc/sysctl.conf
                sed -i 's/^#net.ipv4.ip_forward.*$/net.ipv4.ip_forward=1/' /etc/sysctl.conf
                sysctl -p
                mkdir /etc/containerd
                containerd config default | tee /etc/containerd/config.toml
                sed -i 's/            SystemdCgroup = false/            SystemdCgroup = true/' /etc/containerd/config.toml
                curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
                echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
                apt update -y
                apt install -y kubelet kubeadm kubectl
                apt-mark hold kubelet kubeadm kubectl containerd
                reboot
            """
            )
        )

        # auto_scaling_group = asg.AutoScalingGroup(self, "ASG",
        #     launch_template=launch_template_worker_nodes,
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
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

        vpc.add_interface_endpoint( "SSMvpcEndpoint",
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
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
