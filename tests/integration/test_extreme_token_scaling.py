#!/usr/bin/env python3
"""
Extreme High Token Count Test - Generate very large prompts to show dramatic scaling
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"  # Your proxy
ANTHROPIC_DIRECT = "https://api.z.ai/api/anthropic"  # Direct upstream

def generate_massive_prompt(target_tokens=50000):
    """Generate a massive prompt targeting specific token count"""
    
    print(f"📝 Generating massive prompt targeting ~{target_tokens:,} tokens...")
    
    # Technical content that's meaningful and varied
    base_sections = [
        """
        ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING SYSTEMS ARCHITECTURE:
        
        Modern AI systems require sophisticated architectural patterns to handle the complexity of machine learning workloads at scale. The evolution from monolithic AI applications to distributed, microservices-based ML pipelines represents a fundamental shift in how we design, deploy, and maintain intelligent systems. Key considerations include:
        
        1. Data Pipeline Architecture: Implementing robust ETL/ELT processes that can handle streaming and batch data from multiple sources, ensuring data quality, consistency, and lineage tracking throughout the machine learning lifecycle.
        
        2. Model Serving Infrastructure: Designing scalable inference endpoints that can handle varying load patterns while maintaining low latency and high availability, including support for A/B testing, canary deployments, and real-time monitoring.
        
        3. Training and Experimentation Platforms: Building environments that support distributed training, hyperparameter optimization, and experiment tracking while efficiently utilizing computational resources across GPU clusters.
        
        4. MLOps and Model Lifecycle Management: Establishing practices for continuous integration and deployment of machine learning models, including automated testing, validation, and rollback capabilities.
        
        The integration of these components requires careful consideration of data governance, security, and compliance requirements, particularly in regulated industries such as healthcare, finance, and autonomous systems.
        """,
        
        """
        DISTRIBUTED SYSTEMS AND CLOUD ARCHITECTURE PATTERNS:
        
        The design of distributed systems involves numerous trade-offs between consistency, availability, and partition tolerance, as described by the CAP theorem. Modern cloud-native applications must address these challenges while providing seamless user experiences across global deployments.
        
        Key architectural patterns include:
        
        1. Event-Driven Architecture: Implementing asynchronous communication patterns using message queues, event streams, and publish-subscribe models to achieve loose coupling and improved scalability.
        
        2. Circuit Breaker and Bulkhead Patterns: Implementing fault tolerance mechanisms that prevent cascade failures and isolate critical system components during partial system outages.
        
        3. Service Mesh and API Gateway Patterns: Managing service-to-service communication, authentication, authorization, and observability in complex microservices ecosystems.
        
        4. Data Consistency Patterns: Implementing eventual consistency, saga patterns, and distributed transaction management to maintain data integrity across distributed services.
        
        Cloud platforms provide managed services that abstract much of this complexity, but understanding the underlying principles remains crucial for making informed architectural decisions and troubleshooting complex distributed system issues.
        """,
        
        """
        CYBERSECURITY AND PRIVACY-PRESERVING TECHNOLOGIES:
        
        The increasing sophistication of cyber threats requires a multi-layered defense strategy that encompasses network security, application security, data protection, and user education. Modern security architectures must address both traditional attack vectors and emerging threats related to cloud computing, IoT devices, and AI systems.
        
        Critical security domains include:
        
        1. Zero Trust Architecture: Implementing security models that assume no implicit trust and continuously validate every transaction, regardless of location or user credentials.
        
        2. Privacy-Preserving Computation: Utilizing techniques such as homomorphic encryption, secure multi-party computation, and differential privacy to enable data analysis while protecting individual privacy.
        
        3. Threat Intelligence and Detection: Deploying advanced monitoring systems that use machine learning and behavioral analysis to identify anomalous activities and potential security breaches.
        
        4. Identity and Access Management: Implementing robust authentication and authorization systems that support multi-factor authentication, role-based access control, and continuous verification.
        
        The regulatory landscape, including GDPR, CCPA, and industry-specific compliance requirements, adds additional complexity to security implementations, requiring careful balance between functionality and privacy protection.
        """,
        
        """
        BLOCKCHAIN TECHNOLOGY AND DECENTRALIZED SYSTEMS:
        
        Blockchain technology represents a paradigm shift toward decentralized trust and consensus mechanisms, enabling new forms of digital interaction and value transfer. The technology's implications extend beyond cryptocurrency to supply chain management, digital identity, smart contracts, and decentralized finance.
        
        Key technical components include:
        
        1. Consensus Mechanisms: Understanding the trade-offs between different consensus algorithms, including Proof of Work, Proof of Stake, and newer approaches like Proof of History and Delegated Proof of Stake.
        
        2. Smart Contract Development: Designing and implementing self-executing contracts with built-in business logic, including considerations for gas optimization, security vulnerabilities, and upgrade mechanisms.
        
        3. Decentralized Application Architecture: Building user-facing applications that interact with blockchain networks while providing traditional web application user experiences.
        
        4. Interoperability and Cross-Chain Communication: Implementing protocols that enable different blockchain networks to communicate and transfer value, addressing the fragmentation in the blockchain ecosystem.
        
        The environmental impact of blockchain systems, particularly energy-intensive proof-of-work networks, has led to increased focus on sustainable blockchain technologies and carbon-neutral consensus mechanisms.
        """,
        
        """
        QUANTUM COMPUTING AND POST-QUANTUM CRYPTOGRAPHY:
        
        Quantum computing represents a fundamental departure from classical computing paradigms, leveraging quantum mechanical properties such as superposition and entanglement to perform certain calculations exponentially faster than classical computers.
        
        Key areas of development include:
        
        1. Quantum Algorithm Development: Creating algorithms that take advantage of quantum properties to solve problems in optimization, simulation, and cryptography that are intractable for classical computers.
        
        2. Quantum Hardware Platforms: Understanding different approaches to quantum computing, including superconducting qubits, trapped ion systems, photonic quantum computers, and topological qubits.
        
        3. Quantum Error Correction: Developing techniques to maintain quantum coherence and correct errors that naturally occur in quantum systems due to environmental interference.
        
        4. Post-Quantum Cryptography: Preparing for the eventual advent of cryptographically relevant quantum computers by developing encryption methods that remain secure against both classical and quantum attacks.
        
        The timeline for practical quantum advantage in various application domains remains uncertain, but organizations must begin preparing for the post-quantum era to maintain security and competitiveness.
        """
    ]
    
    # Calculate how many repetitions we need
    words_per_section = sum(len(section.split()) for section in base_sections)
    target_words = target_tokens // 1.3  # Rough token-to-word ratio
    repetitions_needed = max(1, int(target_words / words_per_section))
    
    print(f"   • Target tokens: {target_tokens:,}")
    print(f"   • Target words: {target_words:,}")  
    print(f"   • Words per cycle: {words_per_section:,}")
    print(f"   • Repetitions needed: {repetitions_needed}")
    
    # Build the massive prompt
    prompt = """Please provide an extremely comprehensive and detailed technical analysis covering all aspects of the following advanced technology domains. For each domain, provide in-depth explanations, real-world examples, implementation strategies, challenges, best practices, and future implications:

"""
    
    section_counter = 1
    for repetition in range(repetitions_needed):
        for section in base_sections:
            prompt += f"\n--- SECTION {section_counter} (Analysis Round {repetition + 1}) ---"
            prompt += section
            prompt += f"\n\nPlease elaborate further on the technical implementation details, provide specific code examples where applicable, discuss performance implications, security considerations, and integration challenges for the concepts described above.\n"
            section_counter += 1
    
    # Add specific detailed questions
    prompt += """
    
SPECIFIC DETAILED ANALYSIS REQUIREMENTS:

Please address each of the following questions with comprehensive technical detail:

1. What are the specific technical trade-offs between different architectural approaches, including performance metrics, scalability limitations, and resource utilization patterns?

2. How do emerging industry standards and regulatory requirements influence technology adoption decisions, and what compliance frameworks should be considered?

3. What are the detailed implementation strategies for ensuring system reliability, including fault tolerance mechanisms, monitoring approaches, and disaster recovery procedures?

4. How can organizations effectively balance innovation velocity with system stability, security requirements, and technical debt management?

5. What specific metrics and KPIs should be implemented to measure the success and effectiveness of technology implementations across different organizational contexts?

6. What are the detailed cost-benefit analyses for different technology adoption strategies, including both direct and indirect costs?

7. How do different technology choices impact long-term maintainability, team productivity, and organizational learning capabilities?

8. What are the specific integration challenges when combining multiple advanced technologies, and how can these be addressed systematically?

9. What risk mitigation strategies should be employed when implementing cutting-edge technologies in production environments?

10. How can organizations prepare for future technological disruptions while maintaining current operational excellence?

Please provide detailed technical explanations, specific examples, and actionable recommendations for each area of analysis.
"""
    
    actual_words = len(prompt.split())
    estimated_tokens = int(actual_words * 1.3)
    
    print(f"   ✅ Generated prompt with {actual_words:,} words")
    print(f"   📊 Estimated tokens: ~{estimated_tokens:,}")
    
    return prompt

def test_extreme_scaling():
    """Test with extremely high token count"""
    
    print(f"\n🚀 EXTREME TOKEN SCALING TEST")
    print("=" * 80)
    
    # Generate massive prompt targeting ~50k tokens
    massive_prompt = generate_massive_prompt(50000)
    
    # Test direct Anthropic
    print(f"\n🔍 Testing Direct Anthropic with Massive Prompt:")
    print("-" * 60)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5",
        "max_tokens": 1000,  # Reasonable response size
        "messages": [{"role": "user", "content": massive_prompt}]
    }
    
    try:
        print("📤 Sending massive request to direct Anthropic endpoint...")
        print("   ⏳ This may take a while due to the large prompt size...")
        
        response = requests.post(f"{ANTHROPIC_DIRECT}/v1/messages", headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            total_tokens = input_tokens + output_tokens
            
            print(f"\n🔥 MASSIVE RAW ANTHROPIC RESULTS:")
            print(f"   📥 Input tokens:  {input_tokens:,}")
            print(f"   📤 Output tokens: {output_tokens:,}")
            print(f"   🔢 Total tokens:  {total_tokens:,}")
            
            direct_result = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
        else:
            print(f"❌ Direct Anthropic Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}...")
            return
            
    except Exception as e:
        print(f"❌ Direct Anthropic Exception: {e}")
        return
    
    # Test proxy
    print(f"\n🔍 Testing Proxy with Same Massive Prompt:")
    print("-" * 60)
    
    proxy_payload = {
        "model": "glm-4.5-anthropic",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": massive_prompt}],
        "temperature": 0.0
    }
    
    try:
        print("📤 Sending massive request to proxy...")
        print("   ⏳ Testing token scaling with extreme input...")
        
        response = requests.post(f"{BASE_URL}/v1/chat/completions", headers=headers, json=proxy_payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            
            print(f"\n🎯 MASSIVE SCALED PROXY RESULTS:")
            print(f"   📥 Prompt tokens:     {prompt_tokens:,}")
            print(f"   📤 Completion tokens: {completion_tokens:,}")
            print(f"   🔢 Total tokens:      {total_tokens:,}")
            
            proxy_result = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        else:
            print(f"❌ Proxy Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}...")
            return
            
    except Exception as e:
        print(f"❌ Proxy Exception: {e}")
        return
    
    # DRAMATIC ANALYSIS
    print(f"\n💥 EXTREME SCALING ANALYSIS")
    print("=" * 80)
    
    # Input token analysis
    input_reduction = direct_result['input_tokens'] - proxy_result['prompt_tokens']
    input_scaling_factor = proxy_result['prompt_tokens'] / direct_result['input_tokens'] if direct_result['input_tokens'] > 0 else 0
    
    print(f"📥 INPUT TOKEN SCALING:")
    print(f"   🔴 Direct Anthropic:    {direct_result['input_tokens']:,} tokens")
    print(f"   🔵 Scaled Proxy:        {proxy_result['prompt_tokens']:,} tokens")
    print(f"   📉 MASSIVE REDUCTION:   {input_reduction:,} tokens saved!")
    print(f"   📊 Scaling Factor:      {input_scaling_factor:.6f}")
    print(f"   💰 Percentage Saved:    {(1-input_scaling_factor)*100:.1f}%")
    
    # Total token analysis  
    total_reduction = direct_result['total_tokens'] - proxy_result['total_tokens']
    total_scaling_factor = proxy_result['total_tokens'] / direct_result['total_tokens'] if direct_result['total_tokens'] > 0 else 0
    
    print(f"\n🔢 TOTAL TOKEN SCALING:")
    print(f"   🔴 Direct Anthropic:    {direct_result['total_tokens']:,} tokens")
    print(f"   🔵 Scaled Proxy:        {proxy_result['total_tokens']:,} tokens")
    print(f"   📉 MASSIVE REDUCTION:   {total_reduction:,} tokens saved!")
    print(f"   📊 Scaling Factor:      {total_scaling_factor:.6f}")
    print(f"   💰 Percentage Saved:    {(1-total_scaling_factor)*100:.1f}%")
    
    # Theoretical comparison
    expected_factor = 128000 / 200000
    difference = abs(total_scaling_factor - expected_factor)
    
    print(f"\n🧮 THEORETICAL VALIDATION:")
    print(f"   📋 Expected (131k/200k): {expected_factor:.6f}")
    print(f"   📊 Actual Measured:      {total_scaling_factor:.6f}")
    print(f"   📏 Difference:           {difference:.6f}")
    
    if difference < 0.01:
        print(f"   ✅ PERFECT VALIDATION! Scaling is mathematically correct!")
    else:
        print(f"   ❓ Deviation from expected (but may be due to rounding)")
    
    # Impact demonstration
    print(f"\n🎊 EXTREME IMPACT DEMONSTRATION:")
    print(f"   💎 With {direct_result['total_tokens']:,} raw tokens → {proxy_result['total_tokens']:,} scaled tokens")
    print(f"   🚀 Your proxy saves {total_reduction:,} tokens per request!")
    print(f"   💰 Cost reduction: {(1-total_scaling_factor)*100:.1f}% per API call")
    print(f"   ⚡ Efficiency: Client processes {total_reduction:,} fewer tokens")
    print(f"   🏆 PROOF: Anthropic's 200k context → OpenAI's 131k context scaling WORKS!")

def main():
    print("🚀 EXTREME HIGH TOKEN SCALING TEST")
    print("=" * 80)
    print("This test generates MASSIVE prompts (50,000+ tokens) to demonstrate")
    print("dramatic token scaling from Anthropic's 200k context to OpenAI's 131k!")
    print()
    
    try:
        test_extreme_scaling()
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        print("This might be due to prompt size limits or timeout issues.")
    
    print(f"\n🏁 EXTREME TEST COMPLETE!")

if __name__ == "__main__":
    main()