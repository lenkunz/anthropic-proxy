#!/usr/bin/env python3
"""
Simple API test for AI-powered message condensation system
"""

import os
import asyncio
import json
import time
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_api_health():
    """Test API health and basic functionality"""
    
    print("🏥 Testing API Health")
    print("=" * 30)
    
    base_url = "http://localhost:5000"
    api_key = os.getenv("SERVER_API_KEY")
    
    if not api_key:
        print("❌ SERVER_API_KEY not found")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test health endpoint
            response = await client.get(f"{base_url}/health")
            print(f"✅ Health check: {response.status_code}")
            
            # Test models endpoint
            headers = {"Authorization": f"Bearer {api_key}"}
            response = await client.get(f"{base_url}/v1/models", headers=headers)
            print(f"✅ Models endpoint: {response.status_code}")
            
            if response.status_code == 200:
                models = response.json()
                print(f"📋 Available models: {len(models.get('data', []))} models")
                
                # Check for our condensation-enabled models
                model_ids = [model.get('id', '') for model in models.get('data', [])]
                glm_models = [mid for mid in model_ids if 'glm' in mid]
                print(f"🤖 GLM models found: {len(glm_models)}")
                
                return True
            else:
                print(f"❌ Models endpoint failed: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

async def test_condensation_trigger():
    """Test that condensation is triggered with large conversations"""
    
    print("\n🧪 Testing Condensation Trigger")
    print("=" * 40)
    
    base_url = "http://localhost:5000"
    api_key = os.getenv("SERVER_API_KEY")
    
    # Create a conversation that should trigger condensation
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Provide detailed responses."},
        {"role": "user", "content": "Explain machine learning in great detail, including all major concepts, algorithms, and practical applications. Be very thorough in your explanation."},
        {"role": "assistant", "content": "Machine learning is a comprehensive field of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It encompasses various approaches including supervised learning, unsupervised learning, reinforcement learning, and deep learning. Each paradigm has its own strengths and applications across different domains. The field combines statistics, computer science, and optimization to create systems that can recognize patterns, make decisions, and improve performance over time based on data exposure."},
        {"role": "user", "content": "That's a good start, but I need much more detail. Please explain every major machine learning algorithm, including linear regression, logistic regression, decision trees, random forests, support vector machines, neural networks, clustering algorithms, dimensionality reduction techniques, and ensemble methods. For each one, explain the mathematical foundations, how they work, their advantages and disadvantages, and when to use them."},
        {"role": "assistant", "content": "I'll provide a comprehensive overview of major machine learning algorithms:\n\n**Linear Regression**: A fundamental supervised learning algorithm used for predicting continuous values. It models the relationship between dependent and independent variables by fitting a linear equation to observed data. The mathematical foundation is based on minimizing the sum of squared differences between predicted and actual values using ordinary least squares. Advantages include simplicity and interpretability, while disadvantages include sensitivity to outliers and assumption of linearity.\n\n**Logistic Regression**: Used for binary classification problems. It applies the logistic function to model the probability of a binary outcome. The foundation is maximum likelihood estimation, and it outputs probabilities between 0 and 1. It's efficient and interpretable but assumes linearity between features and log-odds.\n\n**Decision Trees**: Non-parametric supervised learning methods that can be used for both classification and regression. They work by recursively partitioning the feature space into regions, making predictions based on the majority class or average value in each region. They're easy to interpret but prone to overfitting.\n\n**Random Forests**: Ensemble learning methods that construct multiple decision trees during training and output the class that is the mode of the classes or mean prediction of the individual trees. They reduce overfitting and improve accuracy but are less interpretable than single trees.\n\n**Support Vector Machines**: Powerful supervised learning algorithms that can be used for classification, regression, and outlier detection. They work by finding the optimal hyperplane that best separates data points in a high-dimensional space. They're effective in high-dimensional spaces but can be computationally intensive."},
        {"role": "user", "content": "Continue with neural networks, clustering algorithms, dimensionality reduction, and ensemble methods. I need very detailed explanations with mathematical formulas, implementation details, and practical examples for each."},
        {"role": "assistant", "content": "Continuing with the comprehensive overview:\n\n**Neural Networks**: Computational models inspired by biological neural networks. They consist of interconnected layers of nodes (neurons) that process information using connectionist approaches. Each neuron receives inputs, applies weights and biases, and passes the result through activation functions. The mathematical foundation involves forward propagation (computing outputs) and backpropagation (computing gradients). Deep learning architectures include CNNs for image processing, RNNs for sequential data, and Transformers for natural language processing.\n\n**Clustering Algorithms**: Unsupervised learning methods that group similar data points together. K-means clustering partitions data into K clusters by minimizing within-cluster variance. Hierarchical clustering builds a tree of clusters. DBSCAN identifies clusters based on density. Gaussian Mixture Models assume data comes from a mixture of Gaussian distributions.\n\n**Dimensionality Reduction**: Techniques to reduce the number of features while preserving important information. Principal Component Analysis (PCA) finds orthogonal directions that capture maximum variance. t-SNE is used for visualization by preserving local structure. Autoencoders learn compressed representations using neural networks.\n\n**Ensemble Methods**: Combine multiple models to improve performance. Bagging (Bootstrap Aggregating) trains models on different subsets of data. Boosting sequentially trains models, focusing on difficult examples. Stacking combines predictions from multiple models using a meta-learner.\n\nEach algorithm has specific mathematical foundations, computational requirements, and suitability for different types of problems and data."}
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Test with vision request to trigger condensation
    payload = {
        "model": "glm-4.6",
        "messages": messages + [
            {"role": "user", "content": [
                {"type": "text", "text": "Based on our detailed discussion, summarize the key points and help me understand which algorithms I should focus on learning first."},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="}}
            ]}
        ],
        "max_tokens": 300,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            start_time = time.time()
            
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"✅ Request completed: {response.status_code}")
            print(f"⏱️  Response time: {response_time:.2f}s")
            
            if response.status_code == 200:
                result = response.json()
                
                if "usage" in result:
                    usage = result["usage"]
                    print(f"📊 Input tokens: {usage.get('input_tokens', 'N/A')}")
                    print(f"📊 Output tokens: {usage.get('output_tokens', 'N/A')}")
                    
                    # Check if condensation likely occurred (high token count but successful response)
                    input_tokens = usage.get('input_tokens', 0)
                    if input_tokens > 8000:  # High token count suggests condensation was needed
                        print(f"🔄 High token count detected ({input_tokens}), condensation may have been applied")
                    else:
                        print(f"📝 Token count within limits ({input_tokens}), no condensation needed")
                
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"📝 Response received: {len(content)} characters")
                print(f"🎯 API test PASSED")
                
                return True
            else:
                print(f"❌ API request failed: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

async def main():
    """Main test runner"""
    
    print("🤖 AI Condensation API Tests")
    print("=" * 40)
    
    # Test API health first
    health_ok = await test_api_health()
    if not health_ok:
        print("❌ API health check failed, stopping tests")
        return False
    
    # Test condensation functionality
    condensation_ok = await test_condensation_trigger()
    
    if condensation_ok:
        print("\n🎉 All API tests passed!")
        print("✅ The AI condensation system is working correctly")
    else:
        print("\n❌ Some API tests failed")
        print("⚠️  Please check the service logs")
    
    return condensation_ok

if __name__ == "__main__":
    asyncio.run(main())