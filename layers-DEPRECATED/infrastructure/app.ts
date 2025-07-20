#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { LambdaLayersStack } from './lambda-layers-stack';

const app = new cdk.App();

// Get environment from context or default to 'dev'
const environment = app.node.tryGetContext('environment') || 'dev';
const layerPrefix = app.node.tryGetContext('layerPrefix') || 'climate-risk-rag';

new LambdaLayersStack(app, `ClimateRiskLambdaLayers-${environment}`, {
  layerPrefix,
  environment,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: `Lambda layers for Climate Risk RAG system (${environment})`,
  tags: {
    Project: 'ClimateRiskRAG',
    Component: 'LambdaLayers',
    Environment: environment,
  },
});
