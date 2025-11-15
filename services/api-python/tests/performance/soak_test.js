/**
 * k6 Soak Testing Script
 *
 * Tests system stability over extended period
 * Run with: k6 run --duration 1h soak_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5m', target: 200 },     // Ramp up
    { duration: '50m', target: 200 },    // Stay at moderate load
    { duration: '5m', target: 0 },       // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'],
    'http_req_failed': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function() {
  // Simulate realistic user behavior
  const endpoints = [
    '/api/v1/health',
    '/api/v1/employees',
    '/api/v1/departments',
    '/api/v1/analytics/summary',
  ];

  endpoints.forEach(endpoint => {
    const res = http.get(`${BASE_URL}${endpoint}`);
    check(res, {
      'status is 200': (r) => r.status === 200,
    });
    sleep(2);
  });

  sleep(5);  // Think time between sessions
}
