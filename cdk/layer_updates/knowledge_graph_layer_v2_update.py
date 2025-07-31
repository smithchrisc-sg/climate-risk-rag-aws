#!/usr/bin/env python3
"""
Knowledge Graph Layer v2.0.0 CDK Update
Updates all Lambda functions to use the new layer version with NLP-Ontology integration
"""

from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_ec2 as ec2,
    CfnOutput
)

class KnowledgeGraphLayerV2Update:
    """
    CDK update class for Knowledge Graph Layer v2.0.0
    Maintains backward compatibility while adding new NLP functionality
    """
    
    def __init__(self, stack, existing_resources):
        """
        Initialize layer update with existing stack resources
        
        Args:
            stack: CDK stack instance
            existing_resources: Dictionary of existing resources (VPC, subnets, etc.)
        """
        self.stack = stack
        self.existing_resources = existing_resources
        
        # Create updated layer
        self.knowledge_graph_layer_v2 = self._create_knowledge_graph_layer_v2()
        
        # Update existing functions
        self._update_existing_functions()
        
        # Add new NLP functions
        self._add_new_nlp_functions()
    
    def _create_knowledge_graph_layer_v2(self) -> lambda_.LayerVersion:
        """Create Knowledge Graph Layer v2.0.0 with NLP-Ontology integration"""
        
        return lambda_.LayerVersion(
            self.stack, "KnowledgeGraphLayerV2",
            code=lambda_.Code.from_asset("../layers/knowledge-graph-layer/knowledge-graph-layer-v2.0.0-minimal.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration - Backward Compatible",
            layer_version_name="knowledge-graph-layer-v2"
        )
    
    def _update_existing_functions(self):
        """Update existing Lambda functions to use v2.0.0 layer"""
        
        # Get common environment and layer configuration
        common_layers = [
            self.existing_resources['database_layer'],
            self.existing_resources['database_dependencies_layer'],
            self.knowledge_graph_layer_v2  # Updated to v2.0.0
        ]
        
        common_env = self.existing_resources.get('common_env', {})
        
        # 1. Update Document Structure KG Processor
        self.document_structure_kg_processor_v2 = lambda_.Function(
            self.stack, "DocumentStructureKGProcessorV2",
            function_name="solve-global-kr-document-structure-kg-processor-v2",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/document-structure-kg-processor"),
            role=self.existing_resources['lambda_role'],
            timeout=Duration.minutes(15),
            memory_size=1024,  # Same as before - no changes needed
            vpc=self.existing_resources['vpc'],
            vpc_subnets=ec2.SubnetSelection(subnets=[
                self.existing_resources['database_subnet_1'], 
                self.existing_resources['database_subnet_2']
            ]),
            security_groups=[self.existing_resources['lambda_sg']],
            layers=common_layers,  # Updated layer
            environment={
                **common_env,
                "KG_TRIPLES_READY_TOPIC_ARN": self.existing_resources['kg_triples_ready_topic'].topic_arn,
                "KG_BUCKET": self.existing_resources['kg_bucket'].bucket_name,
                "NEPTUNE_ENDPOINT": self.existing_resources.get('neptune_endpoint', ''),
                "NEPTUNE_PORT": "8182"
            }
        )
        
        # 2. Update KG Triple Loader
        self.kg_triple_loader_v2 = lambda_.Function(
            self.stack, "KGTripleLoaderV2",
            function_name="solve-global-kr-kg-triple-loader-v2",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/kg-triple-loader"),
            role=self.existing_resources['lambda_role'],
            timeout=Duration.minutes(15),
            memory_size=1024,  # Same as before
            vpc=self.existing_resources['vpc'],
            vpc_subnets=ec2.SubnetSelection(subnets=[
                self.existing_resources['neptune_subnet_1'], 
                self.existing_resources['neptune_subnet_2']
            ]),
            security_groups=[self.existing_resources['lambda_sg']],
            layers=common_layers,  # Updated layer
            environment={
                **common_env,
                "NEPTUNE_ENDPOINT": self.existing_resources.get('neptune_endpoint', ''),
                "NEPTUNE_PORT": "8182",
                "TTL_BUCKET": self.existing_resources['kg_bucket'].bucket_name
            }
        )
    
    def _add_new_nlp_functions(self):
        """Add new NLP Lambda functions using v2.0.0 layer"""
        
        # Common configuration for NLP functions
        nlp_common_layers = [
            self.existing_resources['database_layer'],
            self.existing_resources['database_dependencies_layer'],
            self.knowledge_graph_layer_v2  # v2.0.0 with NLP utilities
        ]
        
        nlp_common_env = {
            **self.existing_resources.get('common_env', {}),
            "NEPTUNE_ENDPOINT": self.existing_resources.get('neptune_endpoint', ''),
            "NEPTUNE_PORT": "8182",
            "ONTOLOGY_BUCKET": self.existing_resources.get('ontology_bucket', ''),
            "NER_RESULTS_BUCKET": self.existing_resources.get('ner_results_bucket', ''),
            "TEXT_BUCKET": self.existing_resources.get('text_bucket', '')
        }
        
        # 1. NLP Entity-Ontology Mapper
        self.nlp_entity_ontology_mapper = lambda_.Function(
            self.stack, "NLPEntityOntologyMapper",
            function_name="solve-global-kr-nlp-entity-ontology-mapper",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-entity-ontology-mapper"),
            role=self.existing_resources['lambda_role'],
            timeout=Duration.minutes(10),
            memory_size=1024,  # Increased for NLP processing
            vpc=self.existing_resources['vpc'],
            vpc_subnets=ec2.SubnetSelection(subnets=[
                self.existing_resources['database_subnet_1'], 
                self.existing_resources['database_subnet_2']
            ]),
            security_groups=[self.existing_resources['lambda_sg']],
            layers=nlp_common_layers,
            environment={
                **nlp_common_env,
                "MIN_CONFIDENCE_THRESHOLD": "0.6",
                "MAX_CANDIDATES": "5"
            }
        )
        
        # 2. NLP Ontology Term Finder
        self.nlp_ontology_term_finder = lambda_.Function(
            self.stack, "NLPOntologyTermFinder",
            function_name="solve-global-kr-nlp-ontology-term-finder",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-ontology-term-finder"),
            role=self.existing_resources['lambda_role'],
            timeout=Duration.minutes(10),
            memory_size=1024,  # Increased for pattern matching
            vpc=self.existing_resources['vpc'],
            vpc_subnets=ec2.SubnetSelection(subnets=[
                self.existing_resources['database_subnet_1'], 
                self.existing_resources['database_subnet_2']
            ]),
            security_groups=[self.existing_resources['lambda_sg']],
            layers=nlp_common_layers,
            environment={
                **nlp_common_env,
                "MIN_CONFIDENCE_THRESHOLD": "0.7",
                "MIN_TERM_LENGTH": "3",
                "MAX_TERM_DISTANCE": "100"
            }
        )
        
        # 3. NLP Concept Reconciler
        self.nlp_concept_reconciler = lambda_.Function(
            self.stack, "NLPConceptReconciler",
            function_name="solve-global-kr-nlp-concept-reconciler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-concept-reconciler"),
            role=self.existing_resources['lambda_role'],
            timeout=Duration.minutes(5),
            memory_size=512,  # Lower memory for reconciliation logic
            vpc=self.existing_resources['vpc'],
            vpc_subnets=ec2.SubnetSelection(subnets=[
                self.existing_resources['database_subnet_1'], 
                self.existing_resources['database_subnet_2']
            ]),
            security_groups=[self.existing_resources['lambda_sg']],
            layers=nlp_common_layers,
            environment={
                **nlp_common_env,
                "RECONCILIATION_STRATEGY": "confidence_weighted",
                "CONFLICT_RESOLUTION": "highest_confidence",
                "MIN_CONFIDENCE_THRESHOLD": "0.6"
            }
        )
        
        # 4. NLP-KG Integrator
        self.nlp_kg_integrator = lambda_.Function(
            self.stack, "NLPKGIntegrator",
            function_name="solve-global-kr-nlp-kg-integrator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-kg-integrator"),
            role=self.existing_resources['lambda_role'],
            timeout=Duration.minutes(10),
            memory_size=1024,  # Increased for RDF processing
            vpc=self.existing_resources['vpc'],
            vpc_subnets=ec2.SubnetSelection(subnets=[
                self.existing_resources['neptune_subnet_1'], 
                self.existing_resources['neptune_subnet_2']
            ]),
            security_groups=[self.existing_resources['lambda_sg']],
            layers=nlp_common_layers,
            environment={
                **nlp_common_env,
                "ENABLE_VALIDATION": "true",
                "KG_BUCKET": self.existing_resources['kg_bucket'].bucket_name
            }
        )
    
    def add_outputs(self):
        """Add CDK outputs for new layer and functions"""
        
        # Layer output
        CfnOutput(
            self.stack, "KnowledgeGraphLayerV2Arn",
            value=self.knowledge_graph_layer_v2.layer_version_arn,
            description="Knowledge Graph Layer v2.0.0 ARN with NLP-Ontology Integration"
        )
        
        # Function outputs
        CfnOutput(
            self.stack, "NLPEntityOntologyMapperArn",
            value=self.nlp_entity_ontology_mapper.function_arn,
            description="NLP Entity-Ontology Mapper Function ARN"
        )
        
        CfnOutput(
            self.stack, "NLPOntologyTermFinderArn",
            value=self.nlp_ontology_term_finder.function_arn,
            description="NLP Ontology Term Finder Function ARN"
        )
        
        CfnOutput(
            self.stack, "NLPConceptReconcilerArn",
            value=self.nlp_concept_reconciler.function_arn,
            description="NLP Concept Reconciler Function ARN"
        )
        
        CfnOutput(
            self.stack, "NLPKGIntegratorArn",
            value=self.nlp_kg_integrator.function_arn,
            description="NLP-KG Integrator Function ARN"
        )

# Usage example for integration into existing CDK stack
def integrate_knowledge_graph_layer_v2(stack, existing_resources):
    """
    Integrate Knowledge Graph Layer v2.0.0 into existing CDK stack
    
    Args:
        stack: CDK stack instance
        existing_resources: Dictionary containing existing resources
    
    Returns:
        KnowledgeGraphLayerV2Update instance
    """
    
    # Create the layer update
    kg_layer_update = KnowledgeGraphLayerV2Update(stack, existing_resources)
    
    # Add outputs
    kg_layer_update.add_outputs()
    
    return kg_layer_update
