/**
 * k6 Stress Testing Script
 *
 * Tests system behavior under extreme load to find breaking point
 * Run with: k6 run stress_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '2m', target: 100 },    // Warm up
    { duration: '5m', target: 100 },    // Baseline
    { duration: '2m', target: 500 },    // Spike to 500
    { duration: '5m', target: 500 },    // Hold at 500
    { duration: '2m', target: 1000 },   // Spike to 1000
    { duration: '5m', target: 1000 },   // Hold at 1000
    { duration: '2m', target: 2000 },   // Spike to 2000 (breaking point)
    { duration: '5m', target: 2000 },   // Hold at 2000
    { duration: '5m', target: 0 },      // Recovery
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1000'],  // Relaxed threshold for stress test
    'errors': ['rate<0.1'],               // Allow 10% error rate
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function() {
  const res = http.get(`${BASE_URL}/api/v1/health`);

  check(res, {
    'status is 200': (r) => r.status === 200,
  }) || errorRate.add(1);

  sleep(1);
}
