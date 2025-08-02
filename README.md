# aws-vpc-with-client-vpn-endpoint
Build out an AWS VPC with Client VPN Endpoint using Cloud Development Kit!

## Requirements

- AWS CDK installed
- AWS CLI installed
- Run `aws configure` to configure access keys
- Create two self-signed certificates (client, server)

```
openssl req -new -key server.pem -out client.pem
openssl genrsa -out server_key.pem
openssl x509 -req -in server_csr.pem -signkey server_key.pem -out server_cert.pem -days 365
openssl genrsa -out client_key.pem
openssl x509 -req -in client_csr.pem -signkey client_key.pem -out client_cert.pem -days 365
```

- Upload these to two AWS S3 buckets one for client and one for server and record the resource ARNs

Update the `workspace/workspace_stack.py` file `server_cert_arn` and `client_cert_arn` variables

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
