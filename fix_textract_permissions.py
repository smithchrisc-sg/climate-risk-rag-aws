#!/usr/bin/env python3
"""
Diagnose and fix Textract permissions issues
"""

import boto3
import json
import os

def check_current_permissions():
    """Check current IAM permissions for Textract"""
    
    print("Checking Current IAM Permissions")
    print("=" * 50)
    
    session = boto3.Session(profile_name='solve-global')
    
    # Get current user identity
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    
    print(f"Current User: {identity.get('Arn')}")
    print(f"Account: {identity.get('Account')}")
    
    # Check IAM policies
    iam = session.client('iam')
    
    try:
        # Get user name from ARN
        user_arn = identity.get('Arn')
        if ':user/' in user_arn:
            username = user_arn.split(':user/')[-1]
            
            print(f"\nChecking policies for user: {username}")
            
            # Get attached user policies
            user_policies = iam.list_attached_user_policies(UserName=username)
            print(f"Attached policies: {len(user_policies['AttachedPolicies'])}")
            
            for policy in user_policies['AttachedPolicies']:
                print(f"  - {policy['PolicyName']} ({policy['PolicyArn']})")
            
            # Get inline user policies
            inline_policies = iam.list_user_policies(UserName=username)
            if inline_policies['PolicyNames']:
                print(f"Inline policies: {len(inline_policies['PolicyNames'])}")
                for policy_name in inline_policies['PolicyNames']:
                    print(f"  - {policy_name}")
            
            # Check groups
            user_groups = iam.get_groups_for_user(UserName=username)
            if user_groups['Groups']:
                print(f"Member of groups: {len(user_groups['Groups'])}")
                for group in user_groups['Groups']:
                    print(f"  - {group['GroupName']}")
                    
                    # Check group policies
                    group_policies = iam.list_attached_group_policies(GroupName=group['GroupName'])
                    for policy in group_policies['AttachedPolicies']:
                        print(f"    Policy: {policy['PolicyName']}")
            
    except Exception as e:
        print(f"Could not check IAM details: {str(e)}")

def test_textract_with_s3_bucket():
    """Test Textract with explicit S3 bucket access"""
    
    print(f"\n" + "="*50)
    print("Testing Textract with S3 Bucket Access")
    print("="*50)
    
    session = boto3.Session(profile_name='solve-global')
    textract = session.client('textract', region_name='us-east-1')
    s3 = session.client('s3', region_name='us-east-1')
    
    # Test bucket for Textract
    test_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'
    test_key = 'textract-test/sample.pdf'
    
    # Upload a simple test PDF
    print("1. Creating and uploading test PDF...")
    
    try:
        # Create simple PDF content
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import tempfile
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        c = canvas.Canvas(temp_file.name, pagesize=letter)
        c.drawString(100, 750, "Test PDF for Textract permissions")
        c.drawString(100, 730, "This should work if permissions are correct")
        c.showPage()
        c.save()
        
        # Upload to S3
        with open(temp_file.name, 'rb') as f:
            s3.put_object(
                Bucket=test_bucket,
                Key=test_key,
                Body=f.read(),
                ContentType='application/pdf'
            )
        
        print(f"✅ Uploaded test PDF to s3://{test_bucket}/{test_key}")
        
        # Clean up local file
        os.unlink(temp_file.name)
        
    except Exception as e:
        print(f"❌ Failed to upload test PDF: {str(e)}")
        return False
    
    # Test Textract with S3 reference
    print("2. Testing Textract with S3 reference...")
    
    try:
        response = textract.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': test_bucket,
                    'Name': test_key
                }
            }
        )
        
        blocks = response.get('Blocks', [])
        lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
        
        print(f"✅ SUCCESS! Textract extracted {len(lines)} lines via S3")
        for line in lines:
            print(f"   - {line}")
        
        # Clean up test file
        s3.delete_object(Bucket=test_bucket, Key=test_key)
        print("🧹 Cleaned up test file")
        
        return True
        
    except Exception as e:
        print(f"❌ Textract failed with S3 reference: {str(e)}")
        
        # Try with bytes instead
        print("3. Testing Textract with direct bytes...")
        
        try:
            obj = s3.get_object(Bucket=test_bucket, Key=test_key)
            pdf_bytes = obj['Body'].read()
            
            response = textract.detect_document_text(
                Document={'Bytes': pdf_bytes}
            )
            
            blocks = response.get('Blocks', [])
            lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
            
            print(f"✅ SUCCESS! Textract extracted {len(lines)} lines via bytes")
            
            # Clean up
            s3.delete_object(Bucket=test_bucket, Key=test_key)
            
            return True
            
        except Exception as bytes_error:
            print(f"❌ Textract also failed with bytes: {str(bytes_error)}")
            
            # Clean up
            try:
                s3.delete_object(Bucket=test_bucket, Key=test_key)
            except:
                pass
            
            return False

def suggest_permission_fixes():
    """Suggest permission fixes based on the issue"""
    
    print(f"\n" + "="*50)
    print("PERMISSION FIX RECOMMENDATIONS")
    print("="*50)
    
    print("Based on the console working but API failing, you likely need:")
    print()
    print("1. TEXTRACT SERVICE PERMISSIONS:")
    print("   - textract:DetectDocumentText")
    print("   - textract:AnalyzeDocument")
    print("   - textract:StartDocumentTextDetection")
    print("   - textract:GetDocumentTextDetection")
    print()
    print("2. S3 PERMISSIONS FOR TEXTRACT:")
    print("   - s3:GetObject (on source buckets)")
    print("   - s3:PutObject (on result buckets)")
    print("   - s3:CreateBucket (if Textract needs temp buckets)")
    print()
    print("3. IAM ROLE/POLICY EXAMPLE:")
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "textract:*"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:CreateBucket",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::solve-global-kr-*",
                    "arn:aws:s3:::solve-global-kr-*/*"
                ]
            }
        ]
    }
    
    print(json.dumps(policy, indent=2))
    
    print(f"\n4. NEXT STEPS:")
    print("   a. Add the above policy to your IAM user/role")
    print("   b. Wait 5-10 minutes for permissions to propagate")
    print("   c. Test again with our scripts")
    print("   d. If still failing, check CloudTrail logs for specific permission denials")

if __name__ == "__main__":
    print("Textract Permissions Diagnostic")
    print("=" * 60)
    
    # Check current permissions
    check_current_permissions()
    
    # Test with proper S3 setup
    success = test_textract_with_s3_bucket()
    
    if not success:
        suggest_permission_fixes()
    else:
        print(f"\n✅ PERMISSIONS APPEAR TO BE WORKING!")
        print("The issue may have been resolved, or it's intermittent.")
        
        # Now test with a real-world PDF
        print(f"\nTesting with real-world PDF...")
        
        test_pdf = "/Users/chris/climate-risk-rag-aws/test_pdfs/Dynamic Evolving Neural-Fuzzy Inference System for Rainfall-Runoff Modelling.pdf"
        
        if os.path.exists(test_pdf):
            session = boto3.Session(profile_name='solve-global')
            textract = session.client('textract', region_name='us-east-1')
            
            try:
                with open(test_pdf, 'rb') as f:
                    pdf_bytes = f.read()
                
                response = textract.detect_document_text(
                    Document={'Bytes': pdf_bytes}
                )
                
                blocks = response.get('Blocks', [])
                lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
                
                print(f"🎉 BREAKTHROUGH! Real PDF now works: {len(lines)} lines extracted!")
                
            except Exception as e:
                print(f"❌ Real PDF still fails: {str(e)}")
                print("Permissions may be partially fixed but not complete.")
