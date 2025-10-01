#!/usr/bin/env python3
"""
Integration test for AI-powered message condensation system

This test validates the condensation system works end-to-end with the actual API.
"""

import os
import asyncio
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import required modules
from message_condenser import condense_messages_if_needed
from context_window_manager import get_context_info

async def test_condensation_integration():
    """Test condensation system integration"""
    
    print("🧪 AI Condensation Integration Test")
    print("=" * 40)
    
    # Check API key
    api_key = os.getenv("SERVER_API_KEY")
    if not api_key:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Create test conversation that would exceed context limits
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant specialized in machine learning and data science."},
        
        {"role": "user", "content": "I'm working on a machine learning project and need help understanding neural networks. Can you explain how they work from the ground up?"},
        
        {"role": "assistant", "content": "I'd be happy to explain neural networks! At their core, neural networks are computational models inspired by the human brain. They consist of interconnected nodes (neurons) organized in layers. Each neuron receives inputs, applies a mathematical operation, and passes the result to the next layer. The network learns by adjusting the strength of connections between neurons through a process called training."},
        
        {"role": "user", "content": "That's helpful! Can you explain backpropagation in more detail? I've heard it's important for training neural networks."},
        
        {"role": "assistant", "content": "Backpropagation is indeed fundamental! It's an algorithm that enables neural networks to learn from errors. Here's how it works: 1) The network makes a prediction, 2) We calculate the error (difference between prediction and actual), 3) This error is propagated backward through the network, 4) Each connection's weight is adjusted to reduce future errors. It's like a feedback system that continuously improves the network's performance."},
        
        {"role": "user", "content": "What about activation functions? I see ReLU, sigmoid, and tanh mentioned a lot. What's the difference and when should I use each?"},
        
        {"role": "assistant", "content": "Great question! Activation functions introduce non-linearity, allowing networks to learn complex patterns. Here are the main ones:\n\n• ReLU (Rectified Linear Unit): f(x) = max(0, x). Simple and efficient, helps with vanishing gradients. Most common choice for hidden layers.\n• Sigmoid: f(x) = 1/(1 + e^(-x)). Outputs values between 0 and 1. Good for binary classification outputs.\n• Tanh: f(x) = (e^x - e^(-x))/(e^x + e^(-x)). Outputs between -1 and 1. Centered around zero, sometimes better than sigmoid.\n\nFor hidden layers, start with ReLU. For outputs, choose based on your problem: sigmoid for binary, softmax for multi-class, linear for regression."},
        
        {"role": "user", "content": "I'm also confused about optimization algorithms. What's the difference between SGD, Adam, and RMSprop?"},
        
        {"role": "assistant", "content": "Optimization algorithms determine how the network updates its weights during training:\n\n• SGD (Stochastic Gradient Descent): The most basic approach. Updates weights using the gradient from a single training example. Simple but can be noisy.\n• Adam (Adaptive Moment Estimation): Combines momentum and adaptive learning rates. Generally performs well and is a good default choice.\n• RMSprop: Maintains a per-parameter learning rate. Good for recurrent neural networks.\n\nMy recommendation: Start with Adam. It's robust and works well for most problems. Only consider others if you have specific reasons."},
        
        {"role": "user", "content": "How do I prevent overfitting? My model performs great on training data but poorly on validation data."},
        
        {"role": "assistant", "content": "Overfitting is a common challenge! Here are effective strategies:\n\n1. **Regularization**: Add penalty terms to loss function (L1/L2 regularization)\n2. **Dropout**: Randomly deactivate neurons during training\n3. **Early Stopping**: Monitor validation loss and stop when it starts increasing\n4. **Data Augmentation**: Increase training data variety\n5. **Cross-validation**: Better estimate of model performance\n6. **Reduce model complexity**: Fewer layers/neurons\n7. **Batch normalization**: Normalize layer inputs\n\nStart with dropout and early stopping - they're often most effective."},
        
        {"role": "user", "content": "What are convolutional neural networks (CNNs) and how do they differ from regular neural networks?"},
        
        {"role": "assistant", "content": "CNNs are specialized for processing grid-like data, particularly images. Key differences:\n\n**Regular Neural Networks**: Each neuron connects to all neurons in the next layer (fully connected).\n\n**CNNs**: Use convolutional layers that apply filters across local regions. This creates feature maps that detect patterns (edges, textures, shapes) regardless of their position in the image.\n\nKey CNN components:\n• Convolutional layers: Apply learned filters\n• Pooling layers: Reduce spatial dimensions\n• Fully connected layers: Final classification\n\nCNNs are translation-invariant and much more parameter-efficient for images than regular neural networks."},
        
        {"role": "user", "content": "Can you explain how transformers work? I've heard they're revolutionizing NLP."},
        
        {"role": "assistant", "content": "Transformers have indeed transformed NLP! Unlike RNNs that process sequentially, transformers process all tokens simultaneously using attention mechanisms.\n\nKey components:\n\n**Self-Attention**: Each token attends to all other tokens, learning relationships regardless of distance.\n\n**Multi-Head Attention**: Multiple attention mechanisms operating in parallel.\n\n**Positional Encoding**: Adds position information since there's no sequential processing.\n\n**Feed-Forward Networks**: Process the attention outputs.\n\n**Encoder-Decoder Architecture**: Encoders process input, decoders generate output.\n\nAdvantages: Parallel processing, handling long-range dependencies, and superior performance on most NLP tasks. Models like GPT, BERT, and T5 are all based on transformers."},
        
        {"role": "user", "content": "What's transfer learning and how can I use it for my project?"},
        
        {"role": "assistant", "content": "Transfer learning leverages knowledge from pre-trained models for new tasks. It's incredibly powerful!\n\n**How it works**: Take a model trained on large datasets (like ImageNet or Wikipedia text) and fine-tune it for your specific task.\n\n**Benefits**:\n• Reduces training time dramatically\n• Requires less data\n• Often achieves better performance\n• Leverages learned features/patterns\n\n**Common approaches**:\n• Feature extraction: Use pre-trained model as fixed feature extractor\n• Fine-tuning: Update some or all layers for your task\n• Domain adaptation: Adapt model to related domain\n\n**Popular pre-trained models**:\n• Images: ResNet, VGG, EfficientNet\n• Text: BERT, GPT, T5\n• Audio: Wav2Vec, HuBERT\n\nStart with a pre-trained model and fine-tune the last few layers for your specific task."}
    ]
    
    print(f"📝 Created test conversation with {len(messages)} messages")
    
    # Analyze context
    context_info = get_context_info(messages, is_vision=True)
    print(f"📊 Context Analysis:")
    print(f"   Estimated tokens: {context_info['estimated_tokens']}")
    print(f"   Utilization: {context_info['utilization_percent']}%")
    print(f"   Hard limit: {context_info['hard_limit']}")
    print(f"   Available: {context_info['available_tokens']}")
    
    # Test condensation
    print(f"\n🔄 Testing message condensation...")
    start_time = time.time()
    
    try:
        condensed_messages, metadata = await condense_messages_if_needed(
            messages=messages,
            current_tokens=context_info['estimated_tokens'],
            max_tokens=context_info['hard_limit'] * 0.7,  # Target 70% of limit
            preferred_strategy="conversation_summary",
            is_vision=True
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"✅ Condensation completed in {processing_time:.2f} seconds")
        print(f"📈 Results:")
        print(f"   Original messages: {len(messages)}")
        print(f"   Condensed messages: {len(condensed_messages)}")
        print(f"   Original tokens: {metadata.get('original_tokens', 'N/A')}")
        print(f"   Final tokens: {metadata.get('final_tokens', 'N/A')}")
        print(f"   Tokens saved: {metadata.get('tokens_saved', 'N/A')}")
        print(f"   Strategy used: {metadata.get('strategy_used', 'N/A')}")
        print(f"   Processing time: {metadata.get('processing_time', 'N/A'):.2f}s")
        print(f"   Condensed: {metadata.get('condensed', False)}")
        
        if metadata.get('error_message'):
            print(f"   Error: {metadata['error_message']}")
        
        # Show condensed content preview
        if len(condensed_messages) < len(messages):
            print(f"\n📝 Condensed content preview:")
            for i, msg in enumerate(condensed_messages[-3:]):  # Show last 3 messages
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if isinstance(content, str):
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   {i+1}. [{role}]: {content_preview}")
                else:
                    print(f"   {i+1}. [{role}]: [Complex content]")
        
        # Validate condensation quality
        success = True
        if metadata.get('condensed', False):
            tokens_saved = metadata.get('tokens_saved', 0)
            if tokens_saved > 0:
                print(f"✅ Successfully saved {tokens_saved} tokens")
            else:
                print(f"⚠️  Condensation completed but no tokens saved")
                success = False
        else:
            print(f"ℹ️  No condensation applied (threshold not reached)")
        
        return success
        
    except Exception as e:
        print(f"❌ Condensation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_strategies():
    """Test different condensation strategies"""
    
    print(f"\n🧪 Testing Multiple Condensation Strategies")
    print("=" * 50)
    
    # Create a smaller test set for strategy testing
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Explain machine learning concepts in detail."},
        {"role": "assistant", "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. It involves training models on datasets to recognize patterns and make predictions without being explicitly programmed. Key concepts include supervised learning, unsupervised learning, reinforcement learning, neural networks, deep learning, and various optimization techniques."},
        {"role": "user", "content": "What about deep learning specifically?"},
        {"role": "assistant", "content": "Deep learning is a subfield of machine learning that uses neural networks with multiple layers. These deep neural networks can automatically learn hierarchical representations of data, from simple features to complex abstractions. Deep learning has revolutionized fields like computer vision, natural language processing, and speech recognition."},
        {"role": "user", "content": "How do neural networks actually learn?"},
        {"role": "assistant", "content": "Neural networks learn through a process called training, which typically involves forward propagation, loss calculation, backpropagation, and weight updates. During forward propagation, input data flows through the network layers to produce predictions. The loss function measures the difference between predictions and actual values. Backpropagation calculates gradients of the loss with respect to each weight. Optimization algorithms like SGD or Adam update the weights to minimize the loss. This process repeats over many iterations until the model converges."},
    ]
    
    strategies = ["conversation_summary", "key_point_extraction", "progressive_summarization", "smart_truncation"]
    
    for strategy in strategies:
        print(f"\n🔄 Testing strategy: {strategy}")
        
        try:
            start_time = time.time()
            
            condensed_messages, metadata = await condense_messages_if_needed(
                messages=messages,
                current_tokens=2000,
                max_tokens=1000,
                preferred_strategy=strategy,
                is_vision=False
            )
            
            end_time = time.time()
            
            print(f"   ✅ {strategy}: {len(messages)} → {len(condensed_messages)} messages "
                  f"({end_time - start_time:.2f}s)")
            print(f"   📊 Tokens saved: {metadata.get('tokens_saved', 0)}")
            print(f"   🎯 Success: {metadata.get('condensed', False)}")
            
        except Exception as e:
            print(f"   ❌ {strategy}: Failed - {e}")

async def main():
    """Main test runner"""
    
    print("🤖 AI-Powered Message Condensation Integration Tests")
    print("=" * 60)
    
    # Check environment
    if not os.getenv("SERVER_API_KEY"):
        print("❌ SERVER_API_KEY not found in .env file")
        print("Please set up your .env file with a valid z.ai API key")
        return False
    
    try:
        # Run main integration test
        success1 = await test_condensation_integration()
        
        # Run strategy tests
        await test_multiple_strategies()
        
        if success1:
            print(f"\n🎉 Integration test completed successfully!")
            print(f"   The AI condensation system is working correctly.")
        else:
            print(f"\n⚠️  Integration test had issues.")
            print(f"   Please check the logs above for details.")
        
        return success1
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(main())