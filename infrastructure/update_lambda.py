#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess

def parse_args():
    parser = argparse.ArgumentParser(description="Update Lambda function code only using CDK hotswap")
    parser.add_argument("function_name", help="Name of the Lambda function to update")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Activate virtual environment if not already activated
    if "VIRTUAL_ENV" not in os.environ:
        print("Activating virtual environment...")
        # This script will be run with the virtual env's Python if called properly
        # but we'll add a note for users
        print("NOTE: Make sure to run this script from within the virtual environment:")
        print("  source .venv/bin/activate && python update_lambda.py <function-name>")
    
    # Get absolute path to infrastructure directory
    infra_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"\nUpdating Lambda function: {args.function_name}")
    print("Using CDK hotswap to bypass CloudFormation for faster deployment...\n")
    
    # Run the CDK hotswap command
    try:
        # Set to current directory as the infrastructure directory
        os.chdir(infra_dir)
        
        # Execute the CDK hotswap command
        cmd = ["cdk", "deploy", "--hotswap", "ReadRecallStack"]
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            print(f"\n✅ Successfully updated Lambda function: {args.function_name}")
        else:
            print(f"\n❌ Failed to update Lambda function: {args.function_name}")
            return 1
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error executing CDK command: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
