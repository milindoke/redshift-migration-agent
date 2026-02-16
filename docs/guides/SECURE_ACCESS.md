# Secure Access to Redshift Migration Agent

Your Lambda function is secured with IAM authentication. Only users with proper IAM permissions can invoke it.

## ✅ What's Configured

1. **Lambda Function**: `redshift-migration-agent` (private, no public access)
2. **IAM Role**: `AgentExecutionRole` (Lambda execution role with Redshift/Bedrock permissions)

## 🔑 Access Control

To invoke the Lambda function, your IAM user or role needs the `lambda:InvokeFunction` permission.

### Grant Access to Users

Create an IAM policy and attach it to users who need access:

```bash
# Create policy document
cat > lambda-invoke-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:*:*:function:redshift-migration-agent"
    }
  ]
}
EOF

# Attach to a user
aws iam put-user-policy \
  --user-name YOUR_USERNAME \
  --policy-name RedshiftAgentInvoke \
  --policy-document file://lambda-invoke-policy.json

# Or create a managed policy for reuse
aws iam create-policy \
  --policy-name RedshiftAgentInvokePolicy \
  --policy-document file://lambda-invoke-policy.json

# Then attach to users
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/RedshiftAgentInvokePolicy
```

### Grant Access to Roles

For applications running on AWS (EC2, ECS, Lambda), attach the policy to their IAM role:

```bash
aws iam attach-role-policy \
  --role-name YOUR_ROLE_NAME \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/RedshiftAgentInvokePolicy
```

## 📞 How to Use the Agent

### Option 1: AWS CLI

```bash
aws lambda invoke \
  --function-name redshift-migration-agent \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"List my Redshift clusters in us-east-2"}' \
  --region us-east-2 \
  response.json && cat response.json
```

### Option 2: Python Client (Recommended)

```python
from examples.secure_client import RedshiftAgentClient

# Create client (uses AWS credentials automatically)
client = RedshiftAgentClient(region='us-east-2')

# Use the agent
result = client.chat("List my Redshift clusters")
print(result['response'])

# Or use helper methods
result = client.list_clusters(region='us-east-2')
result = client.extract_config('my-cluster-id', region='us-east-2')
```

### Option 3: Boto3 Direct

```python
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-2')

response = lambda_client.invoke(
    FunctionName='redshift-migration-agent',
    Payload=json.dumps({'message': 'List my clusters'})
)

result = json.loads(response['Payload'].read())
print(result)
```

## 👥 Managing Access

### Add More Users

Grant Lambda invoke permission to additional users:

```bash
# Attach policy to another user
aws iam attach-user-policy \
  --user-name another-user \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/RedshiftAgentInvokePolicy
```

### Revoke Access

Remove the policy from a user:

```bash
aws iam detach-user-policy \
  --user-name user-to-remove \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/RedshiftAgentInvokePolicy
```

### List Users with Access

```bash
# List users with the policy attached
aws iam list-entities-for-policy \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/RedshiftAgentInvokePolicy
```

## 🔒 Security Features

✅ **No public access** - Function requires IAM authentication  
✅ **Least privilege** - Users can only invoke this specific function  
✅ **Audit trail** - All invocations logged in CloudWatch  
✅ **Credential rotation** - Easy to rotate access keys  
✅ **Group-based access** - Easy to manage multiple users  

## 📊 Monitoring

### View invocation logs:

```bash
aws logs tail /aws/lambda/redshift-migration-agent --follow --region us-east-2
```

### Check who's using the function:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=redshift-migration-agent \
  --region us-east-2
```

## 🔄 Credential Rotation

### Rotate access keys:

```bash
# Create new key
aws iam create-access-key --user-name redshift-agent-user

# Delete old key (after updating applications)
aws iam delete-access-key \
  --user-name redshift-agent-user \
  --access-key-id OLD_KEY_ID
```

## 🚫 Revoking Access

### Remove a user:

```bash
# Remove from group
aws iam remove-user-from-group \
  --user-name john-doe \
  --group-name RedshiftAgentUsers

# Delete access keys
aws iam list-access-keys --user-name john-doe
aws iam delete-access-key --user-name john-doe --access-key-id KEY_ID

# Delete user
aws iam delete-user --user-name john-doe
```

## 💰 Cost

- Lambda invocations: ~$0.20 per 1M requests
- IAM users/groups: Free
- CloudWatch logs: ~$0.50/GB

**Estimated total: $0-20/month** depending on usage

## 🔧 Troubleshooting

### "Access Denied" error:

1. Check credentials are configured:
   ```bash
   aws sts get-caller-identity
   ```

2. Verify user is in the group:
   ```bash
   aws iam get-group --group-name RedshiftAgentUsers
   ```

3. Check policy is attached:
   ```bash
   aws iam list-attached-group-policies --group-name RedshiftAgentUsers
   ```

### Lambda function errors:

Check logs:
```bash
aws logs tail /aws/lambda/redshift-migration-agent --since 10m --region us-east-2
```

## 📝 Best Practices

1. **Use IAM roles** for applications running on AWS (EC2, ECS, Lambda)
2. **Rotate credentials** regularly (every 90 days)
3. **Use MFA** for IAM users with console access
4. **Monitor usage** via CloudWatch and CloudTrail
5. **Principle of least privilege** - only grant necessary permissions

## 🎯 Next Steps

1. Test the secure client: `python examples/secure_client.py`
2. Share credentials with authorized team members
3. Set up CloudWatch alarms for monitoring
4. Configure credential rotation schedule

---

**Your agent is now securely deployed and ready to use!** 🎉
