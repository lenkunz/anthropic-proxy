#!/usr/bin/env python3
"""
Test to check if upstream servers themselves do token scaling.

This test compares:
- Direct OpenAI endpoint (should be baseline/no scaling)
- Direct Anthropic endpoint (suspected of inflating tokens)

Both use the same GLM-4.5 model, so token counts should theoretically be identical
unless one of the upstream servers is doing internal scaling.
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

# Direct upstream endpoints (NO PROXY)
OPENAI_DIRECT = "https://api.z.ai/api/coding/paas/v4"
ANTHROPIC_DIRECT = "https://api.z.ai/api/anthropic"

def test_direct_openai(prompt):
    """Test direct OpenAI endpoint"""
    url = f"{OPENAI_DIRECT}/chat/completions"
    print(f"📤 Testing direct OpenAI endpoint...")
    print(f"   🌐 URL: {url}")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5",
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
            print(f"   ✅ OpenAI response received in {duration:.2f}s")
            return {
                'prompt_tokens': result['usage']['prompt_tokens'],
                'completion_tokens': result['usage']['completion_tokens'],
                'total_tokens': result['usage']['total_tokens'],
                'duration': duration
            }
        else:
            print(f"❌ No usage data in OpenAI response: {result}")
            return None
            
    except Exception as e:
        print(f"❌ OpenAI direct test failed: {e}")
        return None

def test_direct_anthropic(prompt):
    """Test direct Anthropic endpoint"""
    url = f"{ANTHROPIC_DIRECT}/v1/messages"
    print(f"📤 Testing direct Anthropic endpoint...")
    print(f"   🌐 URL: {url}")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",  # Map to GLM-4.5
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 50
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        end_time = time.time()
        duration = end_time - start_time
        
        response.raise_for_status()
        result = response.json()
        
        if 'usage' in result:
            print(f"   ✅ Anthropic response received in {duration:.2f}s")
            return {
                'input_tokens': result['usage']['input_tokens'],
                'output_tokens': result['usage']['output_tokens'],
                'total_tokens': result['usage']['input_tokens'] + result['usage']['output_tokens'],
                'duration': duration
            }
        else:
            print(f"❌ No usage data in Anthropic response: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Anthropic direct test failed: {e}")
        return None

def run_upstream_scaling_test():
    """Run the upstream scaling comparison test"""
    
    print("🔍 UPSTREAM SERVER SCALING COMPARISON TEST")
    print("=" * 60)
    print("Testing if upstream servers themselves do token scaling")
    print("Both should use GLM-4.5, so tokens should match unless scaling occurs")
    print()
    
    # Test with different prompt sizes - MUCH LONGER for accurate scaling calculation
    test_prompts = [
        {
            "name": "Medium Prompt",
            "content": """Provide a comprehensive analysis of artificial intelligence and machine learning technologies. 
            Discuss the evolution from rule-based expert systems to modern neural networks and deep learning architectures. 
            Explain the key differences between supervised, unsupervised, and reinforcement learning paradigms, providing 
            specific examples of algorithms within each category. Detail the mathematical foundations underlying gradient 
            descent optimization, backpropagation in neural networks, and the role of activation functions in deep learning 
            models. Analyze the applications of convolutional neural networks in computer vision, recurrent neural networks 
            and transformers in natural language processing, and generative adversarial networks in content creation. 
            Discuss the challenges of training large-scale models, including computational requirements, data preprocessing, 
            regularization techniques to prevent overfitting, and the importance of hyperparameter tuning. Address the 
            ethical considerations in AI development, including algorithmic bias, privacy concerns, transparency requirements, 
            and the societal impact of automation. Examine the current state of artificial general intelligence research 
            and the technical barriers that remain in achieving human-level cognitive capabilities."""
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
            eventual consistency models, and the use of NoSQL databases for handling large-scale unstructured data. Address 
            security considerations in distributed environments, including authentication and authorization mechanisms, 
            encrypted communication protocols, zero-trust network architectures, and the challenges of maintaining security 
            boundaries across multiple services and cloud providers. Analyze performance optimization techniques including 
            caching strategies, load balancing algorithms, content delivery networks, and the importance of monitoring and 
            observability in maintaining system reliability. Discuss the evolution of cloud computing from Infrastructure 
            as a Service (IaaS) to Platform as a Service (PaaS) and Software as a Service (SaaS), including serverless 
            computing paradigms and their impact on application architecture and cost optimization."""
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
            cryptography in preparation for quantum computing threats. Address identity and access management (IAM) 
            systems, including multi-factor authentication mechanisms, privileged access management, and the integration 
            of biometric authentication technologies. Analyze cloud security considerations, including shared responsibility 
            models, container security, serverless security challenges, and the compliance requirements for various 
            industry standards such as SOC 2, ISO 27001, and PCI DSS. Discuss incident response planning and digital 
            forensics techniques, including threat hunting methodologies, memory analysis, network traffic analysis, 
            and the legal and procedural aspects of cybercrime investigation. Examine the human factor in cybersecurity, 
            including social engineering attacks, security awareness training programs, and the development of security 
            culture within organizations. Address emerging technologies and their security implications, including blockchain 
            security considerations, 5G network vulnerabilities, edge computing security challenges, and the potential 
            security risks associated with quantum computing and artificial general intelligence. Analyze regulatory 
            compliance requirements such as GDPR, CCPA, HIPAA, and industry-specific regulations, including their impact 
            on data protection strategies, privacy by design principles, and the balance between security measures and 
            user privacy rights."""
        },
        {
            "name": "Maximum Prompt",
            "content": """Conduct a comprehensive technical analysis of blockchain technology, cryptocurrency systems, and 
            decentralized finance (DeFi) ecosystems, examining their underlying cryptographic principles, consensus mechanisms, 
            economic models, and potential societal impacts. Begin with the fundamental concepts of distributed ledger 
            technology, explaining how cryptographic hash functions, Merkle trees, and digital signatures combine to create 
            immutable transaction records. Detail the various consensus algorithms employed in blockchain networks, including 
            Proof of Work (PoW) and its energy consumption implications, Proof of Stake (PoS) and its variants such as 
            Delegated Proof of Stake (DPoS) and Nominated Proof of Stake (NPoS), as well as newer approaches like Proof 
            of History, Proof of Authority, and Byzantine Fault Tolerant consensus mechanisms. Analyze the technical 
            architecture of major blockchain platforms including Bitcoin's UTXO model, Ethereum's account-based system 
            and virtual machine, and newer platforms like Solana, Cardano, and Polkadot, comparing their scalability 
            solutions, transaction throughput capabilities, and smart contract functionalities. Examine the development 
            and deployment of smart contracts, including the Solidity programming language for Ethereum, gas optimization 
            techniques, common security vulnerabilities such as reentrancy attacks and overflow issues, and formal verification 
            methods for ensuring contract correctness. Discuss Layer 2 scaling solutions including state channels, sidechains, 
            plasma frameworks, optimistic rollups, and zero-knowledge rollups, analyzing their trade-offs between scalability, 
            security, and decentralization. Explore the technical implementation of various cryptocurrency token standards 
            such as ERC-20, ERC-721 (NFTs), and ERC-1155, including their use cases in representing fungible and non-fungible 
            assets. Analyze decentralized finance protocols including automated market makers (AMMs), liquidity pools, 
            yield farming mechanisms, decentralized exchanges (DEXs), lending and borrowing protocols, and synthetic asset 
            platforms, examining their economic incentive structures and potential risks. Discuss interoperability solutions 
            for connecting disparate blockchain networks, including cross-chain bridges, atomic swaps, and emerging standards 
            for blockchain communication protocols. Address the environmental impact of blockchain technologies, particularly 
            energy-intensive proof-of-work systems, and examine sustainable alternatives and carbon offset mechanisms. 
            Analyze regulatory challenges and compliance considerations for blockchain-based financial services, including 
            anti-money laundering (AML) requirements, know-your-customer (KYC) procedures, and the classification of digital 
            assets by various regulatory bodies. Examine privacy-focused blockchain implementations including zero-knowledge 
            proofs, ring signatures, stealth addresses, and mixing services, along with their potential applications in 
            protecting user privacy while maintaining network transparency. Discuss the integration of blockchain technology 
            with other emerging technologies such as artificial intelligence, Internet of Things (IoT), and edge computing, 
            exploring potential use cases in supply chain management, digital identity verification, decentralized storage 
            systems, and autonomous organizations. Address the challenges of blockchain governance, including on-chain and 
            off-chain decision-making processes, token-based voting mechanisms, and the balance between decentralization 
            and effective project management. Analyze the potential societal implications of widespread blockchain adoption, 
            including its impact on traditional financial institutions, central bank digital currencies (CBDCs), financial 
            inclusion in underbanked populations, and the potential for creating more transparent and accountable governance 
            systems through blockchain-based voting and record-keeping mechanisms."""
        }
    ]
    
    for i, prompt_data in enumerate(test_prompts, 1):
        print(f"🧪 TEST {i}: {prompt_data['name']}")
        print("-" * 50)
        
        # Test OpenAI direct (baseline)
        openai_result = test_direct_openai(prompt_data['content'])
        time.sleep(1)  # Rate limiting
        
        # Test Anthropic direct (suspected scaling)
        anthropic_result = test_direct_anthropic(prompt_data['content'])
        time.sleep(1)  # Rate limiting
        
        if openai_result and anthropic_result:
            print(f"📊 RESULTS COMPARISON:")
            print(f"   🟦 OpenAI Direct:    {openai_result['prompt_tokens']} input tokens")
            print(f"   🟪 Anthropic Direct: {anthropic_result['input_tokens']} input tokens")
            
            # Calculate performance rates (tokens/sec)
            openai_tokens_per_sec = openai_result['total_tokens'] / openai_result['duration']
            anthropic_tokens_per_sec = anthropic_result['total_tokens'] / anthropic_result['duration']
            
            print(f"   ⚡ Performance Rates:")
            print(f"     🟦 OpenAI: {openai_tokens_per_sec:.1f} tokens/sec ({openai_result['duration']:.2f}s)")
            print(f"     🟪 Anthropic: {anthropic_tokens_per_sec:.1f} tokens/sec ({anthropic_result['duration']:.2f}s)")
            
            # Calculate difference and ratios
            difference = anthropic_result['input_tokens'] - openai_result['prompt_tokens']
            if difference > 0:
                inflation_ratio = anthropic_result['input_tokens'] / openai_result['prompt_tokens']
                # Calculate what base context would scale to 200k with this ratio
                base_context_est = 200000 / inflation_ratio
                print(f"   📈 INFLATION: +{difference} tokens ({inflation_ratio:.3f}x)")
                print(f"   💡 Anthropic inflates by {((inflation_ratio - 1) * 100):.1f}%")
                print(f"   📐 Base context estimate: {base_context_est:,.0f} tokens → 200k")
                print(f"   📊 Token ratio: {openai_result['prompt_tokens']}/{anthropic_result['input_tokens']} = {(openai_result['prompt_tokens']/anthropic_result['input_tokens']):.6f}")
            elif difference < 0:
                deflation_ratio = openai_result['prompt_tokens'] / anthropic_result['input_tokens']
                print(f"   📉 DEFLATION: {difference} tokens ({deflation_ratio:.3f}x)")
            else:
                print(f"   ✅ IDENTICAL: Same token count")
                
            print(f"   🔢 Total tokens - OpenAI: {openai_result['total_tokens']}, Anthropic: {anthropic_result['total_tokens']}")
            
        else:
            print("❌ Could not compare - one or both tests failed")
            
        print()
    
    print("🎯 ANALYSIS:")
    print("- If Anthropic shows MORE tokens: Anthropic endpoint inflates tokens")  
    print("- If OpenAI shows MORE tokens: OpenAI endpoint inflates tokens")
    print("- If tokens match: Neither endpoint does internal scaling")
    print("- Both use GLM-4.5 model, so differences indicate upstream scaling")

if __name__ == "__main__":
    run_upstream_scaling_test()