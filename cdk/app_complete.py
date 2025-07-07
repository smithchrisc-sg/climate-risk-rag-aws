#!/usr/bin/env python3
"""
AWS CDK App for Climate Risk RAG System - Complete Version
Includes all TextExtractor infrastructure with proper dependencies
Captures all manual configurations for complete deployment from scratch
"""

import aws_cdk as cdk
from constructs import Construct
from stacks.networking_stack import NetworkingStack
from stacks.data_lake_stack import DataLakeStack
from stacks.data_stack import DataStack
from stacks.ai_ml_stack import AiMlStack
from stacks.microservices_compute_stack import MicroservicesComputeStack
from stacks.notifications_stack import NotificationsStack
from stacks.textextractor_messaging_stack_complete import TextExtractorMessagingStackComplete
from stacks.textextractor_lambda_stack_complete import TextExtractorLambdaStackComplete

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=app.node.try_get_context("account") or "861276078413",
    region=app.node.try_get_context("region") or "us-east-1"
)

# Stack naming prefix
project_name = "solve-global-kr-rag"

# Networking stack (VPC, subnets, security groups)
networking_stack = NetworkingStack(
    app, 
    f"{project_name}-networking",
    env=env,
    description="Networking infrastructure for Climate Risk RAG system"
)

# Data Lake stack (S3 buckets for microservices data lake)
data_lake_stack = DataLakeStack(
    app,
    f"{project_name}-data-lake",
    env=env,
    description="Data lake infrastructure with S3 buckets for microservices architecture"
)

# Data stack (OpenSearch, Neptune, RDS)
data_stack = DataStack(
    app,
    f"{project_name}-data",
    vpc=networking_stack.vpc,
    env=env,
    description="Data layer infrastructure (OpenSearch, Neptune, RDS)"
)

# AI/ML stack (Bedrock permissions, model access)
ai_ml_stack = AiMlStack(
    app,
    f"{project_name}-ai-ml",
    env=env,
    description="AI/ML services configuration and permissions"
)

# TextExtractor Messaging stack (SNS/SQS + Security Groups for async processing)
textextractor_messaging_stack = TextExtractorMessagingStackComplete(
    app,
    f"{project_name}-textextractor-messaging",
    vpc=networking_stack.vpc,
    rds_security_group_id=data_stack.database_security_group.security_group_id,
    env=env,
    description="Complete SNS/SQS messaging infrastructure for TextExtractor async processing"
)

# TextExtractor Lambda stack (Lambda functions with VPC configuration)
textextractor_lambda_stack = TextExtractorLambdaStackComplete(
    app,
    f"{project_name}-textextractor-lambda",
    vpc=networking_stack.vpc,
    messaging_stack=textextractor_messaging_stack,
    database_url="postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require",
    env=env,
    description="Complete Lambda functions for async TextExtractor document processing"
)

# Prepare bucket names
bucket_names = {
    "documents": f"solve-global-kr-documents-{env.account}-{env.region}",
    "extracted_text": f"solve-global-kr-text-{env.account}-{env.region}",
    "chunks": f"solve-global-kr-chunks-{env.account}-{env.region}",
    "embeddings": f"solve-global-kr-embeddings-{env.account}-{env.region}",
    "ner_results": f"solve-global-kr-ner-{env.account}-{env.region}",
    "knowledge_graph": f"solve-global-kr-kg-data-{env.account}-{env.region}",
    "processing_metadata": f"solve-global-kr-cache-{env.account}-{env.region}"
}

# Microservices Compute stack (Lambda functions, API Gateway, Step Functions)
microservices_compute_stack = MicroservicesComputeStack(
    app,
    f"{project_name}-microservices-compute",
    vpc=networking_stack.vpc,
    bucket_names=bucket_names,
    data_resources=data_stack,
    ai_ml_resources=ai_ml_stack,
    env=env,
    description="Microservices compute infrastructure (Lambda functions, API Gateway)"
)

# Notifications stack (S3 event notifications)
notifications_stack = NotificationsStack(
    app,
    f"{project_name}-notifications",
    data_lake_stack=data_lake_stack,
    compute_stack=microservices_compute_stack,
    env=env,
    description="S3 event notifications for data processing pipeline"
)

# Add dependencies (proper order for deployment)
data_lake_stack.add_dependency(networking_stack)
data_stack.add_dependency(networking_stack)
textextractor_messaging_stack.add_dependency(networking_stack)
textextractor_messaging_stack.add_dependency(data_stack)
textextractor_lambda_stack.add_dependency(textextractor_messaging_stack)
textextractor_lambda_stack.add_dependency(networking_stack)
textextractor_lambda_stack.add_dependency(data_stack)
microservices_compute_stack.add_dependency(data_stack)
microservices_compute_stack.add_dependency(ai_ml_stack)
notifications_stack.add_dependency(data_lake_stack)
notifications_stack.add_dependency(microservices_compute_stack)

app.synth()
