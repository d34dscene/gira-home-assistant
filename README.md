## Installation

1. Download as zip and unpack
```bash
curl -o gira-integration.zip https://github.com/leoyn/gira-home-assistant/archive/refs/heads/production.zip
unzip gira-integration.zip
mkdir -p ./custom_components/gira
cp gira-integration/src ./custom_components/gira
```

2. Add the following to your `configuration.yaml`
```yaml
gira:
  host: XXX.XXX.XXX.XXX
  port: 80
  username: <username>
  password: <password>
```