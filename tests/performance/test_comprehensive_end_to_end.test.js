#!/usr/bin/env node

/**
 * Comprehensive End-to-End Test Suite for Intelligent Context Management
 * 
 * This test suite validates:
 * 1. All model variants work correctly
 * 2. Both endpoints (/v1/chat/completions and /v1/messages) function
 * 3. Intelligent context management is working
 * 4. Performance meets requirements
 * 5. Error handling works correctly
 */

const http = require('http');
const https = require('https');
const fs = require('fs');

// Configuration
const BASE_URL = 'http://localhost:5000';
const API_KEY = process.env.API_KEY || fs.readFileSync('.env', 'utf8')
  .split('\n')
  .find(line => line.startsWith('SERVER_API_KEY='))
  ?.split('=')[1];

if (!API_KEY) {
  console.error('❌ API_KEY not found in environment or .env file');
  process.exit(1);
}

class TestSuite {
  constructor() {
    this.results = [];
    this.totalTests = 0;
    this.passedTests = 0;
  }

  async runTest(testName, testFunction) {
    this.totalTests++;
    console.log(`🧪 Running: ${testName}`);
    
    try {
      const startTime = Date.now();
      await testFunction();
      const duration = Date.now() - startTime;
      
      console.log(`✅ ${testName} - PASSED (${duration}ms)`);
      this.results.push({ name: testName, status: 'PASSED', duration });
      this.passedTests++;
    } catch (error) {
      console.log(`❌ ${testName} - FAILED: ${error.message}`);
      this.results.push({ name: testName, status: 'FAILED', error: error.message });
    }
  }

  async makeRequest(path, payload, headers = {}) {
    return new Promise((resolve, reject) => {
      const postData = JSON.stringify(payload);
      const options = {
        hostname: 'localhost',
        port: 5000,
        path: path,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Length': Buffer.byteLength(postData),
          ...headers
        }
      };

      const client = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          try {
            const jsonData = JSON.parse(data);
            resolve({ status: res.statusCode, data: jsonData });
          } catch (e) {
            resolve({ status: res.statusCode, data: data });
          }
        });
      });

      client.on('error', reject);
      client.write(postData);
      client.end();
    });
  }

  async testModelVariants() {
    const models = ['glm-4.6', 'glm-4.6-openai', 'glm-4.6-anthropic'];
    
    for (const model of models) {
      const payload = {
        model: model,
        messages: [
          { role: 'system', content: 'You are a helpful assistant.' },
          { role: 'user', content: 'Say hello and tell me what model you are using.' }
        ],
        max_tokens: 50
      };

      const response = await this.makeRequest('/v1/chat/completions', payload);
      
      if (response.status !== 200) {
        throw new Error(`Model ${model} returned status ${response.status}: ${JSON.stringify(response.data)}`);
      }

      if (!response.data.choices || response.data.choices.length === 0) {
        throw new Error(`Model ${model} returned no choices`);
      }

      console.log(`   ✅ ${model}: ${response.data.choices[0].message?.content?.substring(0, 50) || 'No content'}...`);
    }
  }

  async testLargeConversationContext() {
    // Create a large conversation to test context management
    const messages = [
      { role: 'system', content: 'You are a helpful AI assistant specialized in software development.' }
    ];

    // Add many conversation turns to test context management
    for (let i = 0; i < 20; i++) {
      messages.push({
        role: 'user',
        content: `This is message ${i + 1}. Please provide a detailed response about software development topic ${i + 1}. Include code examples and best practices.`
      });
      
      if (i < 19) {
        messages.push({
          role: 'assistant',
          content: `Response ${i + 1}: Here's a comprehensive explanation about software development topic ${i + 1} with detailed information, best practices, and code examples that would help you understand the concepts thoroughly.`
        });
      }
    }

    const payload = {
      model: 'glm-4.6',
      messages: messages,
      max_tokens: 100
    };

    const startTime = Date.now();
    const response = await this.makeRequest('/v1/chat/completions', payload);
    const duration = Date.now() - startTime;

    if (response.status !== 200) {
      throw new Error(`Large conversation test failed with status ${response.status}`);
    }

    if (duration > 10000) { // 10 second threshold
      throw new Error(`Large conversation took too long: ${duration}ms`);
    }

    console.log(`   ✅ Large conversation processed in ${duration}ms`);
  }

  async testMessagesEndpoint() {
    const payload = {
      model: 'glm-4.6-anthropic',
      messages: [
        { role: 'user', content: 'Hello! Please respond with a brief greeting.' }
      ],
      max_tokens: 50
    };

    const response = await this.makeRequest('/v1/messages', payload);
    
    if (response.status !== 200) {
      throw new Error(`/v1/messages endpoint returned status ${response.status}`);
    }

    if (!response.data.content || response.data.content.length === 0) {
      throw new Error(`/v1/messages endpoint returned no content`);
    }

    console.log(`   ✅ /v1/messages endpoint working: ${response.data.content[0]?.text?.substring(0, 50) || 'No text'}...`);
  }

  async testErrorHandling() {
    // Test with invalid model
    const payload = {
      model: 'invalid-model-name',
      messages: [
        { role: 'user', content: 'Hello' }
      ],
      max_tokens: 50
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    
    if (response.status === 200) {
      throw new Error('Invalid model should have returned an error');
    }

    console.log(`   ✅ Error handling working: invalid model returned ${response.status}`);
  }

  async testPerformanceRequirements() {
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: 'Respond quickly with "Hello World"' }
      ],
      max_tokens: 20
    };

    const iterations = 5;
    const times = [];

    for (let i = 0; i < iterations; i++) {
      const startTime = Date.now();
      const response = await this.makeRequest('/v1/chat/completions', payload);
      const duration = Date.now() - startTime;
      times.push(duration);

      if (response.status !== 200) {
        throw new Error(`Performance test iteration ${i + 1} failed`);
      }
    }

    const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
    const maxTime = Math.max(...times);

    console.log(`   ✅ Performance: avg ${avgTime.toFixed(0)}ms, max ${maxTime}ms`);

    if (avgTime > 5000) { // 5 second average threshold
      throw new Error(`Average response time too high: ${avgTime}ms`);
    }
  }

  async testConfigurationIntegration() {
    // Test that configuration is properly loaded
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'user', content: 'Test message' }
      ],
      max_tokens: 10
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    
    if (response.status !== 200) {
      throw new Error('Configuration integration test failed');
    }

    // Check if response includes usage information
    if (response.data.usage) {
      console.log(`   ✅ Usage tracking working: ${response.data.usage.input_tokens} input, ${response.data.usage.output_tokens} output tokens`);
    }
  }

  async runAllTests() {
    console.log('🚀 Starting Comprehensive End-to-End Test Suite');
    console.log('='.repeat(60));
    console.log(`🔧 API Key: ${API_KEY.substring(0, 10)}...`);
    console.log(`🌐 Base URL: ${BASE_URL}`);
    console.log('');

    await this.runTest('Model Variants Test', () => this.testModelVariants());
    await this.runTest('Large Conversation Context', () => this.testLargeConversationContext());
    await this.runTest('Messages Endpoint Test', () => this.testMessagesEndpoint());
    await this.runTest('Error Handling Test', () => this.testErrorHandling());
    await this.runTest('Performance Requirements Test', () => this.testPerformanceRequirements());
    await this.runTest('Configuration Integration Test', () => this.testConfigurationIntegration());

    this.printSummary();
  }

  printSummary() {
    console.log('');
    console.log('='.repeat(60));
    console.log('📊 TEST SUMMARY');
    console.log('='.repeat(60));
    
    this.results.forEach(result => {
      const status = result.status === 'PASSED' ? '✅' : '❌';
      const duration = result.duration ? ` (${result.duration}ms)` : '';
      const error = result.error ? ` - ${result.error}` : '';
      console.log(`${status} ${result.name}${duration}${error}`);
    });

    console.log('');
    console.log(`Overall Result: ${this.passedTests}/${this.totalTests} tests passed`);
    console.log(`Success Rate: ${((this.passedTests / this.totalTests) * 100).toFixed(1)}%`);

    if (this.passedTests === this.totalTests) {
      console.log('🎉 All tests passed! Intelligent Context Management System is working correctly.');
    } else {
      console.log('⚠️  Some tests failed. Please check the implementation.');
      process.exit(1);
    }
  }
}

// Run the test suite
const testSuite = new TestSuite();
testSuite.runAllTests().catch(error => {
  console.error('❌ Test suite failed:', error);
  process.exit(1);
});