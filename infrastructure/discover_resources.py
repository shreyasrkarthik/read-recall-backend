#!/usr/bin/env python3

import boto3
import json
import os
from botocore.exceptions import ClientError

def discover_resources():
    """Discover AWS resources and output as a structured report"""
    results = {}
    
    # Lambda Functions
    try:
        print("Discovering Lambda functions...")
        lambda_client = boto3.client('lambda')
        functions = lambda_client.list_functions()
        results['lambda'] = [{
            'name': function['FunctionName'],
            'runtime': function['Runtime'],
            'arn': function['FunctionArn']
        } for function in functions['Functions']]
    except ClientError as e:
        print(f"Error listing Lambda functions: {e}")
        results['lambda'] = []
    
    # S3 Buckets
    try:
        print("Discovering S3 buckets...")
        s3_client = boto3.client('s3')
        buckets = s3_client.list_buckets()
        results['s3'] = [{
            'name': bucket['Name']
        } for bucket in buckets['Buckets']]
    except ClientError as e:
        print(f"Error listing S3 buckets: {e}")
        results['s3'] = []
    
    # SQS Queues
    try:
        print("Discovering SQS queues...")
        sqs_client = boto3.client('sqs')
        queues = sqs_client.list_queues()
        queue_urls = queues.get('QueueUrls', [])
        
        results['sqs'] = []
        for url in queue_urls:
            queue_name = url.split('/')[-1]
            try:
                attrs = sqs_client.get_queue_attributes(
                    QueueUrl=url,
                    AttributeNames=['QueueArn']
                )
                results['sqs'].append({
                    'name': queue_name,
                    'url': url,
                    'arn': attrs['Attributes'].get('QueueArn', '')
                })
            except ClientError:
                results['sqs'].append({
                    'name': queue_name,
                    'url': url
                })
    except ClientError as e:
        print(f"Error listing SQS queues: {e}")
        results['sqs'] = []
    
    # DynamoDB Tables
    try:
        print("Discovering DynamoDB tables...")
        dynamodb_client = boto3.client('dynamodb')
        tables = dynamodb_client.list_tables()
        
        results['dynamodb'] = []
        for table_name in tables.get('TableNames', []):
            try:
                table_desc = dynamodb_client.describe_table(TableName=table_name)
                results['dynamodb'].append({
                    'name': table_name,
                    'arn': table_desc['Table']['TableArn']
                })
            except ClientError:
                results['dynamodb'].append({
                    'name': table_name
                })
    except ClientError as e:
        print(f"Error listing DynamoDB tables: {e}")
        results['dynamodb'] = []
    
    # API Gateway APIs
    try:
        print("Discovering API Gateway APIs...")
        apigw_client = boto3.client('apigateway')
        apis = apigw_client.get_rest_apis()
        
        results['apigateway'] = [{
            'name': api['name'],
            'id': api['id'],
            'created_date': api['createdDate'].isoformat() if 'createdDate' in api else None
        } for api in apis.get('items', [])]
    except ClientError as e:
        print(f"Error listing API Gateway APIs: {e}")
        results['apigateway'] = []
    
    return results

def generate_cdk_imports(resources):
    """Generate CDK import code for discovered resources"""
    cdk_code = []
    cdk_code.append("""from aws_cdk import (
    Stack, aws_lambda as _lambda,
    aws_sqs as sqs, aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigw,
    Tags
)
from constructs import Construct

class ReadRecallStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Add project tag to all resources
        Tags.of(self).add("Project", "ReadRecall")
        """)
    
    # Lambda Functions
    if resources.get('lambda'):
        cdk_code.append("        # ▼ Lambda Functions")
        for func in resources['lambda']:
            safe_id = ''.join(c if c.isalnum() else '' for c in func['name'])
            cdk_code.append(f"        {safe_id.lower()}_lambda = _lambda.Function.from_function_name(")
            cdk_code.append(f"            self, \"{safe_id}Function\", \"{func['name']}\"")
            cdk_code.append("        )\n")
    
    # S3 Buckets
    if resources.get('s3'):
        cdk_code.append("        # ▼ S3 Buckets")
        for bucket in resources['s3']:
            safe_id = ''.join(c if c.isalnum() else '' for c in bucket['name'])
            cdk_code.append(f"        {safe_id.lower()}_bucket = s3.Bucket.from_bucket_name(")
            cdk_code.append(f"            self, \"{safe_id}Bucket\", \"{bucket['name']}\"")
            cdk_code.append("        )\n")
    
    # SQS Queues
    if resources.get('sqs'):
        cdk_code.append("        # ▼ SQS Queues")
        for queue in resources['sqs']:
            safe_id = ''.join(c if c.isalnum() else '' for c in queue['name'])
            if 'arn' in queue:
                cdk_code.append(f"        {safe_id.lower()}_queue = sqs.Queue.from_queue_arn(")
                cdk_code.append(f"            self, \"{safe_id}Queue\", \"{queue['arn']}\"")
            else:
                cdk_code.append(f"        {safe_id.lower()}_queue = sqs.Queue.from_queue_arn(")
                cdk_code.append(f"            self, \"{safe_id}Queue\",")
                cdk_code.append(f"            f\"arn:aws:sqs:{{Stack.of(self).region}}:{{Stack.of(self).account}}:{queue['name']}\"")
            cdk_code.append("        )\n")
    
    # DynamoDB Tables
    if resources.get('dynamodb'):
        cdk_code.append("        # ▼ DynamoDB Tables")
        for table in resources['dynamodb']:
            safe_id = ''.join(c if c.isalnum() else '' for c in table['name'])
            cdk_code.append(f"        {safe_id.lower()}_table = dynamodb.Table.from_table_name(")
            cdk_code.append(f"            self, \"{safe_id}Table\", \"{table['name']}\"")
            cdk_code.append("        )\n")
    
    # API Gateway
    if resources.get('apigateway'):
        cdk_code.append("        # ▼ API Gateway")
        for api in resources['apigateway']:
            safe_id = ''.join(c if c.isalnum() else '' for c in api['name'])
            cdk_code.append(f"        {safe_id.lower()}_api = apigw.RestApi.from_rest_api_id(")
            cdk_code.append(f"            self, \"{safe_id}Api\", \"{api['id']}\"")
            cdk_code.append("        )\n")
    
    return '\n'.join(cdk_code)

if __name__ == "__main__":
    print("Discovering AWS resources for CDK import...")
    resources = discover_resources()
    
    # Print summary
    print("\nDiscovered Resources:")
    for resource_type, items in resources.items():
        print(f"- {resource_type.upper()}: {len(items)} resources")
        for item in items:
            print(f"  - {item.get('name', 'unknown')}")
    
    # Generate the CDK import code
    cdk_code = generate_cdk_imports(resources)
    
    # Save to file
    output_file = "discovered_stack.py"
    with open(output_file, 'w') as f:
        f.write(cdk_code)
    
    print(f"\nGenerated CDK import code saved to: {output_file}")
    print("You can review this file and merge the relevant parts into your infrastructure_stack.py")
