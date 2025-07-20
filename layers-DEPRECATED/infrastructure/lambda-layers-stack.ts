import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface LambdaLayersStackProps extends cdk.StackProps {
  readonly layerPrefix?: string;
  readonly environment?: string;
}

export class LambdaLayersStack extends cdk.Stack {
  public readonly layers: { [key: string]: lambda.LayerVersion };
  public readonly layerArns: { [key: string]: string };

  constructor(scope: Construct, id: string, props: LambdaLayersStackProps = {}) {
    super(scope, id, props);

    const layerPrefix = props.layerPrefix || 'climate-risk-rag';
    const environment = props.environment || 'dev';

    this.layers = {};
    this.layerArns = {};

    // Foundation Layers (Third-party dependencies)
    
    // Layer 1: AWS Core Foundation
    this.layers.awsCore = new lambda.LayerVersion(this, 'AwsCoreLayer', {
      layerVersionName: `${layerPrefix}-aws-core-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/aws-core-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'AWS SDK and core utilities used by all functions',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 2: Data Processing Foundation
    this.layers.dataProcessing = new lambda.LayerVersion(this, 'DataProcessingLayer', {
      layerVersionName: `${layerPrefix}-data-processing-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/data-processing-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'NumPy, Pandas, SciPy for data processing',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 3: Database Connectivity
    this.layers.database = new lambda.LayerVersion(this, 'DatabaseLayer', {
      layerVersionName: `${layerPrefix}-database-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/database-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Database connectivity (PostgreSQL, OpenSearch, Redis)',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 4: NLP Core
    this.layers.nlpCore = new lambda.LayerVersion(this, 'NlpCoreLayer', {
      layerVersionName: `${layerPrefix}-nlp-core-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/nlp-core-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Core NLP libraries without models',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 5: PyTorch Foundation
    this.layers.pytorch = new lambda.LayerVersion(this, 'PytorchLayer', {
      layerVersionName: `${layerPrefix}-pytorch-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/pytorch-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'PyTorch framework for ML inference',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 6: Knowledge Graph
    this.layers.knowledgeGraph = new lambda.LayerVersion(this, 'KnowledgeGraphLayer', {
      layerVersionName: `${layerPrefix}-knowledge-graph-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/knowledge-graph-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'RDF, SPARQL, and ontology processing',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 7: Web & Template Processing
    this.layers.webTemplate = new lambda.LayerVersion(this, 'WebTemplateLayer', {
      layerVersionName: `${layerPrefix}-web-template-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/web-template-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Web scraping and templating',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 8: Specialized NLP Models
    this.layers.nlpModels = new lambda.LayerVersion(this, 'NlpModelsLayer', {
      layerVersionName: `${layerPrefix}-nlp-models-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/nlp-models-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Pre-trained NLP models and specialized tools',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Application Layers (Shared application code)

    // Layer 9: Climate Risk Core Utilities
    this.layers.climateRiskCore = new lambda.LayerVersion(this, 'ClimateRiskCoreLayer', {
      layerVersionName: `${layerPrefix}-core-utilities-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/climate-risk-core-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Core application utilities (DocumentIDManager, DatabaseManager, etc.)',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 10: Knowledge Graph Shared Components
    this.layers.kgShared = new lambda.LayerVersion(this, 'KgSharedLayer', {
      layerVersionName: `${layerPrefix}-kg-shared-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/kg-shared-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Knowledge graph shared components and utilities',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Layer 11: RAG System Shared Components
    this.layers.ragShared = new lambda.LayerVersion(this, 'RagSharedLayer', {
      layerVersionName: `${layerPrefix}-rag-shared-${environment}`,
      code: lambda.Code.fromAsset('../built-layers/rag-shared-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'RAG system shared components and base classes',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Store layer ARNs for easy reference
    Object.entries(this.layers).forEach(([key, layer]) => {
      this.layerArns[key] = layer.layerVersionArn;
    });

    // Create IAM role for Lambda functions using these layers
    const lambdaExecutionRole = new iam.Role(this, 'LayerAwareLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
      ],
      inlinePolicies: {
        LayerAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'lambda:GetLayerVersion',
                'lambda:ListLayerVersions',
              ],
              resources: Object.values(this.layers).map(layer => layer.layerVersionArn),
            }),
          ],
        }),
      },
    });

    // Outputs for all layer ARNs
    Object.entries(this.layers).forEach(([key, layer]) => {
      new cdk.CfnOutput(this, `${key}LayerArn`, {
        value: layer.layerVersionArn,
        description: `ARN for ${key} layer`,
        exportName: `${layerPrefix}-${key}-layer-arn-${environment}`,
      });
    });

    // Output the execution role ARN
    new cdk.CfnOutput(this, 'LambdaExecutionRoleArn', {
      value: lambdaExecutionRole.roleArn,
      description: 'ARN for Lambda execution role with layer access',
      exportName: `${layerPrefix}-lambda-execution-role-arn-${environment}`,
    });

    // Create a summary output with all layer information
    const layerSummary = Object.entries(this.layers).map(([key, layer]) => ({
      name: key,
      arn: layer.layerVersionArn,
      version: layer.layerVersionArn.split(':').pop(),
    }));

    new cdk.CfnOutput(this, 'LayerSummary', {
      value: JSON.stringify(layerSummary, null, 2),
      description: 'Summary of all deployed layers',
    });

    // Tags
    cdk.Tags.of(this).add('Project', 'ClimateRiskRAG');
    cdk.Tags.of(this).add('Component', 'LambdaLayers');
    cdk.Tags.of(this).add('Environment', environment);
  }

  /**
   * Get layer combinations for specific function types
   */
  public getLayersForFunction(functionType: string): lambda.ILayerVersion[] {
    const layerCombinations: { [key: string]: lambda.ILayerVersion[] } = {
      // Text Processing Functions
      'textExtractorInitiator': [
        this.layers.awsCore,
        this.layers.database,
        this.layers.climateRiskCore,
      ],
      'textExtractorProcessor': [
        this.layers.awsCore,
        this.layers.database,
        this.layers.dataProcessing,
        this.layers.climateRiskCore,
      ],
      'textChunker': [
        this.layers.awsCore,
        this.layers.dataProcessing,
        this.layers.nlpCore,
        this.layers.climateRiskCore,
      ],

      // ML Functions
      'embeddingGenerator': [
        this.layers.awsCore,
        this.layers.dataProcessing,
        this.layers.database,
        this.layers.pytorch,
        this.layers.nlpModels,
        this.layers.climateRiskCore,
      ],
      'nerProcessor': [
        this.layers.awsCore,
        this.layers.dataProcessing,
        this.layers.nlpCore,
        this.layers.pytorch,
        this.layers.nlpModels,
        this.layers.climateRiskCore,
      ],

      // Knowledge Graph Functions
      'entityExtractor': [
        this.layers.awsCore,
        this.layers.dataProcessing,
        this.layers.knowledgeGraph,
        this.layers.nlpCore,
        this.layers.climateRiskCore,
        this.layers.kgShared,
      ],
      'relationshipMiner': [
        this.layers.awsCore,
        this.layers.dataProcessing,
        this.layers.nlpCore,
        this.layers.pytorch,
        this.layers.knowledgeGraph,
        this.layers.climateRiskCore,
        this.layers.kgShared,
      ],
      'graphUpdater': [
        this.layers.awsCore,
        this.layers.database,
        this.layers.knowledgeGraph,
        this.layers.climateRiskCore,
        this.layers.kgShared,
      ],

      // RAG System Functions
      'queryAnalyzer': [
        this.layers.awsCore,
        this.layers.dataProcessing,
        this.layers.nlpCore,
        this.layers.nlpModels,
        this.layers.webTemplate,
        this.layers.climateRiskCore,
        this.layers.kgShared,
        this.layers.ragShared,
      ],
      'vectorSearcher': [
        this.layers.awsCore,
        this.layers.dataProcessing,
        this.layers.database,
        this.layers.climateRiskCore,
        this.layers.ragShared,
      ],
      'knowledgeGraphSearcher': [
        this.layers.awsCore,
        this.layers.database,
        this.layers.knowledgeGraph,
        this.layers.climateRiskCore,
        this.layers.kgShared,
        this.layers.ragShared,
      ],
      'responseGenerator': [
        this.layers.awsCore,
        this.layers.dataProcessing,
        this.layers.nlpCore,
        this.layers.pytorch,
        this.layers.webTemplate,
        this.layers.climateRiskCore,
        this.layers.ragShared,
      ],
    };

    return layerCombinations[functionType] || [this.layers.awsCore, this.layers.climateRiskCore];
  }

  /**
   * Get common environment variables for functions using these layers
   */
  public getCommonEnvironmentVariables(): { [key: string]: string } {
    return {
      PYTHONPATH: '/opt/python:/var/runtime',
      CLIMATE_RISK_LAYER_VERSION: 'v1.0.0',
      LAYER_CACHE_ENABLED: 'true',
    };
  }
}
