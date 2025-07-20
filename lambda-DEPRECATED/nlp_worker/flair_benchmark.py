#!/usr/bin/env python3
"""
Flair Performance Benchmarking Script
Tests actual processing times and costs for different deployment scenarios
"""
import time
import psutil
import os
from typing import Dict, List, Any
import json

# Mock Flair for testing (replace with actual Flair when available)
class MockFlairBenchmark:
    """Mock Flair for benchmarking without actual library"""
    
    def __init__(self):
        self.model_load_time = 0
        self.model_loaded = False
    
    def load_model(self):
        """Simulate model loading time"""
        start_time = time.time()
        time.sleep(2.0)  # Simulate 2-second model load
        self.model_load_time = time.time() - start_time
        self.model_loaded = True
        return self.model_load_time
    
    def process_text(self, text: str) -> Dict[str, Any]:
        """Simulate text processing"""
        if not self.model_loaded:
            raise RuntimeError("Model not loaded")
        
        # Simulate processing time based on text length
        processing_time = len(text) / 5000  # 5000 chars per second
        time.sleep(processing_time)
        
        # Mock entities
        entities = [
            {'text': 'climate change', 'type': 'EVENT', 'confidence': 0.95},
            {'text': 'global warming', 'type': 'EVENT', 'confidence': 0.88}
        ]
        
        return {
            'entities': entities,
            'processing_time': processing_time,
            'text_length': len(text)
        }

class FlairBenchmark:
    """Benchmark Flair performance across different deployment scenarios"""
    
    def __init__(self):
        self.results = []
        self.mock_flair = MockFlairBenchmark()
    
    def benchmark_lambda_scenario(self, test_texts: List[str]) -> Dict[str, Any]:
        """Benchmark Lambda deployment scenario"""
        
        print("🔬 Benchmarking Lambda Scenario")
        
        # Simulate cold start
        cold_start_time = self.mock_flair.load_model()
        
        results = {
            'scenario': 'lambda',
            'cold_start_time': cold_start_time,
            'memory_usage_mb': self._get_memory_usage(),
            'document_results': []
        }
        
        for i, text in enumerate(test_texts):
            print(f"  Processing document {i+1}/{len(test_texts)} ({len(text)} chars)")
            
            start_time = time.time()
            start_memory = self._get_memory_usage()
            
            # Process text
            processing_result = self.mock_flair.process_text(text)
            
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            doc_result = {
                'document_index': i,
                'text_length': len(text),
                'processing_time': end_time - start_time,
                'memory_delta_mb': end_memory - start_memory,
                'entities_found': len(processing_result['entities']),
                'lambda_cost': self._calculate_lambda_cost(end_time - start_time, 3008)
            }
            
            results['document_results'].append(doc_result)
        
        # Calculate totals
        total_processing_time = sum(r['processing_time'] for r in results['document_results'])
        total_lambda_cost = sum(r['lambda_cost'] for r in results['document_results'])
        
        results['summary'] = {
            'total_documents': len(test_texts),
            'total_processing_time': total_processing_time,
            'average_processing_time': total_processing_time / len(test_texts),
            'total_lambda_cost': total_lambda_cost,
            'average_cost_per_document': total_lambda_cost / len(test_texts),
            'documents_per_hour': 3600 / (total_processing_time / len(test_texts)) if total_processing_time > 0 else 0
        }
        
        return results
    
    def benchmark_container_scenario(self, test_texts: List[str]) -> Dict[str, Any]:
        """Benchmark containerized service scenario"""
        
        print("🐳 Benchmarking Container Scenario")
        
        # Model already loaded (persistent service)
        if not self.mock_flair.model_loaded:
            self.mock_flair.load_model()
        
        results = {
            'scenario': 'container',
            'cold_start_time': 0,  # No cold start for persistent service
            'memory_usage_mb': self._get_memory_usage(),
            'document_results': []
        }
        
        for i, text in enumerate(test_texts):
            print(f"  Processing document {i+1}/{len(test_texts)} ({len(text)} chars)")
            
            start_time = time.time()
            
            # Process text (no model loading overhead)
            processing_result = self.mock_flair.process_text(text)
            
            end_time = time.time()
            
            doc_result = {
                'document_index': i,
                'text_length': len(text),
                'processing_time': end_time - start_time,
                'entities_found': len(processing_result['entities']),
                'fargate_cost_per_hour': 0.117,  # 2 vCPU, 8GB
                'processing_cost': self._calculate_fargate_cost(end_time - start_time)
            }
            
            results['document_results'].append(doc_result)
        
        # Calculate totals
        total_processing_time = sum(r['processing_time'] for r in results['document_results'])
        total_processing_cost = sum(r['processing_cost'] for r in results['document_results'])
        
        results['summary'] = {
            'total_documents': len(test_texts),
            'total_processing_time': total_processing_time,
            'average_processing_time': total_processing_time / len(test_texts),
            'total_processing_cost': total_processing_cost,
            'average_cost_per_document': total_processing_cost / len(test_texts),
            'documents_per_hour': 3600 / (total_processing_time / len(test_texts)) if total_processing_time > 0 else 0,
            'hourly_cost_at_capacity': 0.117  # Fixed Fargate cost
        }
        
        return results
    
    def benchmark_ec2_scenario(self, test_texts: List[str]) -> Dict[str, Any]:
        """Benchmark EC2 deployment scenario"""
        
        print("🖥️  Benchmarking EC2 Scenario")
        
        # Model already loaded (persistent service)
        if not self.mock_flair.model_loaded:
            self.mock_flair.load_model()
        
        results = {
            'scenario': 'ec2',
            'cold_start_time': 0,
            'memory_usage_mb': self._get_memory_usage(),
            'document_results': []
        }
        
        for i, text in enumerate(test_texts):
            print(f"  Processing document {i+1}/{len(test_texts)} ({len(text)} chars)")
            
            start_time = time.time()
            
            # Process text
            processing_result = self.mock_flair.process_text(text)
            
            end_time = time.time()
            
            doc_result = {
                'document_index': i,
                'text_length': len(text),
                'processing_time': end_time - start_time,
                'entities_found': len(processing_result['entities']),
                'ec2_cost_per_hour': 0.025,  # c5.large spot instance
                'processing_cost': self._calculate_ec2_cost(end_time - start_time)
            }
            
            results['document_results'].append(doc_result)
        
        # Calculate totals
        total_processing_time = sum(r['processing_time'] for r in results['document_results'])
        total_processing_cost = sum(r['processing_cost'] for r in results['document_results'])
        
        results['summary'] = {
            'total_documents': len(test_texts),
            'total_processing_time': total_processing_time,
            'average_processing_time': total_processing_time / len(test_texts),
            'total_processing_cost': total_processing_cost,
            'average_cost_per_document': total_processing_cost / len(test_texts),
            'documents_per_hour': 3600 / (total_processing_time / len(test_texts)) if total_processing_time > 0 else 0,
            'hourly_cost_at_capacity': 0.025  # Spot instance cost
        }
        
        return results
    
    def compare_scenarios(self, test_texts: List[str]) -> Dict[str, Any]:
        """Compare all deployment scenarios"""
        
        print("📊 Running Comprehensive Benchmark Comparison")
        
        # Run all benchmarks
        lambda_results = self.benchmark_lambda_scenario(test_texts)
        container_results = self.benchmark_container_scenario(test_texts)
        ec2_results = self.benchmark_ec2_scenario(test_texts)
        
        # Compare results
        comparison = {
            'test_parameters': {
                'document_count': len(test_texts),
                'total_characters': sum(len(text) for text in test_texts),
                'average_document_length': sum(len(text) for text in test_texts) / len(test_texts)
            },
            'scenarios': {
                'lambda': lambda_results['summary'],
                'container': container_results['summary'],
                'ec2': ec2_results['summary']
            },
            'cost_comparison': self._compare_costs(lambda_results, container_results, ec2_results),
            'performance_comparison': self._compare_performance(lambda_results, container_results, ec2_results),
            'recommendations': self._generate_recommendations(lambda_results, container_results, ec2_results)
        }
        
        return comparison
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def _calculate_lambda_cost(self, processing_time: float, memory_mb: int) -> float:
        """Calculate Lambda cost for processing time and memory"""
        gb_seconds = (memory_mb / 1024) * processing_time
        return gb_seconds * 0.0000166667
    
    def _calculate_fargate_cost(self, processing_time: float) -> float:
        """Calculate Fargate cost for processing time"""
        hours = processing_time / 3600
        return hours * 0.117  # 2 vCPU, 8GB Fargate cost
    
    def _calculate_ec2_cost(self, processing_time: float) -> float:
        """Calculate EC2 cost for processing time"""
        hours = processing_time / 3600
        return hours * 0.025  # c5.large spot instance
    
    def _compare_costs(self, lambda_results, container_results, ec2_results) -> Dict[str, Any]:
        """Compare costs across scenarios"""
        
        lambda_cost = lambda_results['summary']['average_cost_per_document']
        container_cost = container_results['summary']['average_cost_per_document']
        ec2_cost = ec2_results['summary']['average_cost_per_document']
        
        costs = [
            ('lambda', lambda_cost),
            ('container', container_cost),
            ('ec2', ec2_cost)
        ]
        
        costs.sort(key=lambda x: x[1])
        
        return {
            'cheapest_to_most_expensive': [{'scenario': name, 'cost_per_document': cost} for name, cost in costs],
            'cost_differences': {
                'lambda_vs_container': abs(lambda_cost - container_cost),
                'lambda_vs_ec2': abs(lambda_cost - ec2_cost),
                'container_vs_ec2': abs(container_cost - ec2_cost)
            }
        }
    
    def _compare_performance(self, lambda_results, container_results, ec2_results) -> Dict[str, Any]:
        """Compare performance across scenarios"""
        
        return {
            'processing_time_per_document': {
                'lambda': lambda_results['summary']['average_processing_time'],
                'container': container_results['summary']['average_processing_time'],
                'ec2': ec2_results['summary']['average_processing_time']
            },
            'documents_per_hour': {
                'lambda': lambda_results['summary']['documents_per_hour'],
                'container': container_results['summary']['documents_per_hour'],
                'ec2': ec2_results['summary']['documents_per_hour']
            },
            'cold_start_impact': {
                'lambda': lambda_results['cold_start_time'],
                'container': 0,
                'ec2': 0
            }
        }
    
    def _generate_recommendations(self, lambda_results, container_results, ec2_results) -> List[str]:
        """Generate recommendations based on benchmark results"""
        
        recommendations = []
        
        # Cost analysis
        lambda_cost = lambda_results['summary']['average_cost_per_document']
        container_cost = container_results['summary']['average_cost_per_document']
        ec2_cost = ec2_results['summary']['average_cost_per_document']
        
        if lambda_cost < container_cost and lambda_cost < ec2_cost:
            recommendations.append("Lambda is most cost-effective for sporadic workloads")
        elif ec2_cost < lambda_cost and ec2_cost < container_cost:
            recommendations.append("EC2 spot instances are most cost-effective for sustained workloads")
        else:
            recommendations.append("Container service provides good balance of cost and simplicity")
        
        # Performance analysis
        lambda_throughput = lambda_results['summary']['documents_per_hour']
        container_throughput = container_results['summary']['documents_per_hour']
        
        if container_throughput > lambda_throughput * 1.5:
            recommendations.append("Container service significantly outperforms Lambda due to no cold starts")
        
        # Complexity analysis
        recommendations.append("Lambda: Lowest operational complexity")
        recommendations.append("Container: Medium complexity, good for sustained workloads")
        recommendations.append("EC2: Highest complexity, best for cost optimization at scale")
        
        return recommendations

def main():
    """Run benchmark comparison"""
    
    # Test texts of different lengths
    test_texts = [
        "Climate change is a major global issue affecting ecosystems worldwide.",  # Short
        "Climate change represents one of the most significant challenges facing humanity in the 21st century. Rising global temperatures, caused primarily by increased greenhouse gas emissions from human activities, are leading to widespread environmental changes including melting ice caps, rising sea levels, and more frequent extreme weather events." * 2,  # Medium
        "Climate change represents one of the most significant challenges facing humanity in the 21st century. Rising global temperatures, caused primarily by increased greenhouse gas emissions from human activities, are leading to widespread environmental changes including melting ice caps, rising sea levels, and more frequent extreme weather events." * 10  # Long
    ]
    
    benchmark = FlairBenchmark()
    results = benchmark.compare_scenarios(test_texts)
    
    # Print results
    print("\n" + "="*60)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*60)
    
    print(f"\nTest Parameters:")
    print(f"  Documents: {results['test_parameters']['document_count']}")
    print(f"  Total characters: {results['test_parameters']['total_characters']:,}")
    print(f"  Average length: {results['test_parameters']['average_document_length']:.0f} chars")
    
    print(f"\nCost per Document:")
    for scenario in results['cost_comparison']['cheapest_to_most_expensive']:
        print(f"  {scenario['scenario'].title()}: ${scenario['cost_per_document']:.6f}")
    
    print(f"\nProcessing Speed (docs/hour):")
    for scenario, speed in results['performance_comparison']['documents_per_hour'].items():
        print(f"  {scenario.title()}: {speed:.1f}")
    
    print(f"\nRecommendations:")
    for rec in results['recommendations']:
        print(f"  • {rec}")
    
    # Save detailed results
    with open('flair_benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: flair_benchmark_results.json")

if __name__ == "__main__":
    main()
