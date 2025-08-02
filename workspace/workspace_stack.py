from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_route53 as route53,
    CfnOutput
)
from constructs import Construct

class ClientVPNStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        server_cert_arn = ""
        client_cert_arn = ""

        vpc = ec2.Vpc(self, "ClientVpnVpc",
            max_azs=2,
            cidr="10.192.0.0/16",
            nat_gateways=0,
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
            key_pair_name="MyKeyPair",
            type=ec2.KeyPairType.RSA
        )

        backend_sg = ec2.SecurityGroup(self, "BackendSecurityGroup",
            vpc=vpc,
            description="Allow VPN traffic",
            allow_all_outbound=True
        )
        backend_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="Allow SSH access from anywhere"
        )

        frontend_server = ec2.Instance(self, "FrontendServer",
            vpc=vpc,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            key_pair=keyPair,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            user_data_causes_replacement=True,
        )

        frontend_server.connections.allow_from_any_ipv4(ec2.Port.tcp(443), "Allow HTTPS access")

        backend_server = ec2.Instance(self, "BackendServer",
            vpc=vpc,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            key_pair=keyPair,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            user_data_causes_replacement=True,
            security_group=backend_sg,
        )

        client_vpn_endpoint = ec2.CfnClientVpnEndpoint(self, "ClientVpnEndpoint",
            authentication_options=[{
                "type": "certificate-authentication",
                "mutualAuthentication": {
                    "clientRootCertificateChainArn": client_cert_arn
                }
            }],
            client_cidr_block="10.100.0.0/22",
            connection_log_options={
                "enabled": False
            },
            server_certificate_arn=server_cert_arn,
            vpn_port=443,
            transport_protocol="tcp",
            description="Client VPN endpoint for secure remote access",
            split_tunnel=True,
            vpc_id=vpc.vpc_id,
            dns_servers=["8.8.8.8", "8.8.4.4"],
            security_group_ids=[backend_sg.security_group_id],
        )

        ec2.CfnClientVpnTargetNetworkAssociation(self, "ClientVpnAssociation",
            client_vpn_endpoint_id=client_vpn_endpoint.ref,
            subnet_id=vpc.private_subnets[0].subnet_id
        )

        ec2.CfnClientVpnAuthorizationRule(self, "ClientVpnAuthRule",
            client_vpn_endpoint_id=client_vpn_endpoint.ref,
            target_network_cidr="0.0.0.0/0",
            authorize_all_groups=True,
            description="Allow access to all networks"
        )
