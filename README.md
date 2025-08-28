# AWS VPC, Public Subnet, Private Subnet, NAT Gateway, Internet Gateway, Auto-Scaling Group, Systems Manager Access, ALB, Apache, MySQL, PHP

## Requirements

- AWS CDK installed
- AWS CLI installed
- Run `aws configure` to configure access keys
- AWS Session Manager installed

## Session Manager

```
$ curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
$ sudo dpkg -i session-manager-plugin.deb

```

AWS-ApplyAnsiblePlaybooks SSM Document

https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-state-manager-ansible.html

aws ssm create-association --name "AWS-ApplyAnsiblePlaybooks" \
    --targets Key=tag:TagKey,Values=TagValue \
    --parameters '{"SourceType":["GitHub"],"SourceInfo":["{\"owner\":\"owner_name\", \"repository\": \"name\", \"getOptions\": \"branch:master\"}"],"InstallDependencies":["True_or_False"],"PlaybookFile":["file_name.yml"],"ExtraVariables":["key/value_pairs_separated_by_a_space"],"Check":["True_or_False"],"Verbose":["-v,-vv,-vvv, or -vvvv"],"TimeoutSeconds":["3600"]}' \
    --association-name "name" \
    --schedule-expression "cron_or_rate_expression"

{
   "owner":"user_name",
   "repository":"name",
   "path":"path_to_directory_or_playbook_to_download",
   "getOptions":"branch:branch_name",
   "tokenInfo":"{{(Optional)_token_information}}"
}

aws ssm send-command \
    --document-name "AWS-ApplyAnsiblePlaybooks" \
    --targets "Key=InstanceIds,Values=instance-id" \
    --cli-input-json file://c1-cp1.json

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
