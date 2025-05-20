from aws_cdk import (
    Stack,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct

class IamRolesStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create the ReadRecallInfraCI role for CI/CD pipeline
        infra_ci_role = iam.Role(
            self, "ReadRecallInfraCI",
            role_name="ReadRecallInfraCI",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("cloudformation.amazonaws.com"),
                # Add GitHub OIDC when you connect GitHub Actions
                iam.ServicePrincipal("codebuild.amazonaws.com")
            ),
            description="Role for CI/CD pipelines to deploy infrastructure changes"
        )

        # Define the policies for the CI role
        infra_ci_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSCloudFormationFullAccess")
        )
        
        infra_ci_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["iam:PassRole"],
                resources=["*"]
            )
        )
        
        infra_ci_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:*",
                    "s3:*",
                    "sqs:*",
                    "logs:*",
                    "apigateway:*"
                ],
                resources=["*"]
            )
        )

        # Create the ReadRecallDevLimited role for developers/interns
        dev_boundary = iam.ManagedPolicy(
            self, "ReadRecallDevLimitedBoundary",
            managed_policy_name="ReadRecallDevLimitedBoundary",
            document=iam.PolicyDocument.from_json({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Deny",
                        "Action": ["cloudformation:*"],
                        "Resource": "*"
                    },
                    {
                        "Effect": "Deny",
                        "Action": [
                            "s3:Create*", "s3:Delete*", "s3:Put*",
                            "dynamodb:Create*", "dynamodb:Delete*", "dynamodb:Put*",
                            "sqs:Create*", "sqs:Delete*", "sqs:Set*",
                            "apigateway:Create*", "apigateway:Delete*", "apigateway:PUT*"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Effect": "Allow",
                        "NotAction": [
                            "cloudformation:*",
                            "iam:*",
                            "organizations:*",
                            "account:*"
                        ],
                        "Resource": "*"
                    }
                ]
            })
        )

        dev_limited_role = iam.Role(
            self, "ReadRecallDevLimited",
            role_name="ReadRecallDevLimited",
            assumed_by=iam.AccountPrincipal(self.account),
            description="Limited role for developers to update Lambda code only",
            permissions_boundary=dev_boundary
        )

        # Add allowed actions for developers
        dev_policy = iam.ManagedPolicy(
            self, "ReadRecallDevLimitedPolicy",
            managed_policy_name="ReadRecallDevLimitedPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "lambda:UpdateFunctionCode",
                        "lambda:GetFunction",
                        "lambda:ListFunctions"
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:DescribeLogStreams",
                        "logs:GetLogEvents",
                        "logs:FilterLogEvents"
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:GetParameter"],
                    resources=["*"]
                )
            ]
        )

        dev_limited_role.add_managed_policy(dev_policy)

        # Outputs for reference
        CfnOutput(
            self, "InfraCIRoleArn",
            value=infra_ci_role.role_arn,
            description="ARN of the ReadRecallInfraCI role for CI/CD"
        )

        CfnOutput(
            self, "DevLimitedRoleArn",
            value=dev_limited_role.role_arn,
            description="ARN of the ReadRecallDevLimited role for developers"
        )
