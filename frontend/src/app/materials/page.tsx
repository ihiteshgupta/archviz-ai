'use client';

import { useState, useEffect } from 'react';
import { getMaterialLibrary, getCategories } from '@/lib/api';
import type { Material } from '@/types';
import { cn } from '@/lib/utils';

export default function MaterialsPage() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [categories, setCategories] = useState<{ id: string; name: string }[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [materialsData, categoriesData] = await Promise.all([
          getMaterialLibrary(),
          getCategories(),
        ]);
        setMaterials(materialsData.materials);
        setCategories(categoriesData.categories);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load materials');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const filteredMaterials = selectedCategory
    ? materials.filter((m) => m.category === selectedCategory)
    : materials;

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="card text-center py-12">
          <p className="text-red-600 mb-4">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Material Library</h1>
        <p className="text-gray-500 mt-1">
          Browse and select materials for your architectural renders
        </p>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2 mb-8">
        <button
          onClick={() => setSelectedCategory(null)}
          className={cn(
            'px-4 py-2 rounded-full text-sm font-medium transition-colors',
            selectedCategory === null
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          )}
        >
          All
        </button>
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.id)}
            className={cn(
              'px-4 py-2 rounded-full text-sm font-medium transition-colors',
              selectedCategory === category.id
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
          >
            {category.name}
          </button>
        ))}
      </div>

      {/* Materials Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredMaterials.map((material) => (
          <div
            key={material.id}
            className="card hover:shadow-md transition-shadow cursor-pointer"
          >
            {/* Color Preview */}
            <div
              className="w-full h-24 rounded-lg mb-4"
              style={{ backgroundColor: material.color_hex }}
            />

            {/* Material Info */}
            <div>
              <h3 className="font-semibold text-gray-900">{material.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{material.description}</p>

              <div className="flex flex-wrap gap-1 mt-3">
                {material.style_tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2 mt-4 text-xs text-gray-500">
                <div>
                  <span className="text-gray-400">Roughness:</span>{' '}
                  {material.roughness.toFixed(2)}
                </div>
                <div>
                  <span className="text-gray-400">Metallic:</span>{' '}
                  {material.metallic.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
