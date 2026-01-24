/**
 * Tests for the API client library
 */

import {
  createProject,
  listProjects,
  getProject,
  deleteProject,
  uploadFile,
  getMaterialLibrary,
  getCategories,
  getStylePresets,
  createRenderJob,
  getRenderJob,
  getRenderStyles,
} from '../api';

// Mock fetch
const mockFetch = global.fetch as jest.Mock;

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  describe('Projects API', () => {
    describe('createProject', () => {
      it('creates project successfully', async () => {
        const mockProject = {
          id: 'abc123',
          name: 'Test Project',
          description: 'Test description',
          status: 'created',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockProject,
        });

        const result = await createProject('Test Project', 'Test description');

        expect(mockFetch).toHaveBeenCalledWith('/api/projects/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: 'Test Project', description: 'Test description' }),
        });
        expect(result).toEqual(mockProject);
      });

      it('throws error on API failure', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => ({ detail: 'Internal server error' }),
        });

        await expect(createProject('Test')).rejects.toThrow('Internal server error');
      });

      it('handles network errors', async () => {
        mockFetch.mockRejectedValueOnce(new Error('Network error'));

        await expect(createProject('Test')).rejects.toThrow('Network error');
      });
    });

    describe('listProjects', () => {
      it('returns list of projects', async () => {
        const mockProjects = [
          { id: '1', name: 'Project 1', status: 'created' },
          { id: '2', name: 'Project 2', status: 'parsed' },
        ];

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockProjects,
        });

        const result = await listProjects();

        expect(mockFetch).toHaveBeenCalledWith('/api/projects/', {
          headers: { 'Content-Type': 'application/json' },
        });
        expect(result).toEqual(mockProjects);
        expect(result).toHaveLength(2);
      });

      it('returns empty array when no projects', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => [],
        });

        const result = await listProjects();

        expect(result).toEqual([]);
      });
    });

    describe('getProject', () => {
      it('returns project by id', async () => {
        const mockProject = {
          id: 'abc123',
          name: 'Test Project',
          status: 'parsed',
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockProject,
        });

        const result = await getProject('abc123');

        expect(mockFetch).toHaveBeenCalledWith('/api/projects/abc123', {
          headers: { 'Content-Type': 'application/json' },
        });
        expect(result).toEqual(mockProject);
      });

      it('throws on 404', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => ({ detail: 'Project not found' }),
        });

        await expect(getProject('nonexistent')).rejects.toThrow('Project not found');
      });
    });

    describe('deleteProject', () => {
      it('deletes project successfully', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'deleted', id: 'abc123' }),
        });

        await expect(deleteProject('abc123')).resolves.not.toThrow();

        expect(mockFetch).toHaveBeenCalledWith('/api/projects/abc123', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
        });
      });
    });

    describe('uploadFile', () => {
      it('uploads file with FormData', async () => {
        const mockResponse = {
          status: 'success',
          project_id: 'abc123',
          file_name: 'test.dxf',
          floor_plan: { rooms: [], walls: [] },
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        });

        const file = new File(['content'], 'test.dxf', { type: 'application/octet-stream' });
        const result = await uploadFile('abc123', file);

        expect(mockFetch).toHaveBeenCalledWith('/api/projects/abc123/upload', {
          method: 'POST',
          body: expect.any(FormData),
        });
        expect(result).toEqual(mockResponse);
      });

      it('throws on upload failure', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 400,
          json: async () => ({ detail: 'Invalid file type' }),
        });

        const file = new File(['content'], 'test.pdf');
        await expect(uploadFile('abc123', file)).rejects.toThrow('Invalid file type');
      });
    });
  });

  describe('Materials API', () => {
    describe('getMaterialLibrary', () => {
      it('returns materials', async () => {
        const mockMaterials = {
          materials: [
            { id: 'wood-oak', name: 'Oak', category: 'wood' },
            { id: 'marble-white', name: 'White Marble', category: 'stone' },
          ],
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockMaterials,
        });

        const result = await getMaterialLibrary();

        expect(result.materials).toHaveLength(2);
      });
    });

    describe('getCategories', () => {
      it('returns categories', async () => {
        const mockCategories = {
          categories: [
            { id: 'wood', name: 'Wood' },
            { id: 'stone', name: 'Stone' },
          ],
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockCategories,
        });

        const result = await getCategories();

        expect(result.categories).toHaveLength(2);
      });
    });

    describe('getStylePresets', () => {
      it('returns style presets', async () => {
        const mockPresets = {
          presets: [
            { id: 'modern', name: 'Modern', materials: {} },
            { id: 'scandinavian', name: 'Scandinavian', materials: {} },
          ],
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockPresets,
        });

        const result = await getStylePresets();

        expect(result.presets).toHaveLength(2);
      });
    });
  });

  describe('Render API', () => {
    describe('createRenderJob', () => {
      it('creates render job', async () => {
        const mockJob = {
          id: 'job123',
          project_id: 'abc123',
          style: 'modern_minimalist',
          status: 'pending',
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockJob,
        });

        const result = await createRenderJob({
          project_id: 'abc123',
          style: 'modern_minimalist',
        });

        expect(result).toEqual(mockJob);
      });
    });

    describe('getRenderJob', () => {
      it('returns render job status', async () => {
        const mockJob = {
          id: 'job123',
          status: 'completed',
          renders: [{ url: 'http://example.com/render.png' }],
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockJob,
        });

        const result = await getRenderJob('job123');

        expect(result.status).toBe('completed');
      });
    });

    describe('getRenderStyles', () => {
      it('returns available styles', async () => {
        const mockStyles = {
          styles: [
            { id: 'modern_minimalist', name: 'Modern Minimalist' },
            { id: 'scandinavian', name: 'Scandinavian' },
          ],
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockStyles,
        });

        const result = await getRenderStyles();

        expect(result.styles.length).toBeGreaterThan(0);
      });
    });
  });
});
