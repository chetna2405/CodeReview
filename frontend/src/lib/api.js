/**
 * API client for CodeReviewEnv backend.
 * Uses window.location.origin so it works on both localhost and HF Spaces.
 */

const API_BASE = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000';

async function request(url, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${url}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      const msg = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
      throw new Error(msg || `HTTP ${res.status}`);
    }
    return res.json();
  } catch (err) {
    console.error(`API Error [${url}]:`, err.message);
    throw err;
  }
}

export const api = {
  // Tasks
  getTasks: () => request('/tasks'),

  // Episodes
  resetEpisode: (body) =>
    request('/api/reset', { method: 'POST', body: JSON.stringify(body) }),
  step: (body) =>
    request('/api/step', { method: 'POST', body: JSON.stringify(body) }),
  getState: (episodeId) => request(`/api/state?episode_id=${episodeId}`),
  getContext: (params) =>
    request(`/api/context?${new URLSearchParams(params)}`),

  // Replay (B3)
  getReplay: (episodeId) => request(`/api/replay/${episodeId}`),

  // Grading & Leaderboard
  getGrader: (episodeId) => request(`/grader?episode_id=${episodeId}`),
  getLeaderboard: () => request('/leaderboard'),
  runBaseline: (body) =>
    request('/baseline', { method: 'POST', body: JSON.stringify(body) }),

  // Health
  health: () => request('/api/health'),
};
