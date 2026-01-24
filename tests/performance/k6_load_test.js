/**
 * k6 Load Test Script for ArchViz AI
 *
 * Usage:
 *   k6 run tests/performance/k6_load_test.js
 *
 *   With environment variables:
 *   k6 run -e API_URL=http://localhost:8000 tests/performance/k6_load_test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const projectListTrend = new Trend('project_list_duration');
const projectCreateTrend = new Trend('project_create_duration');
const renderCreateTrend = new Trend('render_create_duration');
const materialsFetchTrend = new Trend('materials_fetch_duration');
const projectsCreated = new Counter('projects_created');
const rendersCreated = new Counter('renders_created');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 20 },   // Ramp up to 20 users
    { duration: '3m', target: 20 },   // Stay at 20 users
    { duration: '1m', target: 50 },   // Ramp to 50 users
    { duration: '3m', target: 50 },   // Stay at 50 users
    { duration: '1m', target: 100 },  // Ramp to 100 users
    { duration: '3m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.1'],
    'project_list_duration': ['p(95)<300'],
    'project_create_duration': ['p(95)<500'],
    'materials_fetch_duration': ['p(95)<200'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

// Render styles available
const RENDER_STYLES = [
  'modern_minimalist',
  'scandinavian',
  'industrial',
  'traditional',
  'mediterranean',
  'japanese_zen',
  'art_deco'
];

// Helper function to get random style
function getRandomStyle() {
  return RENDER_STYLES[Math.floor(Math.random() * RENDER_STYLES.length)];
}

export default function () {
  let projectId = null;

  group('Health Check', function () {
    const res = http.get(`${BASE_URL}/api/health`);
    check(res, {
      'health status 200': (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  group('Project Operations', function () {
    // List projects
    let listRes = http.get(`${BASE_URL}/api/projects/`);
    projectListTrend.add(listRes.timings.duration);
    check(listRes, {
      'list status 200': (r) => r.status === 200,
      'list response time OK': (r) => r.timings.duration < 500,
      'list returns array': (r) => Array.isArray(JSON.parse(r.body)),
    }) || errorRate.add(1);

    sleep(0.5);

    // Create project
    let createRes = http.post(
      `${BASE_URL}/api/projects/`,
      JSON.stringify({
        name: `k6-test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        description: 'Load test project'
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    projectCreateTrend.add(createRes.timings.duration);

    const createSuccess = check(createRes, {
      'create status 200': (r) => r.status === 200,
      'create returns id': (r) => JSON.parse(r.body).id !== undefined,
    });

    if (!createSuccess) {
      errorRate.add(1);
    } else {
      projectsCreated.add(1);
      projectId = JSON.parse(createRes.body).id;
    }

    sleep(0.5);

    // Get project
    if (projectId) {
      let getRes = http.get(`${BASE_URL}/api/projects/${projectId}`);
      check(getRes, {
        'get status 200': (r) => r.status === 200,
        'get returns correct id': (r) => JSON.parse(r.body).id === projectId,
      }) || errorRate.add(1);
    }
  });

  sleep(1);

  group('Materials API', function () {
    // Get material library
    let matRes = http.get(`${BASE_URL}/api/materials/library`);
    materialsFetchTrend.add(matRes.timings.duration);
    check(matRes, {
      'materials status 200': (r) => r.status === 200,
      'materials has list': (r) => JSON.parse(r.body).materials !== undefined,
    }) || errorRate.add(1);

    sleep(0.3);

    // Get categories
    let catRes = http.get(`${BASE_URL}/api/materials/categories`);
    check(catRes, {
      'categories status 200': (r) => r.status === 200,
    }) || errorRate.add(1);

    sleep(0.3);

    // Get presets
    let presetRes = http.get(`${BASE_URL}/api/materials/presets`);
    check(presetRes, {
      'presets status 200': (r) => r.status === 200,
      'presets has list': (r) => JSON.parse(r.body).presets !== undefined,
    }) || errorRate.add(1);
  });

  sleep(1);

  group('Render Operations', function () {
    // Get render styles
    let stylesRes = http.get(`${BASE_URL}/api/render/styles`);
    check(stylesRes, {
      'styles status 200': (r) => r.status === 200,
      'styles has list': (r) => JSON.parse(r.body).styles !== undefined,
    }) || errorRate.add(1);

    sleep(0.5);

    // Create render job (if we have a project)
    if (projectId) {
      let renderRes = http.post(
        `${BASE_URL}/api/render/`,
        JSON.stringify({
          project_id: projectId,
          style: getRandomStyle(),
          resolution: 1024
        }),
        { headers: { 'Content-Type': 'application/json' } }
      );
      renderCreateTrend.add(renderRes.timings.duration);

      const renderSuccess = check(renderRes, {
        'render create status 200': (r) => r.status === 200,
        'render returns job id': (r) => JSON.parse(r.body).id !== undefined,
      });

      if (!renderSuccess) {
        errorRate.add(1);
      } else {
        rendersCreated.add(1);

        const jobId = JSON.parse(renderRes.body).id;

        // Check render status
        sleep(0.5);
        let statusRes = http.get(`${BASE_URL}/api/render/${jobId}`);
        check(statusRes, {
          'render status check 200': (r) => r.status === 200,
        }) || errorRate.add(1);
      }
    }

    sleep(0.5);

    // Get project renders
    if (projectId) {
      let projRenderRes = http.get(`${BASE_URL}/api/render/project/${projectId}`);
      check(projRenderRes, {
        'project renders status 200': (r) => r.status === 200,
        'project renders is array': (r) => Array.isArray(JSON.parse(r.body)),
      }) || errorRate.add(1);
    }

    // Pipeline status
    let pipelineRes = http.get(`${BASE_URL}/api/render/pipeline/status`);
    check(pipelineRes, {
      'pipeline status 200': (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  sleep(1);

  group('Chat Status', function () {
    let chatStatusRes = http.get(`${BASE_URL}/api/chat/status`);
    check(chatStatusRes, {
      'chat status 200': (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  // Cleanup - delete project
  if (projectId) {
    let deleteRes = http.del(`${BASE_URL}/api/projects/${projectId}`);
    check(deleteRes, {
      'delete status 200': (r) => r.status === 200,
    }); // Don't count delete failures as errors
  }

  sleep(2);
}

// Separate scenario for stress testing
export function stressTest() {
  // Quick burst of requests
  for (let i = 0; i < 10; i++) {
    http.get(`${BASE_URL}/api/projects/`);
    http.get(`${BASE_URL}/api/materials/library`);
    http.get(`${BASE_URL}/api/render/styles`);
  }
}

// Scenario for soak testing
export function soakTest() {
  // Same as default but with longer think time
  http.get(`${BASE_URL}/api/projects/`);
  sleep(5);
  http.get(`${BASE_URL}/api/materials/library`);
  sleep(5);
}
