#!/usr/bin/bash
add-apt-repository -y ppa:deadsnakes/ppa
apt install -y python3.10 python3-pip python3-apt python3-venv docker.io apt-transport-https ca-certificates curl gpg net-tools
apt update -y
apt upgrade -y
wget https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb
cat << 'END_OF_FILE' > /opt/aws/amazon-cloudwatch-agent/bin/config.json
{
  "agent": {
    "run_as_user": "cwagent"
  },
  "metrics": {
    "metrics_collected": {
      "procstat": [
        {
          "pid_file": "/var/run/sshd.pid",
          "measurement": [
            "cpu_usage",
            "memory_rss"
          ],
          "metrics_collection_interval": 60
        }
      ]
    }
  }
}
END_OF_FILE
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/bin/config.json -s
sed -i 's/^#\s*PasswordAuthentication.*$/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^KbdInteractiveAuthentication.*$/#KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
echo 'overlay' > /etc/modules-load.d/k8s.conf
echo 'br_netfilter' >> /etc/modules-load.d/k8s.conf
modprobe overlay
modprobe br_netfilter
echo 'net.bridge.bridge-nf-call-iptables=1' | tee -a /etc/sysctl.conf
echo 'net.bridge.bridge-nf-call-ip6tables=1' | tee -a /etc/sysctl.conf
sed -i 's/^#net.ipv4.ip_forward.*$/net.ipv4.ip_forward=1/' /etc/sysctl.conf
sysctl -p
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
apt update -y
apt install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl docker.io
wget https://s3.us-east-2.amazonaws.com/amazon-ecs-agent-us-east-2/amazon-ecs-init-latest.amd64.deb
dpkg -i amazon-ecs-init-latest.amd64.deb
# Get the ECS config file 
systemctl start --now ecs.service