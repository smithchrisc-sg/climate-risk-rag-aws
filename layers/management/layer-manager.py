#!/usr/bin/env python3
"""
Lambda Layer Manager for Climate Risk RAG System
Provides tools for managing, monitoring, and updating Lambda layers
"""

import boto3
import json
import logging
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LayerManager:
    """Manages Lambda layers for the Climate Risk RAG system"""
    
    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None):
        """Initialize the layer manager"""
        self.region = region
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.lambda_client = self.session.client('lambda', region_name=region)
        self.layer_prefix = 'climate-risk-rag'
        
        # Layer definitions
        self.layer_definitions = {
            'aws-core-layer': {
                'description': 'AWS SDK and core utilities',
                'category': 'foundation',
                'size_estimate': '30MB'
            },
            'data-processing-layer': {
                'description': 'NumPy, Pandas, SciPy for data processing',
                'category': 'foundation',
                'size_estimate': '80MB'
            },
            'database-layer': {
                'description': 'Database connectivity (PostgreSQL, OpenSearch, Redis)',
                'category': 'foundation',
                'size_estimate': '40MB'
            },
            'nlp-core-layer': {
                'description': 'Core NLP libraries without models',
                'category': 'foundation',
                'size_estimate': '200MB'
            },
            'pytorch-layer': {
                'description': 'PyTorch framework for ML inference',
                'category': 'foundation',
                'size_estimate': '400MB'
            },
            'knowledge-graph-layer': {
                'description': 'RDF, SPARQL, and ontology processing',
                'category': 'foundation',
                'size_estimate': '120MB'
            },
            'web-template-layer': {
                'description': 'Web scraping and templating',
                'category': 'foundation',
                'size_estimate': '60MB'
            },
            'nlp-models-layer': {
                'description': 'Pre-trained NLP models and specialized tools',
                'category': 'foundation',
                'size_estimate': '800MB'
            },
            'climate-risk-core-layer': {
                'description': 'Core application utilities',
                'category': 'application',
                'size_estimate': '15MB'
            },
            'kg-shared-layer': {
                'description': 'Knowledge graph shared components',
                'category': 'application',
                'size_estimate': '25MB'
            },
            'rag-shared-layer': {
                'description': 'RAG system shared components',
                'category': 'application',
                'size_estimate': '20MB'
            }
        }
    
    def list_layers(self, include_versions: bool = False) -> Dict[str, Any]:
        """List all Climate Risk RAG layers"""
        logger.info("Listing Climate Risk RAG layers...")
        
        try:
            # Get all layers
            paginator = self.lambda_client.get_paginator('list_layers')
            all_layers = []
            
            for page in paginator.paginate():
                all_layers.extend(page['Layers'])
            
            # Filter our layers
            our_layers = [
                layer for layer in all_layers 
                if layer['LayerName'].startswith(self.layer_prefix)
            ]
            
            result = {
                'layers': [],
                'summary': {
                    'total_layers': len(our_layers),
                    'foundation_layers': 0,
                    'application_layers': 0,
                    'total_versions': 0
                }
            }
            
            for layer in our_layers:
                layer_name = layer['LayerName']
                short_name = layer_name.replace(f'{self.layer_prefix}-', '').replace('-dev', '').replace('-prod', '')
                
                layer_info = {
                    'name': layer_name,
                    'short_name': short_name,
                    'latest_version': layer['LatestMatchingVersion']['Version'],
                    'description': layer['LatestMatchingVersion']['Description'],
                    'created_date': layer['LatestMatchingVersion']['CreatedDate'].isoformat(),
                    'code_size': layer['LatestMatchingVersion']['CodeSize'],
                    'compatible_runtimes': layer['LatestMatchingVersion']['CompatibleRuntimes']
                }
                
                # Add category information
                if short_name in self.layer_definitions:
                    layer_info['category'] = self.layer_definitions[short_name]['category']
                    layer_info['size_estimate'] = self.layer_definitions[short_name]['size_estimate']
                    
                    if self.layer_definitions[short_name]['category'] == 'foundation':
                        result['summary']['foundation_layers'] += 1
                    else:
                        result['summary']['application_layers'] += 1
                
                # Get version information if requested
                if include_versions:
                    layer_info['versions'] = self._get_layer_versions(layer_name)
                    result['summary']['total_versions'] += len(layer_info['versions'])
                
                result['layers'].append(layer_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing layers: {str(e)}")
            raise
    
    def _get_layer_versions(self, layer_name: str) -> List[Dict[str, Any]]:
        """Get all versions of a specific layer"""
        try:
            paginator = self.lambda_client.get_paginator('list_layer_versions')
            versions = []
            
            for page in paginator.paginate(LayerName=layer_name):
                for version in page['LayerVersions']:
                    versions.append({
                        'version': version['Version'],
                        'created_date': version['CreatedDate'].isoformat(),
                        'code_size': version['CodeSize'],
                        'description': version.get('Description', '')
                    })
            
            return sorted(versions, key=lambda x: x['version'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting versions for layer {layer_name}: {str(e)}")
            return []
    
    def get_layer_usage(self, layer_name: str) -> List[Dict[str, Any]]:
        """Get functions using a specific layer"""
        logger.info(f"Finding functions using layer: {layer_name}")
        
        try:
            # Get all functions
            paginator = self.lambda_client.get_paginator('list_functions')
            functions_using_layer = []
            
            for page in paginator.paginate():
                for function in page['Functions']:
                    if 'Layers' in function:
                        for layer in function['Layers']:
                            if layer_name in layer['Arn']:
                                functions_using_layer.append({
                                    'function_name': function['FunctionName'],
                                    'runtime': function['Runtime'],
                                    'last_modified': function['LastModified'],
                                    'layer_arn': layer['Arn'],
                                    'layer_version': layer['Arn'].split(':')[-1]
                                })
            
            return functions_using_layer
            
        except Exception as e:
            logger.error(f"Error getting layer usage: {str(e)}")
            return []
    
    def update_layer(self, layer_name: str, zip_file_path: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Update a layer with a new version"""
        logger.info(f"Updating layer: {layer_name}")
        
        if not os.path.exists(zip_file_path):
            raise FileNotFoundError(f"Zip file not found: {zip_file_path}")
        
        try:
            with open(zip_file_path, 'rb') as f:
                zip_content = f.read()
            
            # Use existing description if not provided
            if not description:
                short_name = layer_name.replace(f'{self.layer_prefix}-', '').replace('-dev', '').replace('-prod', '')
                if short_name in self.layer_definitions:
                    description = self.layer_definitions[short_name]['description']
                else:
                    description = f"Updated {layer_name}"
            
            response = self.lambda_client.publish_layer_version(
                LayerName=layer_name,
                Content={'ZipFile': zip_content},
                CompatibleRuntimes=['python3.11'],
                Description=description
            )
            
            logger.info(f"Successfully updated {layer_name} to version {response['Version']}")
            return response
            
        except Exception as e:
            logger.error(f"Error updating layer {layer_name}: {str(e)}")
            raise
    
    def delete_layer_version(self, layer_name: str, version: int) -> bool:
        """Delete a specific version of a layer"""
        logger.info(f"Deleting layer version: {layer_name}:{version}")
        
        try:
            self.lambda_client.delete_layer_version(
                LayerName=layer_name,
                VersionNumber=version
            )
            logger.info(f"Successfully deleted {layer_name}:{version}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting layer version: {str(e)}")
            return False
    
    def cleanup_old_versions(self, layer_name: str, keep_versions: int = 3) -> List[int]:
        """Clean up old versions of a layer, keeping only the specified number"""
        logger.info(f"Cleaning up old versions of {layer_name}, keeping {keep_versions} versions")
        
        try:
            versions = self._get_layer_versions(layer_name)
            
            if len(versions) <= keep_versions:
                logger.info(f"Layer {layer_name} has {len(versions)} versions, no cleanup needed")
                return []
            
            # Sort by version number and keep the latest ones
            versions_to_delete = sorted(versions, key=lambda x: x['version'])[:-keep_versions]
            deleted_versions = []
            
            for version_info in versions_to_delete:
                version = version_info['version']
                if self.delete_layer_version(layer_name, version):
                    deleted_versions.append(version)
            
            logger.info(f"Deleted {len(deleted_versions)} old versions of {layer_name}")
            return deleted_versions
            
        except Exception as e:
            logger.error(f"Error cleaning up layer versions: {str(e)}")
            return []
    
    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate a comprehensive report of all layers"""
        logger.info("Generating layer report...")
        
        try:
            layers_info = self.list_layers(include_versions=True)
            
            report = {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'region': self.region,
                'summary': layers_info['summary'],
                'layers': []
            }
            
            for layer in layers_info['layers']:
                layer_report = {
                    'name': layer['name'],
                    'short_name': layer['short_name'],
                    'category': layer.get('category', 'unknown'),
                    'description': layer['description'],
                    'latest_version': layer['latest_version'],
                    'code_size_mb': round(layer['code_size'] / (1024 * 1024), 2),
                    'size_estimate': layer.get('size_estimate', 'unknown'),
                    'created_date': layer['created_date'],
                    'total_versions': len(layer.get('versions', [])),
                    'functions_using': self.get_layer_usage(layer['name'])
                }
                
                report['layers'].append(layer_report)
            
            # Calculate total sizes
            total_size_mb = sum(layer['code_size_mb'] for layer in report['layers'])
            report['summary']['total_size_mb'] = round(total_size_mb, 2)
            
            # Save to file if requested
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                logger.info(f"Report saved to {output_file}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise
    
    def validate_layer_compatibility(self, layer_name: str) -> Dict[str, Any]:
        """Validate layer compatibility and health"""
        logger.info(f"Validating layer compatibility: {layer_name}")
        
        try:
            # Get layer information
            response = self.lambda_client.get_layer_version_by_arn(
                Arn=f"arn:aws:lambda:{self.region}:{self.session.client('sts').get_caller_identity()['Account']}:layer:{layer_name}"
            )
            
            validation_result = {
                'layer_name': layer_name,
                'is_valid': True,
                'issues': [],
                'recommendations': [],
                'layer_info': {
                    'version': response['Version'],
                    'code_size': response['CodeSize'],
                    'compatible_runtimes': response['CompatibleRuntimes'],
                    'created_date': response['CreatedDate'].isoformat()
                }
            }
            
            # Check size
            size_mb = response['CodeSize'] / (1024 * 1024)
            if size_mb > 250:  # Lambda layer size limit
                validation_result['issues'].append(f"Layer size ({size_mb:.1f}MB) is very large")
                validation_result['recommendations'].append("Consider splitting large dependencies")
            
            # Check runtime compatibility
            if 'python3.11' not in response['CompatibleRuntimes']:
                validation_result['issues'].append("Layer not compatible with Python 3.11")
                validation_result['is_valid'] = False
            
            # Check usage
            functions_using = self.get_layer_usage(layer_name)
            validation_result['functions_using_count'] = len(functions_using)
            
            if len(functions_using) == 0:
                validation_result['issues'].append("Layer is not being used by any functions")
                validation_result['recommendations'].append("Consider removing unused layer")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating layer: {str(e)}")
            return {
                'layer_name': layer_name,
                'is_valid': False,
                'issues': [f"Validation failed: {str(e)}"],
                'recommendations': []
            }

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='Climate Risk RAG Lambda Layer Manager')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--profile', help='AWS profile to use')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all layers')
    list_parser.add_argument('--versions', action='store_true', help='Include version information')
    list_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Usage command
    usage_parser = subparsers.add_parser('usage', help='Show layer usage')
    usage_parser.add_argument('layer_name', help='Layer name to check')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update a layer')
    update_parser.add_argument('layer_name', help='Layer name to update')
    update_parser.add_argument('zip_file', help='Path to zip file')
    update_parser.add_argument('--description', help='Layer description')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old layer versions')
    cleanup_parser.add_argument('layer_name', help='Layer name to clean up')
    cleanup_parser.add_argument('--keep', type=int, default=3, help='Number of versions to keep')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate layer report')
    report_parser.add_argument('--output', help='Output file path')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate layer compatibility')
    validate_parser.add_argument('layer_name', help='Layer name to validate')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize layer manager
    manager = LayerManager(region=args.region, profile=args.profile)
    
    try:
        if args.command == 'list':
            result = manager.list_layers(include_versions=args.versions)
            
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"\nClimate Risk RAG Layers ({result['summary']['total_layers']} total)")
                print("=" * 60)
                
                for layer in result['layers']:
                    print(f"\n📦 {layer['short_name']}")
                    print(f"   Name: {layer['name']}")
                    print(f"   Category: {layer.get('category', 'unknown')}")
                    print(f"   Version: {layer['latest_version']}")
                    print(f"   Size: {layer['code_size'] / (1024*1024):.1f}MB")
                    print(f"   Description: {layer['description']}")
                    
                    if args.versions and 'versions' in layer:
                        print(f"   Versions: {len(layer['versions'])}")
        
        elif args.command == 'usage':
            functions = manager.get_layer_usage(args.layer_name)
            
            print(f"\nFunctions using layer: {args.layer_name}")
            print("=" * 60)
            
            if functions:
                for func in functions:
                    print(f"• {func['function_name']} (version {func['layer_version']})")
            else:
                print("No functions are using this layer")
        
        elif args.command == 'update':
            result = manager.update_layer(args.layer_name, args.zip_file, args.description)
            print(f"✅ Updated {args.layer_name} to version {result['Version']}")
            print(f"   ARN: {result['LayerVersionArn']}")
        
        elif args.command == 'cleanup':
            deleted = manager.cleanup_old_versions(args.layer_name, args.keep)
            if deleted:
                print(f"✅ Deleted {len(deleted)} old versions: {deleted}")
            else:
                print("No versions were deleted")
        
        elif args.command == 'report':
            report = manager.generate_report(args.output)
            
            if not args.output:
                print(f"\nClimate Risk RAG Layer Report")
                print("=" * 60)
                print(f"Generated: {report['generated_at']}")
                print(f"Region: {report['region']}")
                print(f"Total Layers: {report['summary']['total_layers']}")
                print(f"Foundation Layers: {report['summary']['foundation_layers']}")
                print(f"Application Layers: {report['summary']['application_layers']}")
                print(f"Total Size: {report['summary']['total_size_mb']:.1f}MB")
        
        elif args.command == 'validate':
            result = manager.validate_layer_compatibility(args.layer_name)
            
            print(f"\nValidation Results for: {args.layer_name}")
            print("=" * 60)
            print(f"Status: {'✅ Valid' if result['is_valid'] else '❌ Invalid'}")
            
            if result['issues']:
                print("\nIssues:")
                for issue in result['issues']:
                    print(f"  • {issue}")
            
            if result['recommendations']:
                print("\nRecommendations:")
                for rec in result['recommendations']:
                    print(f"  • {rec}")
    
    except Exception as e:
        logger.error(f"Command failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
