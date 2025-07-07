#!/usr/bin/env python3
"""
Configure Lambda VPC Settings
Add VPC configuration to TextExtractor Lambda functions for RDS access
"""

import json
import subprocess
import time

def run_aws_command(cmd):
    """Run AWS CLI command"""
    full_cmd = f"AWS_PROFILE=solve-global AWS_DEFAULT_REGION=us-east-1 {cmd} --region us-east-1"
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {result.stderr}")
        raise Exception(f"Command failed: {result.stderr}")
    return result.stdout.strip()

def wait_for_function_update(function_name, max_wait=300):
    """Wait for Lambda function to be ready for updates"""
    print(f"⏳ Waiting for {function_name} to be ready...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            state = run_aws_command(f"aws lambda get-function --function-name {function_name} --query 'Configuration.State'")
            state = state.strip('"')
            
            if state == "Active":
                print(f"✅ {function_name} is ready")
                return True
            elif state in ["Pending", "Inactive"]:
                print(f"   State: {state}, waiting...")
                time.sleep(10)
            else:
                print(f"⚠️  Unexpected state: {state}")
                time.sleep(10)
                
        except Exception as e:
            print(f"   Error checking state: {e}")
            time.sleep(10)
    
    print(f"❌ Timeout waiting for {function_name}")
    return False

def configure_lambda_vpc(function_name, subnet_ids, security_group_ids):
    """Configure Lambda function VPC settings"""
    print(f"🔧 Configuring VPC for {function_name}...")
    
    # Wait for function to be ready
    if not wait_for_function_update(function_name):
        raise Exception(f"Function {function_name} not ready for updates")
    
    # Configure VPC
    subnets = ",".join(subnet_ids)
    security_groups = ",".join(security_group_ids)
    
    try:
        run_aws_command(f"""aws lambda update-function-configuration \\
            --function-name {function_name} \\
            --vpc-config SubnetIds={subnets},SecurityGroupIds={security_groups}""")
        
        print(f"✅ VPC configured for {function_name}")
        
        # Wait for update to complete
        wait_for_function_update(function_name)
        
    except Exception as e:
        print(f"❌ Failed to configure VPC for {function_name}: {e}")
        raise

def create_lambda_security_group():
    """Create security group for Lambda functions"""
    print("🔧 Creating security group for Lambda functions...")
    
    try:
        # Create security group
        result = run_aws_command("""aws ec2 create-security-group \\
            --group-name solve-global-kr-lambda-sg \\
            --description "Security group for TextExtractor Lambda functions" \\
            --vpc-id vpc-051c21d88c7dc3819""")
        
        sg_data = json.loads(result)
        sg_id = sg_data['GroupId']
        print(f"✅ Created security group: {sg_id}")
        
        # Add outbound rule for RDS (PostgreSQL)
        run_aws_command(f"""aws ec2 authorize-security-group-egress \\
            --group-id {sg_id} \\
            --protocol tcp \\
            --port 5432 \\
            --source-group sg-09bc56a537bf7ac12""")
        
        # Add outbound rule for HTTPS (for AWS API calls)
        run_aws_command(f"""aws ec2 authorize-security-group-egress \\
            --group-id {sg_id} \\
            --protocol tcp \\
            --port 443 \\
            --cidr 0.0.0.0/0""")
        
        print(f"✅ Security group rules configured")
        return sg_id
        
    except Exception as e:
        if "already exists" in str(e):
            print("⚠️  Security group already exists, getting ID...")
            result = run_aws_command("""aws ec2 describe-security-groups \\
                --group-names solve-global-kr-lambda-sg \\
                --query 'SecurityGroups[0].GroupId'""")
            sg_id = result.strip('"')
            print(f"✅ Using existing security group: {sg_id}")
            return sg_id
        else:
            raise

def update_rds_security_group(lambda_sg_id):
    """Update RDS security group to allow Lambda access"""
    print("🔧 Updating RDS security group for Lambda access...")
    
    try:
        # Add inbound rule to RDS security group for Lambda
        run_aws_command(f"""aws ec2 authorize-security-group-ingress \\
            --group-id sg-09bc56a537bf7ac12 \\
            --protocol tcp \\
            --port 5432 \\
            --source-group {lambda_sg_id}""")
        
        print("✅ RDS security group updated")
        
    except Exception as e:
        if "already exists" in str(e):
            print("⚠️  Security group rule already exists")
        else:
            print(f"❌ Failed to update RDS security group: {e}")

def main():
    """Configure Lambda VPC settings"""
    print("🔧 Configuring TextExtractor Lambda VPC Settings")
    print("=" * 50)
    
    # VPC Configuration
    vpc_id = "vpc-051c21d88c7dc3819"
    private_subnets = ["subnet-03d8bd6cf3491f38c", "subnet-0c0be1dd59f70f70e"]
    rds_security_group = "sg-09bc56a537bf7ac12"
    
    print(f"VPC ID: {vpc_id}")
    print(f"Private Subnets: {', '.join(private_subnets)}")
    print(f"RDS Security Group: {rds_security_group}")
    
    # Create Lambda security group
    lambda_sg_id = create_lambda_security_group()
    
    # Update RDS security group
    update_rds_security_group(lambda_sg_id)
    
    # Configure Lambda functions
    lambda_functions = [
        "solve-global-kr-textextractor-initiator",
        "solve-global-kr-textextractor-processor"
    ]
    
    for function_name in lambda_functions:
        print(f"\\n🔧 Configuring {function_name}")
        configure_lambda_vpc(function_name, private_subnets, [lambda_sg_id])
    
    print("\\n🎉 VPC Configuration Complete!")
    print("\\n📋 Summary:")
    print(f"   Lambda Security Group: {lambda_sg_id}")
    print(f"   VPC: {vpc_id}")
    print(f"   Subnets: {', '.join(private_subnets)}")
    print(f"   Functions configured: {len(lambda_functions)}")
    
    print("\\n🧪 Test the pipeline:")
    print("   AWS_PROFILE=solve-global aws lambda invoke --function-name solve-global-kr-textextractor-trigger --region us-east-1 /tmp/vpc-test.json")

if __name__ == "__main__":
    main()
