from aws_cdk import (
    aws_iam as iam,
    aws_ec2 as ec2,
    Stack,
)
from constructs import Construct

class WorkspaceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ami_id = "ami-024267eacd9cea07d"

        vpc = ec2.Vpc(self, "Vpc",
            max_azs=1,
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
        
        ec2_role = iam.Role(self, "Ec2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            role_name="Ec2Role"
        )

        for i in ["AmazonSSMManagedInstanceCore", "CloudWatchLogsFullAccess", "ElasticLoadBalancingFullAccess"]:
            ec2_role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(i)
            )

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

        c1_cp1_user_data = ec2.UserData.for_linux()
        c1_cp1_user_data.add_commands(
            "hostname c1-cp1",
            "echo 'c1-cp1 > /etc/hostname'",
            "kubeadm init --kubernetes-version v1.30.5 --pod-network-cidr=10.244.0.0/16 --ignore-preflight-errors=NumCPU,Mem",
            "mkdir -p /home/ubuntu/.kube",
            "chown ubuntu:ubuntu /home/ubuntu/.kube",
            "cp /etc/kubernetes/admin.conf /home/ubuntu/.kube/config",
            "chown ubuntu:ubuntu /home/ubuntu/.kube/config",
            "sudo su - ubuntu",
            "cd /home/ubuntu",
            "helm repo update",
            "wget https://raw.githubusercontent.com/russest3/aws-vpc-with-client-vpn-endpoint/refs/heads/main/workspace/workspace/kube-flannel.yml",
            "kubectl apply -f /home/ubuntu/kube-flannel.yml",
            "wget https://get.helm.sh/helm-v3.15.3-linux-amd64.tar.gz",
            "tar -xvzf helm-v3.15.3-linux-amd64.tar.gz",
            "cp linux-amd64/helm /usr/bin/helm",
            "sudo su - ubuntu",
            "helm repo add eks https://aws.github.io/eks-charts",
            "helm repo update",
            "helm upgrade --install aws-vpc-cni eks/aws-vpc-cni --namespace kube-system --set enableNetworkPolicy=true",   
            "kubeadm token create --print-join-command",
            "wget https://raw.githubusercontent.com/russest3/aws-vpc-with-client-vpn-endpoint/refs/heads/main/workspace/workspace/ingress.yml"
            "kubectl apply -f ingress.yml",
        )

        c1_cp1 = ec2.Instance(self, "ControlNode",
            vpc=vpc,
            instance_name="c1-cp1",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.generic_linux({"us-east-2": ami_id}),
            role=ec2_role,
            key_pair=keyPair,
            user_data=c1_cp1_user_data,
            user_data_causes_replacement=True,
        )

        c1_node1_user_data = ec2.UserData.for_linux()
        c1_node1_user_data.add_commands(
            "hostname c1-node1",
            "echo 'c1-node1 > /etc/hostname'",
        )

        c1_node1 = ec2.Instance(self, "WorkerNode1",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.generic_linux({"us-east-2": ami_id}),
            instance_name="c1-node1",
            security_group=sg,
            role=ec2_role,
            user_data=c1_node1_user_data,
            user_data_causes_replacement=True,
            key_pair=keyPair,
        )

        c1_node2_user_data = ec2.UserData.for_linux()
        c1_node2_user_data.add_commands(
            "hostname c1-node2",
            "echo 'c1-node2 > /etc/hostname'",
        )

        c1_node2 = ec2.Instance(self, "WorkerNode2",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_name="c1-node2",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.generic_linux({"us-east-2": ami_id}),
            security_group=sg,
            role=ec2_role,
            user_data=c1_node2_user_data,
            user_data_causes_replacement=True,
            key_pair=keyPair,
        )

        c1_node3_user_data = ec2.UserData.for_linux()
        c1_node3_user_data.add_commands(
            "hostname c1-node3",
            "echo 'c1-node3 > /etc/hostname'",
        )

        c1_node3 = ec2.Instance(self, "WorkerNode3",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.generic_linux({"us-east-2": ami_id}),
            instance_name="c1-node3",
            security_group=sg,
            role=ec2_role,
            user_data=c1_node3_user_data,
            user_data_causes_replacement=True,
            key_pair=keyPair,
        )
