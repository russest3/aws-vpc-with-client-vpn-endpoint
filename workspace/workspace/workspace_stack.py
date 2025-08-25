##  CloudWatch Logs not working???

from aws_cdk import (
    aws_ssm as ssm,
    Stack,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_autoscaling as asg,
    aws_route53 as route53,
    CfnOutput,
    Duration,
)
from constructs import Construct
import os

class WorkspaceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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
                ),
            ]
        )

        ssm_role = iam.Role(self, "SSMrole",
                assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        
        ssm_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )

        sg = ec2.SecurityGroup(
            self,
            "Ec2Sg",
            vpc=vpc,
            description="Allow EC2 to use SSM",
            allow_all_outbound=True,
        )

        launch_template = ec2.LaunchTemplate(self, "LaunchTemplate",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),            
            user_data=ec2.UserData.custom("""
                #!/bin/bash
                yum -y update
                yum -y install httpd
                systemctl start httpd
                systemctl enable httpd
                echo "<h1>Hello World from $(hostname -f)</h1>" > /var/www/html/index.html
                """
            ),
            security_group=sg,
            role=ssm_role
        )

        ec2.UserData.add_signal_on_exit_command(self, resource=launch_template)

        asg.AutoScalingGroup(self, "ASG",
            launch_template=launch_template,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            max_capacity=2,
            min_capacity=1,
        )

        vpc.add_interface_endpoint( "SSMvpcEndpoint",
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
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
