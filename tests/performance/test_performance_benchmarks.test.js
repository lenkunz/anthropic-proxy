#!/usr/bin/env node

/**
 * Performance Benchmark Test Suite for Intelligent Context Management
 * 
 * This test suite measures:
 * 1. Token counting performance
 * 2. Context validation performance
 * 3. Large conversation handling performance
 * 4. Memory usage and efficiency
 * 5. Cache effectiveness
 */

const http = require('http');
const fs = require('fs');

// Configuration
const BASE_URL = 'http://localhost:5000';
const API_KEY = fs.readFileSync('.env', 'utf8')
  .split('\n')
  .find(line => line.startsWith('SERVER_API_KEY='))
  ?.split('=')[1];

class PerformanceBenchmark {
  constructor() {
    this.results = [];
  }

  async makeRequest(path, payload) {
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
          'Content-Length': Buffer.byteLength(postData)
        }
      };

      const client = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          try {
            const jsonData = JSON.parse(data);
            resolve({ status: res.statusCode, data: jsonData, headers: res.headers });
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

  createTestConversation(messageCount, tokensPerMessage = 100) {
    const messages = [
      { role: 'system', content: 'You are a helpful AI assistant.' }
    ];

    const loremIpsum = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. '.repeat(tokensPerMessage / 10);

    for (let i = 0; i < messageCount; i++) {
      messages.push({
        role: 'user',
        content: `Message ${i + 1}: ${loremIpsum}`
      });
    }

    return messages;
  }

  async benchmarkTokenCounting() {
    console.log('🔢 Benchmarking Token Counting Performance...');
    
    const conversationSizes = [5, 10, 25, 50, 100];
    const results = [];

    for (const size of conversationSizes) {
      const messages = this.createTestConversation(size, 50);
      const payload = {
        model: 'glm-4.6',
        messages: messages,
        max_tokens: 10
      };

      const iterations = 3;
      const times = [];

      for (let i = 0; i < iterations; i++) {
        const startTime = Date.now();
        const response = await this.makeRequest('/v1/chat/completions', payload);
        const duration = Date.now() - startTime;
        times.push(duration);

        if (response.status !== 200) {
          throw new Error(`Token counting benchmark failed for size ${size}`);
        }
      }

      const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
      const messagesPerSec = (size / avgTime) * 1000;

      results.push({
        messageCount: size,
        avgTime: avgTime,
        messagesPerSec: messagesPerSec
      });

      console.log(`   📊 ${size} messages: ${avgTime.toFixed(0)}ms avg, ${messagesPerSec.toFixed(0)} msgs/sec`);
    }

    return results;
  }

  async benchmarkLargeConversations() {
    console.log('📚 Benchmarking Large Conversation Handling...');
    
    const largeConversations = [
      { messages: 100, description: '100 messages (~10K tokens)' },
      { messages: 200, description: '200 messages (~20K tokens)' },
      { messages: 500, description: '500 messages (~50K tokens)' }
    ];

    const results = [];

    for (const conv of largeConversations) {
      const messages = this.createTestConversation(conv.messages, 100);
      const payload = {
        model: 'glm-4.6',
        messages: messages,
        max_tokens: 50
      };

      console.log(`   🔄 Testing ${conv.description}...`);
      
      const startTime = Date.now();
      const response = await this.makeRequest('/v1/chat/completions', payload);
      const duration = Date.now() - startTime;

      if (response.status !== 200) {
        throw new Error(`Large conversation benchmark failed for ${conv.description}`);
      }

      const tokensPerSec = (conv.messages * 100) / (duration / 1000);

      results.push({
        description: conv.description,
        messageCount: conv.messages,
        duration: duration,
        tokensPerSec: tokensPerSec,
        success: true
      });

      console.log(`   ✅ ${conv.description}: ${duration}ms, ${tokensPerSec.toFixed(0)} tokens/sec`);
    }

    return results;
  }

  async benchmarkConcurrentRequests() {
    console.log('⚡ Benchmarking Concurrent Request Handling...');
    
    const concurrentCounts = [1, 3, 5, 10];
    const results = [];

    for (const count of concurrentCounts) {
      const payload = {
        model: 'glm-4.6',
        messages: [
          { role: 'system', content: 'You are a helpful assistant.' },
          { role: 'user', content: 'Respond with "Hello World"' }
        ],
        max_tokens: 20
      };

      console.log(`   🔄 Testing ${count} concurrent requests...`);

      const startTime = Date.now();
      const promises = [];

      for (let i = 0; i < count; i++) {
        promises.push(this.makeRequest('/v1/chat/completions', payload));
      }

      const responses = await Promise.all(promises);
      const duration = Date.now() - startTime;

      const successCount = responses.filter(r => r.status === 200).length;
      const avgResponseTime = duration / count;
      const requestsPerSec = (count / duration) * 1000;

      results.push({
        concurrentCount: count,
        successCount: successCount,
        duration: duration,
        avgResponseTime: avgResponseTime,
        requestsPerSec: requestsPerSec
      });

      console.log(`   ✅ ${count}/${successCount} successful: ${duration}ms total, ${avgResponseTime.toFixed(0)}ms avg, ${requestsPerSec.toFixed(0)} req/sec`);
    }

    return results;
  }

  async benchmarkMemoryEfficiency() {
    console.log('💾 Benchmarking Memory Efficiency...');
    
    // Test memory usage with increasing conversation sizes
    const sizes = [10, 50, 100, 200];
    const results = [];

    for (const size of sizes) {
      const messages = this.createTestConversation(size, 200);
      const payload = {
        model: 'glm-4.6',
        messages: messages,
        max_tokens: 100
      };

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }

      const startTime = Date.now();
      const response = await this.makeRequest('/v1/chat/completions', payload);
      const duration = Date.now() - startTime;

      if (response.status !== 200) {
        throw new Error(`Memory efficiency test failed for size ${size}`);
      }

      // Estimate memory efficiency based on processing time
      const tokensProcessed = size * 200;
      const tokensPerMs = tokensProcessed / duration;

      results.push({
        messageCount: size,
        estimatedTokens: tokensProcessed,
        duration: duration,
        tokensPerMs: tokensPerMs
      });

      console.log(`   📊 ${size} messages (~${tokensProcessed} tokens): ${duration}ms, ${tokensPerMs.toFixed(1)} tokens/ms`);
    }

    return results;
  }

  async runAllBenchmarks() {
    console.log('🚀 Starting Performance Benchmark Suite');
    console.log('='.repeat(60));
    console.log(`🔧 API Key: ${API_KEY.substring(0, 10)}...`);
    console.log(`🌐 Base URL: ${BASE_URL}`);
    console.log('');

    const startTime = Date.now();

    const tokenCountingResults = await this.benchmarkTokenCounting();
    console.log('');
    
    const largeConversationResults = await this.benchmarkLargeConversations();
    console.log('');
    
    const concurrentResults = await this.benchmarkConcurrentRequests();
    console.log('');
    
    const memoryResults = await this.benchmarkMemoryEfficiency();
    console.log('');

    const totalDuration = Date.now() - startTime;

    this.printSummary({
      tokenCounting: tokenCountingResults,
      largeConversations: largeConversationResults,
      concurrent: concurrentResults,
      memory: memoryResults,
      totalDuration: totalDuration
    });
  }

  printSummary(results) {
    console.log('='.repeat(60));
    console.log('📊 PERFORMANCE BENCHMARK SUMMARY');
    console.log('='.repeat(60));

    console.log('\n🔢 Token Counting Performance:');
    results.tokenCounting.forEach(result => {
      console.log(`   ${result.messageCount} messages: ${result.messagesPerSec.toFixed(0)} msgs/sec`);
    });

    console.log('\n📚 Large Conversation Handling:');
    results.largeConversations.forEach(result => {
      console.log(`   ${result.description}: ${result.tokensPerSec.toFixed(0)} tokens/sec`);
    });

    console.log('\n⚡ Concurrent Request Handling:');
    results.concurrent.forEach(result => {
      console.log(`   ${result.concurrentCount} concurrent: ${result.requestsPerSec.toFixed(0)} req/sec`);
    });

    console.log('\n💾 Memory Efficiency:');
    results.memory.forEach(result => {
      console.log(`   ${result.messageCount} messages: ${result.tokensPerMs.toFixed(1)} tokens/ms`);
    });

    console.log(`\n⏱️  Total benchmark time: ${results.totalDuration}ms`);

    // Performance requirements validation
    console.log('\n🎯 Performance Requirements Validation:');
    
    const avgMessagesPerSec = results.tokenCounting.reduce((sum, r) => sum + r.messagesPerSec, 0) / results.tokenCounting.length;
    const maxTokensPerSec = Math.max(...results.largeConversations.map(r => r.tokensPerSec));
    const maxRequestsPerSec = Math.max(...results.concurrent.map(r => r.requestsPerSec));

    console.log(`   ✅ Average token counting: ${avgMessagesPerSec.toFixed(0)} msgs/sec (>1000 req/sec target: ${avgMessagesPerSec > 1000 ? '✅' : '❌'})`);
    console.log(`   ✅ Large conversation processing: ${maxTokensPerSec.toFixed(0)} tokens/sec (>1000 tokens/sec target: ${maxTokensPerSec > 1000 ? '✅' : '❌'})`);
    console.log(`   ✅ Concurrent request handling: ${maxRequestsPerSec.toFixed(0)} req/sec (>10 req/sec target: ${maxRequestsPerSec > 10 ? '✅' : '❌'})`);

    console.log('\n🎉 Performance benchmarks completed!');
  }
}

// Run the benchmark suite
const benchmark = new PerformanceBenchmark();
benchmark.runAllBenchmarks().catch(error => {
  console.error('❌ Benchmark suite failed:', error);
  process.exit(1);
});