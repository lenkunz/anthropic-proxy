#!/usr/bin/env python3
"""
Test proxy performance comparison between OpenAI and Anthropic endpoint routing.

This test compares:
- Proxy → OpenAI endpoint (using glm-4.5-openai model)
- Proxy → Anthropic endpoint (using glm-4.5-anthropic model)

Both go through your proxy but route to different upstream endpoints.
"""

import os
import requests
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

# Proxy endpoint
PROXY_BASE = "http://localhost:5000"

def test_proxy_openai_route(prompt):
    """Test proxy routing to OpenAI endpoint using glm-4.5-openai model"""
    url = f"{PROXY_BASE}/v1/chat/completions"
    print(f"📤 Testing proxy → OpenAI route...")
    print(f"   🌐 URL: {url}")
    print(f"   🎯 Model: glm-4.5-openai (forces OpenAI endpoint)")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5-openai",  # Forces OpenAI endpoint
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 50,
        "temperature": 0
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        end_time = time.time()
        duration = end_time - start_time
        
        response.raise_for_status()
        result = response.json()
        
        if 'usage' in result:
            print(f"   ✅ Proxy → OpenAI response received in {duration:.2f}s")
            return {
                'prompt_tokens': result['usage']['prompt_tokens'],
                'completion_tokens': result['usage']['completion_tokens'],
                'total_tokens': result['usage']['total_tokens'],
                'duration': duration
            }
        else:
            print(f"❌ No usage data in proxy → OpenAI response: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Proxy → OpenAI test failed: {e}")
        return None

def test_proxy_anthropic_route(prompt):
    """Test proxy routing to Anthropic endpoint using glm-4.5-anthropic model"""
    url = f"{PROXY_BASE}/v1/chat/completions"
    print(f"📤 Testing proxy → Anthropic route...")
    print(f"   🌐 URL: {url}")
    print(f"   🎯 Model: glm-4.5-anthropic (forces Anthropic endpoint)")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5-anthropic",  # Forces Anthropic endpoint
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 50,
        "temperature": 0
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        end_time = time.time()
        duration = end_time - start_time
        
        response.raise_for_status()
        result = response.json()
        
        if 'usage' in result:
            print(f"   ✅ Proxy → Anthropic response received in {duration:.2f}s")
            return {
                'prompt_tokens': result['usage']['prompt_tokens'],
                'completion_tokens': result['usage']['completion_tokens'],
                'total_tokens': result['usage']['total_tokens'],
                'duration': duration
            }
        else:
            print(f"❌ No usage data in proxy → Anthropic response: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Proxy → Anthropic test failed: {e}")
        return None

def run_proxy_performance_test():
    """Run the proxy performance comparison test"""
    
    print("⚡ PROXY PERFORMANCE COMPARISON TEST")
    print("=" * 60)
    print("Testing proxy performance when routing to different endpoints")
    print("Both requests go through your proxy with different model variants")
    print()
    
    # Test with different prompt sizes
    test_prompts = [
        {
            "name": "Medium Prompt",
            "content": """Provide a comprehensive analysis of artificial intelligence and machine learning technologies. 
            Discuss the evolution from rule-based expert systems to modern neural networks and deep learning architectures. 
            Explain the key differences between supervised, unsupervised, and reinforcement learning paradigms, providing 
            specific examples of algorithms within each category. Detail the mathematical foundations underlying gradient 
            descent optimization, backpropagation in neural networks, and the role of activation functions in deep learning 
            models. Analyze the applications of convolutional neural networks in computer vision, recurrent neural networks 
            and transformers in natural language processing, and generative adversarial networks in content creation."""
        },
        {
            "name": "Large Prompt",
            "content": """Conduct an in-depth technical analysis of distributed systems architecture and cloud computing paradigms. 
            Begin with the fundamental principles of distributed computing, including the CAP theorem and its implications 
            for system design, the challenges of maintaining consistency in distributed databases, and the trade-offs between 
            availability and partition tolerance. Explain the various consensus algorithms such as Raft, Paxos, and Byzantine 
            fault tolerance protocols, detailing how they ensure data consistency across multiple nodes in the presence of 
            network failures and malicious actors. Analyze microservices architecture patterns, including service discovery 
            mechanisms, API gateway implementations, circuit breaker patterns for fault tolerance, and the role of containers 
            and orchestration platforms like Kubernetes in managing complex distributed applications. Discuss event-driven 
            architectures, message queuing systems, and the differences between synchronous and asynchronous communication 
            patterns in distributed systems. Examine data storage strategies including database sharding, replication techniques, 
            eventual consistency models, and the use of NoSQL databases for handling large-scale unstructured data."""
        },
        {
            "name": "Extra Large Prompt",
            "content": """Provide a comprehensive technical exploration of modern cybersecurity threats, defense mechanisms, 
            and emerging security paradigms in the digital age. Begin with an analysis of the evolving threat landscape, 
            including advanced persistent threats (APTs), zero-day exploits, ransomware campaigns, and state-sponsored 
            cyber warfare activities. Detail the techniques used in modern malware development, including polymorphic and 
            metamorphic code, fileless malware, living-off-the-land attacks, and the abuse of legitimate system tools 
            for malicious purposes. Explain the role of artificial intelligence and machine learning in both offensive 
            and defensive cybersecurity applications, including adversarial machine learning attacks, AI-powered threat 
            detection systems, and the potential for automated vulnerability discovery and exploitation. Analyze network 
            security architectures, including next-generation firewalls, intrusion detection and prevention systems, 
            network segmentation strategies, and the implementation of zero-trust network models. Discuss endpoint security 
            solutions, including endpoint detection and response (EDR) systems, behavioral analysis techniques, and the 
            challenges of securing mobile devices and Internet of Things (IoT) endpoints. Examine cryptographic protocols 
            and their applications in securing digital communications, including symmetric and asymmetric encryption 
            algorithms, digital signatures, public key infrastructure (PKI), and the emerging field of post-quantum 
            cryptography in preparation for quantum computing threats."""
        }
    ]
    
    performance_summary = []
    
    for i, prompt_data in enumerate(test_prompts, 1):
        print(f"🧪 TEST {i}: {prompt_data['name']}")
        print("-" * 50)
        
        # Test proxy → OpenAI route
        openai_result = test_proxy_openai_route(prompt_data['content'])
        time.sleep(1)  # Rate limiting
        
        # Test proxy → Anthropic route  
        anthropic_result = test_proxy_anthropic_route(prompt_data['content'])
        time.sleep(1)  # Rate limiting
        
        if openai_result and anthropic_result:
            print(f"📊 PROXY PERFORMANCE COMPARISON:")
            print(f"   🟦 Proxy → OpenAI:    {openai_result['prompt_tokens']} input tokens")
            print(f"   🟪 Proxy → Anthropic: {anthropic_result['prompt_tokens']} input tokens")
            
            # Calculate performance rates (tokens/sec)
            openai_tokens_per_sec = openai_result['total_tokens'] / openai_result['duration']
            anthropic_tokens_per_sec = anthropic_result['total_tokens'] / anthropic_result['duration']
            
            print(f"   ⚡ PROXY PERFORMANCE RATES:")
            print(f"     🟦 Proxy → OpenAI: {openai_tokens_per_sec:.1f} tokens/sec ({openai_result['duration']:.2f}s)")
            print(f"     🟪 Proxy → Anthropic: {anthropic_tokens_per_sec:.1f} tokens/sec ({anthropic_result['duration']:.2f}s)")
            
            # Determine winner
            if openai_tokens_per_sec > anthropic_tokens_per_sec:
                speed_diff = ((openai_tokens_per_sec / anthropic_tokens_per_sec) - 1) * 100
                print(f"   🏆 WINNER: Proxy → OpenAI is {speed_diff:.1f}% faster")
            elif anthropic_tokens_per_sec > openai_tokens_per_sec:
                speed_diff = ((anthropic_tokens_per_sec / openai_tokens_per_sec) - 1) * 100
                print(f"   🏆 WINNER: Proxy → Anthropic is {speed_diff:.1f}% faster")
            else:
                print(f"   🤝 TIE: Both routes have similar performance")
            
            # Check token scaling
            print(f"   📊 Token Scaling Check:")
            print(f"     Original Anthropic tokens would be: ~{anthropic_result['prompt_tokens'] / 0.6396:.0f}")
            print(f"     Scaled down to: {anthropic_result['prompt_tokens']} tokens")
            
            # Store for summary
            performance_summary.append({
                'prompt': prompt_data['name'],
                'openai_tps': openai_tokens_per_sec,
                'anthropic_tps': anthropic_tokens_per_sec,
                'openai_time': openai_result['duration'],
                'anthropic_time': anthropic_result['duration']
            })
            
        else:
            print("❌ Could not compare - one or both tests failed")
            
        print()
    
    # Final summary
    if performance_summary:
        print("🏁 OVERALL PROXY PERFORMANCE SUMMARY")
        print("=" * 50)
        avg_openai_tps = sum(p['openai_tps'] for p in performance_summary) / len(performance_summary)
        avg_anthropic_tps = sum(p['anthropic_tps'] for p in performance_summary) / len(performance_summary)
        avg_openai_time = sum(p['openai_time'] for p in performance_summary) / len(performance_summary)
        avg_anthropic_time = sum(p['anthropic_time'] for p in performance_summary) / len(performance_summary)
        
        print(f"📊 Average Performance:")
        print(f"   🟦 Proxy → OpenAI: {avg_openai_tps:.1f} tokens/sec (avg {avg_openai_time:.2f}s)")
        print(f"   🟪 Proxy → Anthropic: {avg_anthropic_tps:.1f} tokens/sec (avg {avg_anthropic_time:.2f}s)")
        
        if avg_openai_tps > avg_anthropic_tps:
            overall_diff = ((avg_openai_tps / avg_anthropic_tps) - 1) * 100
            print(f"🏆 OVERALL WINNER: Proxy → OpenAI route is {overall_diff:.1f}% faster on average")
        else:
            overall_diff = ((avg_anthropic_tps / avg_openai_tps) - 1) * 100
            print(f"🏆 OVERALL WINNER: Proxy → Anthropic route is {overall_diff:.1f}% faster on average")
        
        print()
        print("💡 RECOMMENDATIONS:")
        print("   • Use glm-4.5-openai for fastest performance")
        print("   • Use glm-4.5-anthropic for text-only with token scaling")
        print("   • Use glm-4.5 (auto) for smart routing based on content")

if __name__ == "__main__":
    run_proxy_performance_test()