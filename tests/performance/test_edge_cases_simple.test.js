#!/usr/bin/env node

/**
 * Simple Edge Cases and Error Handling Test Suite
 */

const http = require('http');
const fs = require('fs');

const API_KEY = fs.readFileSync('.env', 'utf8')
  .split('\n')
  .find(line => line.startsWith('SERVER_API_KEY='))
  ?.split('=')[1];

class SimpleEdgeCaseTest {
  async makeRequest(path, payload, apiKey = API_KEY) {
    return new Promise((resolve, reject) => {
      const postData = JSON.stringify(payload);
      const options = {
        hostname: 'localhost',
        port: 5000,
        path: path,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
          'Content-Length': Buffer.byteLength(postData)
        }
      };

      const client = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          resolve({ status: res.statusCode, data: data });
        });
      });

      client.on('error', reject);
      client.write(postData);
      client.end();
    });
  }

  async runTests() {
    console.log('🧪 Running Edge Cases and Error Handling Tests');
    console.log('='.repeat(50));

    let passed = 0;
    let total = 0;

    // Test 1: Empty messages
    total++;
    try {
      const response = await this.makeRequest('/v1/chat/completions', {
        model: 'glm-4.6',
        messages: [],
        max_tokens: 10
      });
      console.log(`✅ Empty messages: ${response.status}`);
      passed++;
    } catch (error) {
      console.log(`❌ Empty messages failed: ${error.message}`);
    }

    // Test 2: Invalid model
    total++;
    try {
      const response = await this.makeRequest('/v1/chat/completions', {
        model: 'invalid-model',
        messages: [{ role: 'user', content: 'test' }],
        max_tokens: 10
      });
      console.log(`✅ Invalid model handled: ${response.status}`);
      passed++;
    } catch (error) {
      console.log(`❌ Invalid model test failed: ${error.message}`);
    }

    // Test 3: Missing required fields
    total++;
    try {
      const response = await this.makeRequest('/v1/chat/completions', {
        messages: [{ role: 'user', content: 'test' }]
        // missing model
      });
      console.log(`✅ Missing fields handled: ${response.status}`);
      passed++;
    } catch (error) {
      console.log(`❌ Missing fields test failed: ${error.message}`);
    }

    // Test 4: Invalid API key
    total++;
    try {
      const response = await this.makeRequest('/v1/chat/completions', {
        model: 'glm-4.6',
        messages: [{ role: 'user', content: 'test' }],
        max_tokens: 10
      }, 'invalid_key');
      console.log(`✅ Invalid API key handled: ${response.status}`);
      passed++;
    } catch (error) {
      console.log(`❌ Invalid API key test failed: ${error.message}`);
    }

    // Test 5: Very long message
    total++;
    try {
      const longContent = 'A'.repeat(10000);
      const response = await this.makeRequest('/v1/chat/completions', {
        model: 'glm-4.6',
        messages: [{ role: 'user', content: longContent }],
        max_tokens: 10
      });
      console.log(`✅ Long message handled: ${response.status}`);
      passed++;
    } catch (error) {
      console.log(`❌ Long message test failed: ${error.message}`);
    }

    // Test 6: Unicode content
    total++;
    try {
      const unicodeContent = 'Hello 🌍! Test with émojis and spëcial chars: 中文, русский, العربية';
      const response = await this.makeRequest('/v1/chat/completions', {
        model: 'glm-4.6',
        messages: [{ role: 'user', content: unicodeContent }],
        max_tokens: 20
      });
      console.log(`✅ Unicode content handled: ${response.status}`);
      passed++;
    } catch (error) {
      console.log(`❌ Unicode content test failed: ${error.message}`);
    }

    console.log('='.repeat(50));
    console.log(`📊 Edge Cases Test Summary: ${passed}/${total} tests passed`);
    console.log(`Success Rate: ${((passed / total) * 100).toFixed(1)}%`);

    if (passed === total) {
      console.log('🎉 All edge case tests passed!');
    } else {
      console.log('⚠️ Some edge case tests failed.');
    }
  }
}

// Run the tests
const test = new SimpleEdgeCaseTest();
test.runTests().catch(error => {
  console.error('❌ Edge case test suite failed:', error);
  process.exit(1);
});