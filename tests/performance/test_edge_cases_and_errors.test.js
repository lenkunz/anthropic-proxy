#!/usr/bin/env node

/**
 * Edge Cases and Error Handling Test Suite
 * 
 * This test suite validates:
 * 1. Graceful degradation when components fail
 * 2. Handling of malformed inputs
 * 3. Boundary conditions
 * 4. Error recovery mechanisms
 * 5. Configuration edge cases
 */

const http = require('http');
const fs = require('fs');

// Configuration
const BASE_URL = 'http://localhost:5000';
const API_KEY = fs.readFileSync('.env', 'utf8')
  .split('\n')
  .find(line => line.startsWith('SERVER_API_KEY='))
  ?.split('=')[1];

class EdgeCaseTestSuite {
  constructor() {
    this.results = [];
    this.totalTests = 0;
    this.passedTests = 0;
  }

  async runTest(testName, testFunction, expectError = false) {
    this.totalTests++;
    console.log(`🧪 Running: ${testName}`);
    
    try {
      const startTime = Date.now();
      await testFunction();
      const duration = Date.now() - startTime;
      
      if (expectError) {
        console.log(`❌ ${testName} - FAILED: Expected error but got success (${duration}ms)`);
        this.results.push({ name: testName, status: 'FAILED', error: 'Expected error but got success' });
      } else {
        console.log(`✅ ${testName} - PASSED (${duration}ms)`);
        this.results.push({ name: testName, status: 'PASSED', duration });
        this.passedTests++;
      }
    } catch (error) {
      const duration = Date.now() - startTime;
      if (expectError) {
        console.log(`✅ ${testName} - PASSED (expected error: ${error.message})`);
        this.results.push({ name: testName, status: 'PASSED', duration, note: `Expected error: ${error.message}` });
        this.passedTests++;
      } else {
        console.log(`❌ ${testName} - FAILED: ${error.message}`);
        this.results.push({ name: testName, status: 'FAILED', error: error.message });
      }
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
            if (res.statusCode >= 400) {
              reject(new Error(`HTTP ${res.statusCode}: ${data}`));
            } else {
              resolve({ status: res.statusCode, data: jsonData });
            }
          } catch (e) {
            if (res.statusCode >= 400) {
              reject(new Error(`HTTP ${res.statusCode}: ${data}`));
            } else {
              resolve({ status: res.statusCode, data: data });
            }
          }
        });
      });

      client.on('error', reject);
      client.write(postData);
      client.end();
    });
  }

  // Test 1: Empty messages array
  async testEmptyMessages() {
    const payload = {
      model: 'glm-4.6',
      messages: [],
      max_tokens: 50
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status === 200) {
      console.log('     Empty messages handled gracefully');
    }
  }

  // Test 2: Very long message content
  async testVeryLongMessage() {
    const longContent = 'A'.repeat(50000); // 50K characters
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'user', content: longContent }
      ],
      max_tokens: 10
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status === 200) {
      console.log('     Very long message handled successfully');
    }
  }

  // Test 3: Invalid message roles
  async testInvalidRoles() {
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'invalid_role', content: 'Test message' }
      ],
      max_tokens: 10
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status === 200) {
      console.log('     Invalid role handled gracefully');
    }
  }

  // Test 4: Missing required fields
  async testMissingRequiredFields() {
    const payload = {
      // Missing model field
      messages: [
        { role: 'user', content: 'Test message' }
      ]
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status >= 400) {
      console.log('     Missing required fields properly rejected');
    }
  }

  // Test 5: Zero max_tokens
  async testZeroMaxTokens() {
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'user', content: 'Test message' }
      ],
      max_tokens: 0
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status === 200) {
      console.log('     Zero max_tokens handled gracefully');
    }
  }

  // Test 6: Negative max_tokens
  async testNegativeMaxTokens() {
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'user', content: 'Test message' }
      ],
      max_tokens: -10
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status >= 400) {
      console.log('     Negative max_tokens properly rejected');
    }
  }

  // Test 7: Extremely large max_tokens
  async testExtremelyLargeMaxTokens() {
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'user', content: 'Test message' }
      ],
      max_tokens: 1000000
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status === 200) {
      console.log('     Large max_tokens handled gracefully');
    }
  }

  // Test 8: Malformed JSON content
  async testMalformedContent() {
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'user', content: { invalid: 'object' } }
      ],
      max_tokens: 10
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status === 200) {
      console.log('     Malformed content handled gracefully');
    }
  }

  // Test 9: Unicode and special characters
  async testUnicodeContent() {
    const unicodeContent = 'Hello 🌍! Test with émojis and spëcial chars: 中文, русский, العربية, हिन्दी';
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'user', content: unicodeContent }
      ],
      max_tokens: 50
    };

    const response = await this.makeRequest('/v1/chat/completions', payload);
    if (response.status === 200) {
      console.log('     Unicode content handled successfully');
    }
  }

  // Test 10: Invalid API key
  async testInvalidApiKey() {
    const payload = {
      model: 'glm-4.6',
      messages: [
        { role: 'user', content: 'Test message' }
      ],
      max_tokens: 10
    };

    return new Promise((resolve, reject) => {
      const postData = JSON.stringify(payload);
      const options = {
        hostname: 'localhost',
        port: 5000,
        path: '/v1/chat/completions',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer invalid_api_key',
          'Content-Length': Buffer.byteLength(postData)
        }
      };

      const client = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          if (res.status