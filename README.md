# AWS VPC, Public Subnet, Private Subnet, NAT Gateway, Internet Gateway, Auto-Scaling Group, Systems Manager Access, ALB, Apache, MySQL, PHP

## Requirements

- AWS CDK installed
- AWS CLI installed
- Run `aws configure` to configure access keys
- AWS Session Manager installed
- openvpn3 installed

## Session Manager

```
$ curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
$ sudo dpkg -i session-manager-plugin.deb

```

## VPN Access

Generate self signed certificates using easy-rsa.

```
sudo apt install easy-rsa -y
sudo su -
./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa build-key-server server.example.com
./easyrsa build-key client
```

Create Certificates in ACM and record their ARNs.  Update lines 24,25 in the workspace_stack.py file

After stack is created use openvpn3 to connect to the vpn client endpoint:

```
openvpn3 session-start --config config.ovpn
```


## Procedure

Create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

Deploy the code with:

```
$ cdk deploy
```

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
