/**
 * CDK Changes for Database Layer Standardization
 * Implements standardized database access across all Lambda functions
 */

import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export class DatabaseLayerStandardization extends Construct {
  public readonly databaseCoreLayer: lambda.LayerVersion;
  public readonly databaseAccessSecurityGroup: ec2.SecurityGroup;
  public readonly standardDatabaseEnv: { [key: string]: string };
  public readonly standardVpcConfig: lambda.VpcConfig;

  constructor(
    scope: Construct,
    id: string,
    props: {
      vpc: ec2.Vpc;
      rdsInstance: rds.DatabaseInstance;
      databaseSecret: secretsmanager.Secret;
      privateSubnets: ec2.Subnet[];
    }
  ) {
    super(scope, id);

    // 1. Create Database Core Layer
    this.databaseCoreLayer = new lambda.LayerVersion(this, 'DatabaseCoreLayer', {
      code: lambda.Code.fromAsset('layers/database-core-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Core database utilities (DatabaseManager, DocumentIDManager)',
      layerVersionName: 'database-core-layer'
    });

    // 2. Create Standard Security Group for Database Access
    this.databaseAccessSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseAccessSG', {
      vpc: props.vpc,
      description: 'Standard security group for Lambda functions accessing RDS database',
      securityGroupName: 'lambda-database-access'
    });

    // Allow outbound to RDS
    this.databaseAccessSecurityGroup.addEgressRule(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.tcp(5432),
      'Allow outbound to RDS PostgreSQL'
    );

    // Update RDS security group to allow Lambda access
    const rdsSecurityGroup = props.rdsInstance.connections.securityGroups[0];
    rdsSecurityGroup.addIngressRule(
      this.databaseAccessSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow Lambda database access'
    );

    // 3. Define Standard Database Environment Variables
    this.standardDatabaseEnv = {
      DATABASE_SECRET_NAME: props.databaseSecret.secretName,
      DB_HOST: props.rdsInstance.instanceEndpoint.hostname,
      DB_NAME: 'climate_risk_rag',
      DB_PORT: '5432',
      DATABASE_CONNECTION_METHOD: 'secrets_manager'
    };

    // 4. Define Standard VPC Configuration
    this.standardVpcConfig = {
      vpc: props.vpc,
      securityGroups: [this.databaseAccessSecurityGroup],
      vpcSubnets: {
        subnets: props.privateSubnets
      }
    };

    // Grant secrets access to the security group (for Lambda functions)
    props.databaseSecret.grantRead(this.databaseAccessSecurityGroup);
  }

  /**
   * Create standardized Lambda function with database access
   */
  public createStandardLambdaFunction(
    id: string,
    props: {
      functionName: string;
      code: lambda.Code;
      handler: string;
      additionalLayers?: lambda.ILayerVersion[];
      additionalEnvironment?: { [key: string]: string };
      timeout?: Duration;
      memorySize?: number;
    }
  ): lambda.Function {
    
    // Combine standard database layer with additional layers
    const layers = [this.databaseCoreLayer];
    if (props.additionalLayers) {
      layers.push(...props.additionalLayers);
    }

    // Combine standard database environment with additional environment
    const environment = { ...this.standardDatabaseEnv };
    if (props.additionalEnvironment) {
      Object.assign(environment, props.additionalEnvironment);
    }

    return new lambda.Function(this, id, {
      functionName: props.functionName,
      runtime: lambda.Runtime.PYTHON_3_11,
      code: props.code,
      handler: props.handler,
      layers: layers,
      environment: environment,
      vpc: this.standardVpcConfig.vpc,
      securityGroups: this.standardVpcConfig.securityGroups,
      vpcSubnets: this.standardVpcConfig.vpcSubnets,
      timeout: props.timeout,
      memorySize: props.memorySize
    });
  }
}

/**
 * Example usage in main CDK stack
 */
export class ClimateRiskRagStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // Existing resources
    const vpc = ec2.Vpc.fromLookup(this, 'ExistingVpc', { vpcId: 'vpc-051c21d88c7dc3819' });
    const rdsInstance = rds.DatabaseInstance.fromDatabaseInstanceAttributes(this, 'ExistingRDS', {
      instanceIdentifier: 'solve-global-kr-rag-data-postgresqldatabase03fc658',
      instanceEndpointAddress: 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
      port: 5432,
      securityGroups: []
    });
    const databaseSecret = secretsmanager.Secret.fromSecretNameV2(this, 'DatabaseSecret', 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863');

    // Create database layer standardization
    const dbStandardization = new DatabaseLayerStandardization(this, 'DatabaseStandardization', {
      vpc,
      rdsInstance,
      databaseSecret,
      privateSubnets: [
        ec2.Subnet.fromSubnetId(this, 'PrivateSubnet1', 'subnet-03d8bd6cf3491f38c'),
        ec2.Subnet.fromSubnetId(this, 'PrivateSubnet2', 'subnet-0c0be1dd59f70f70e')
      ]
    });

    // Create standardized Lambda functions
    
    // 1. Pipeline Test Function
    const pipelineTestFunction = dbStandardization.createStandardLambdaFunction('PipelineTestFunction', {
      functionName: 'solve-global-kr-pipeline-test-function',
      code: lambda.Code.fromAsset('lambda/pipeline_test_function'),
      handler: 'pipeline_test_handler.lambda_handler',
      additionalEnvironment: {
        SQLITE_DB_PATH: '/tmp/corpus_document_ids.db'
      },
      timeout: Duration.minutes(15),
      memorySize: 1024
    });

    // 2. Cleanup Service Function
    const cleanupServiceFunction = dbStandardization.createStandardLambdaFunction('CleanupServiceFunction', {
      functionName: 'solve-global-kr-cleanup-service',
      code: lambda.Code.fromAsset('lambda/cleanup_service'),
      handler: 'cleanup_service.lambda_handler',
      additionalLayers: [
        // Add OpenSearch layer for cleanup service
        lambda.LayerVersion.fromLayerVersionArn(this, 'OpenSearchLayer', 'arn:aws:lambda:us-east-1:861276078413:layer:opensearch-dependencies:2')
      ],
      additionalEnvironment: {
        OPENSEARCH_VECTOR_ENDPOINT: 'https://rui72a7agqnqo77vk34b.us-east-1.aoss.amazonaws.com',
        OPENSEARCH_KEYWORD_ENDPOINT: 'https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com',
        NEPTUNE_ENDPOINT: 'solve-global-kr-neptune-instance.cqhsckw0edl1.us-east-1.neptune.amazonaws.com',
        NEPTUNE_PORT: '8182',
        AWS_ACCOUNT_ID: this.account
      },
      timeout: Duration.minutes(5),
      memorySize: 1024
    });

    // 3. Text Chunker Function
    const textChunkerFunction = dbStandardization.createStandardLambdaFunction('TextChunkerFunction', {
      functionName: 'text-chunker-pipeline',
      code: lambda.Code.fromAsset('lambda/text_chunker'),
      handler: 'text_chunker.lambda_handler',
      additionalEnvironment: {
        NLP_PROCESSOR_TOPIC_ARN: 'arn:aws:sns:us-east-1:861276078413:nlp-processor'
      },
      timeout: Duration.minutes(15),
      memorySize: 1024
    });

    // 4. NLP Processor Function
    const nlpProcessorFunction = dbStandardization.createStandardLambdaFunction('NlpProcessorFunction', {
      functionName: 'nlp-processor',
      code: lambda.Code.fromAsset('lambda/nlp_processor'),
      handler: 'nlp_processor.lambda_handler',
      additionalEnvironment: {
        NLP_WORKER_TOPIC_ARN: 'arn:aws:sns:us-east-1:861276078413:nlp-worker'
      },
      timeout: Duration.minutes(1),
      memorySize: 512
    });

    // 5. NLP Worker Function
    const nlpWorkerFunction = dbStandardization.createStandardLambdaFunction('NlpWorkerFunction', {
      functionName: 'nlp-worker',
      code: lambda.Code.fromAsset('lambda/nlp_worker'),
      handler: 'nlp_worker.lambda_handler',
      timeout: Duration.minutes(15),
      memorySize: 2048
    });

    // 6. Vector Embeddings Processor
    const vectorEmbeddingsProcessorFunction = dbStandardization.createStandardLambdaFunction('VectorEmbeddingsProcessorFunction', {
      functionName: 'vector-embeddings-processor',
      code: lambda.Code.fromAsset('lambda/vector_embeddings_processor'),
      handler: 'vector_embeddings_processor.lambda_handler',
      additionalEnvironment: {
        VECTOR_WORKER_TOPIC_ARN: 'arn:aws:sns:us-east-1:861276078413:vector-embeddings-worker'
      },
      timeout: Duration.minutes(1),
      memorySize: 512
    });

    // 7. Vector Embeddings Worker
    const vectorEmbeddingsWorkerFunction = dbStandardization.createStandardLambdaFunction('VectorEmbeddingsWorkerFunction', {
      functionName: 'vector-embeddings-worker',
      code: lambda.Code.fromAsset('lambda/vector_embeddings_worker'),
      handler: 'vector_embeddings_worker.lambda_handler',
      additionalLayers: [
        // Add numpy layer for vector operations
        lambda.LayerVersion.fromLayerVersionArn(this, 'NumpyLayer', 'arn:aws:lambda:us-east-1:861276078413:layer:numpy-dependencies-lambda:1')
      ],
      timeout: Duration.minutes(15),
      memorySize: 2048
    });
  }
}

/**
 * Migration script for existing functions
 */
export class DatabaseLayerMigration {
  
  /**
   * Migrate existing Lambda function to use standardized database layer
   */
  static async migrateLambdaFunction(
    lambdaClient: AWS.Lambda,
    functionName: string,
    newLayerArn: string,
    standardEnvironment: { [key: string]: string },
    standardVpcConfig: AWS.Lambda.VpcConfig
  ): Promise<void> {
    
    // Get current function configuration
    const currentConfig = await lambdaClient.getFunctionConfiguration({ FunctionName: functionName }).promise();
    
    // Update layers - remove old database layers, add new core layer
    const currentLayers = currentConfig.Layers?.map(layer => layer.Arn) || [];
    const updatedLayers = currentLayers.filter(layer => 
      !layer.includes('database-dependencies') && 
      !layer.includes('climate-risk-core-utilities')
    );
    updatedLayers.push(newLayerArn);
    
    // Update environment variables
    const currentEnv = currentConfig.Environment?.Variables || {};
    const updatedEnv = { ...currentEnv, ...standardEnvironment };
    
    // Remove old DATABASE_URL if present
    delete updatedEnv.DATABASE_URL;
    
    // Update function configuration
    await lambdaClient.updateFunctionConfiguration({
      FunctionName: functionName,
      Layers: updatedLayers,
      Environment: { Variables: updatedEnv },
      VpcConfig: standardVpcConfig
    }).promise();
    
    console.log(`✅ Migrated ${functionName} to standardized database layer`);
  }
}

/**
 * Standard import template for Lambda functions
 */
export const STANDARD_DATABASE_IMPORTS = `
# Standard database imports (identical across all functions)
import logging

# Configure logging
logger = logging.getLogger(__name__)

try:
    from utils.DatabaseManager import DatabaseManager
    from utils.DocumentIDManager import DocumentIDManager
    from utils.database_config import validate_database_environment, log_database_configuration
    logger.info("Database utilities imported successfully")
    
    # Log database configuration (without sensitive data)
    log_database_configuration()
    
except ImportError as e:
    logger.error(f"Failed to import database utilities: {e}")
    raise ImportError(f"Database utilities import failed: {e}")

# Initialize database managers
try:
    db_manager = DatabaseManager()
    doc_id_manager = DocumentIDManager(db_manager)
    logger.info("Database managers initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database managers: {e}")
    raise
`;

/**
 * Standard environment variables template
 */
export const STANDARD_DATABASE_ENV_TEMPLATE = {
  DATABASE_SECRET_NAME: 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863',
  DB_HOST: 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
  DB_NAME: 'climate_risk_rag',
  DB_PORT: '5432',
  DATABASE_CONNECTION_METHOD: 'secrets_manager'
};
