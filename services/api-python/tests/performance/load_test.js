/**
 * k6 Load Testing Script for Employee Management System
 *
 * Tests API performance under various load conditions
 * Run with: k6 run load_test.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const authSuccessRate = new Rate('auth_success');
const cacheHitRate = new Rate('cache_hits');
const apiLatency = new Trend('api_latency');
const requestCounter = new Counter('requests_total');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 200 },   // Ramp up to 200 users
    { duration: '5m', target: 200 },   // Stay at 200 users
    { duration: '2m', target: 0 },     // Ramp down to 0 users
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],  // 95% under 500ms, 99% under 1s
    'http_req_failed': ['rate<0.01'],                  // Error rate < 1%
    'errors': ['rate<0.05'],                           // Custom error rate < 5%
    'auth_success': ['rate>0.95'],                     // Auth success > 95%
  },
};

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_VERSION = '/api/v1';

// Test data
const testUsers = [
  { username: 'loadtest1', password: 'Test123!@#', email: 'loadtest1@test.com' },
  { username: 'loadtest2', password: 'Test123!@#', email: 'loadtest2@test.com' },
  { username: 'loadtest3', password: 'Test123!@#', email: 'loadtest3@test.com' },
];

/**
 * Setup function - runs once before all iterations
 */
export function setup() {
  console.log('Setting up load test...');

  // Register test users
  const tokens = [];
  testUsers.forEach(user => {
    const registerPayload = JSON.stringify({
      username: user.username,
      email: user.email,
      password: user.password,
      full_name: `Load Test User ${user.username}`
    });

    const registerRes = http.post(
      `${BASE_URL}${API_VERSION}/auth/register`,
      registerPayload,
      { headers: { 'Content-Type': 'application/json' } }
    );

    if (registerRes.status === 200 || registerRes.status === 409) {
      // Login to get token
      const loginPayload = JSON.stringify({
        username: user.username,
        password: user.password
      });

      const loginRes = http.post(
        `${BASE_URL}${API_VERSION}/auth/login`,
        loginPayload,
        { headers: { 'Content-Type': 'application/json' } }
      );

      if (loginRes.status === 200) {
        const token = JSON.parse(loginRes.body).access_token;
        tokens.push(token);
      }
    }
  });

  console.log(`Setup complete. Created ${tokens.length} test users.`);
  return { tokens };
}

/**
 * Main test function - runs for each virtual user
 */
export default function(data) {
  // Get a random token for this user
  const token = data.tokens[Math.floor(Math.random() * data.tokens.length)];
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };

  // Test 1: Health Check (should be fast)
  group('Health Checks', () => {
    const healthRes = http.get(`${BASE_URL}${API_VERSION}/health`);

    check(healthRes, {
      'health check status 200': (r) => r.status === 200,
      'health check duration < 100ms': (r) => r.timings.duration < 100,
    }) || errorRate.add(1);

    requestCounter.add(1);
    apiLatency.add(healthRes.timings.duration);
  });

  sleep(1);

  // Test 2: List Employees (common read operation)
  group('List Employees', () => {
    const page = Math.floor(Math.random() * 10) + 1;
    const listRes = http.get(
      `${BASE_URL}${API_VERSION}/employees?page=${page}&page_size=20`,
      { headers }
    );

    check(listRes, {
      'list employees status 200': (r) => r.status === 200,
      'list employees has data': (r) => JSON.parse(r.body).items.length > 0,
      'list employees duration < 200ms': (r) => r.timings.duration < 200,
    }) || errorRate.add(1);

    requestCounter.add(1);
    apiLatency.add(listRes.timings.duration);

    // Check for cache hits (second request should be faster)
    sleep(0.5);
    const cachedRes = http.get(
      `${BASE_URL}${API_VERSION}/employees?page=${page}&page_size=20`,
      { headers }
    );

    if (cachedRes.timings.duration < listRes.timings.duration) {
      cacheHitRate.add(1);
    } else {
      cacheHitRate.add(0);
    }
  });

  sleep(1);

  // Test 3: Get Employee by ID (cached read)
  group('Get Employee', () => {
    const empNo = 10001 + Math.floor(Math.random() * 1000);
    const getRes = http.get(
      `${BASE_URL}${API_VERSION}/employees/${empNo}`,
      { headers }
    );

    check(getRes, {
      'get employee status is valid': (r) => [200, 404].includes(r.status),
      'get employee duration < 100ms': (r) => r.timings.duration < 100,
    }) || errorRate.add(1);

    requestCounter.add(1);
    apiLatency.add(getRes.timings.duration);
  });

  sleep(1);

  // Test 4: List Departments
  group('List Departments', () => {
    const deptRes = http.get(
      `${BASE_URL}${API_VERSION}/departments`,
      { headers }
    );

    check(deptRes, {
      'list departments status 200': (r) => r.status === 200,
      'list departments has data': (r) => JSON.parse(r.body).items.length > 0,
    }) || errorRate.add(1);

    requestCounter.add(1);
    apiLatency.add(deptRes.timings.duration);
  });

  sleep(1);

  // Test 5: Get Analytics (complex query)
  group('Analytics Queries', () => {
    const analyticsEndpoints = [
      '/analytics/salary-statistics',
      '/analytics/department-performance',
      '/analytics/gender-diversity',
      '/analytics/summary'
    ];

    const endpoint = analyticsEndpoints[Math.floor(Math.random() * analyticsEndpoints.length)];
    const analyticsRes = http.get(
      `${BASE_URL}${API_VERSION}${endpoint}`,
      { headers }
    );

    check(analyticsRes, {
      'analytics status 200': (r) => r.status === 200,
      'analytics has data': (r) => Object.keys(JSON.parse(r.body)).length > 0,
      'analytics duration < 500ms': (r) => r.timings.duration < 500,
    }) || errorRate.add(1);

    requestCounter.add(1);
    apiLatency.add(analyticsRes.timings.duration);
  });

  sleep(2);

  // Test 6: Create Employee (write operation - less frequent)
  if (Math.random() < 0.1) {  // Only 10% of users create
    group('Create Employee', () => {
      const newEmployee = JSON.stringify({
        first_name: `LoadTest${Math.floor(Math.random() * 10000)}`,
        last_name: 'User',
        birth_date: '1990-01-01',
        gender: Math.random() > 0.5 ? 'M' : 'F',
        hire_date: '2024-01-01',
        email: `loadtest${Math.floor(Math.random() * 100000)}@test.com`
      });

      const createRes = http.post(
        `${BASE_URL}${API_VERSION}/employees`,
        newEmployee,
        { headers }
      );

      check(createRes, {
        'create employee status is valid': (r) => [200, 201, 409].includes(r.status),
        'create employee duration < 300ms': (r) => r.timings.duration < 300,
      }) || errorRate.add(1);

      requestCounter.add(1);
      apiLatency.add(createRes.timings.duration);
    });
  }

  sleep(1);

  // Test 7: Search Employees
  group('Search Employees', () => {
    const searchTerms = ['john', 'mary', 'tech', 'sales'];
    const searchTerm = searchTerms[Math.floor(Math.random() * searchTerms.length)];

    const searchRes = http.get(
      `${BASE_URL}${API_VERSION}/employees?search=${searchTerm}`,
      { headers }
    );

    check(searchRes, {
      'search status 200': (r) => r.status === 200,
      'search duration < 300ms': (r) => r.timings.duration < 300,
    }) || errorRate.add(1);

    requestCounter.add(1);
    apiLatency.add(searchRes.timings.duration);
  });

  sleep(2);
}

/**
 * Teardown function - runs once after all iterations
 */
export function teardown(data) {
  console.log('Load test completed');
  console.log(`Total tokens created: ${data.tokens.length}`);
}

/**
 * Handle summary - runs at the end to generate custom summary
 */
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
    'summary.html': htmlReport(data),
  };
}

function textSummary(data, opts) {
  const indent = opts.indent || '';
  const enableColors = opts.enableColors || false;

  let summary = `\n${indent}Load Test Summary\n`;
  summary += `${indent}================\n\n`;

  summary += `${indent}Test Duration: ${data.state.testRunDurationMs / 1000}s\n`;
  summary += `${indent}Virtual Users: ${data.metrics.vus.values.max}\n\n`;

  summary += `${indent}HTTP Metrics:\n`;
  summary += `${indent}  Requests:        ${data.metrics.http_reqs.values.count}\n`;
  summary += `${indent}  Request Rate:    ${data.metrics.http_reqs.values.rate.toFixed(2)} req/s\n`;
  summary += `${indent}  Failed Requests: ${data.metrics.http_req_failed.values.passes} (${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%)\n\n`;

  summary += `${indent}Response Times:\n`;
  summary += `${indent}  Min:     ${data.metrics.http_req_duration.values.min.toFixed(2)}ms\n`;
  summary += `${indent}  Avg:     ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
  summary += `${indent}  Median:  ${data.metrics.http_req_duration.values.med.toFixed(2)}ms\n`;
  summary += `${indent}  p(90):   ${data.metrics.http_req_duration.values['p(90)'].toFixed(2)}ms\n`;
  summary += `${indent}  p(95):   ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += `${indent}  p(99):   ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n`;
  summary += `${indent}  Max:     ${data.metrics.http_req_duration.values.max.toFixed(2)}ms\n\n`;

  summary += `${indent}Custom Metrics:\n`;
  summary += `${indent}  Error Rate:       ${(data.metrics.errors.values.rate * 100).toFixed(2)}%\n`;
  summary += `${indent}  Auth Success:     ${(data.metrics.auth_success.values.rate * 100).toFixed(2)}%\n`;
  summary += `${indent}  Cache Hit Rate:   ${(data.metrics.cache_hits.values.rate * 100).toFixed(2)}%\n`;

  return summary;
}

function htmlReport(data) {
  return `
<!DOCTYPE html>
<html>
<head>
  <title>Load Test Results</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    h1 { color: #333; }
    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background-color: #4CAF50; color: white; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    .metric-box { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .pass { color: green; font-weight: bold; }
    .fail { color: red; font-weight: bold; }
  </style>
</head>
<body>
  <h1>Load Test Results - Employee Management System</h1>
  <div class="metric-box">
    <h2>Test Configuration</h2>
    <p>Duration: ${data.state.testRunDurationMs / 1000}s</p>
    <p>Max Virtual Users: ${data.metrics.vus.values.max}</p>
  </div>

  <div class="metric-box">
    <h2>Performance Summary</h2>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Total Requests</td><td>${data.metrics.http_reqs.values.count}</td></tr>
      <tr><td>Request Rate</td><td>${data.metrics.http_reqs.values.rate.toFixed(2)} req/s</td></tr>
      <tr><td>Failed Requests</td><td>${data.metrics.http_req_failed.values.passes} (${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%)</td></tr>
      <tr><td>Avg Response Time</td><td>${data.metrics.http_req_duration.values.avg.toFixed(2)}ms</td></tr>
      <tr><td>p95 Response Time</td><td>${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms</td></tr>
      <tr><td>p99 Response Time</td><td>${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms</td></tr>
    </table>
  </div>

  <p>Generated: ${new Date().toISOString()}</p>
</body>
</html>
  `;
}
