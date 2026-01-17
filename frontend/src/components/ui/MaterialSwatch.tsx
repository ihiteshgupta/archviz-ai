'use client';

import { forwardRef, useState } from 'react';
import { Check } from 'lucide-react';

interface Material {
  id: string;
  name: string;
  category: string;
  color?: string;
  texture_url?: string;
  preview_url?: string;
}

interface MaterialSwatchProps {
  material: Material;
  selected?: boolean;
  size?: 'sm' | 'md' | 'lg';
  onClick?: (material: Material) => void;
}

const MaterialSwatch = forwardRef<HTMLButtonElement, MaterialSwatchProps>(
  ({ material, selected = false, size = 'md', onClick }, ref) => {
    const [imageError, setImageError] = useState(false);

    const sizeStyles = {
      sm: 'w-10 h-10',
      md: 'w-12 h-12',
      lg: 'w-16 h-16',
    };

    const checkSizeStyles = {
      sm: 'w-3 h-3',
      md: 'w-4 h-4',
      lg: 'w-5 h-5',
    };

    const previewUrl = material.preview_url || material.texture_url;
    const showImage = previewUrl && !imageError;

    return (
      <button
        ref={ref}
        type="button"
        onClick={() => onClick?.(material)}
        className={`
          ${sizeStyles[size]}
          relative rounded-lg overflow-hidden
          border-2 transition-all
          ${selected ? 'border-primary ring-2 ring-primary-100' : 'border-transparent hover:border-border-hover'}
          hover:scale-105 focus:outline-none focus:ring-2 focus:ring-primary-100
        `}
        title={material.name}
      >
        {showImage ? (
          <img
            src={previewUrl}
            alt={material.name}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div
            className="w-full h-full"
            style={{ backgroundColor: material.color || '#E5E7EB' }}
          />
        )}

        {selected && (
          <div className="absolute top-0.5 right-0.5 bg-primary rounded-full p-0.5">
            <Check className={`${checkSizeStyles[size]} text-white`} />
          </div>
        )}
      </button>
    );
  }
);

MaterialSwatch.displayName = 'MaterialSwatch';

interface MaterialSwatchGroupProps {
  materials: Material[];
  selectedId?: string;
  onSelect?: (material: Material) => void;
  size?: 'sm' | 'md' | 'lg';
  maxVisible?: number;
  label?: string;
}

const MaterialSwatchGroup = ({
  materials,
  selectedId,
  onSelect,
  size = 'md',
  maxVisible = 6,
  label,
}: MaterialSwatchGroupProps) => {
  const [showAll, setShowAll] = useState(false);

  const visibleMaterials = showAll ? materials : materials.slice(0, maxVisible);
  const hiddenCount = materials.length - maxVisible;

  return (
    <div>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}
      <div className="flex flex-wrap gap-2 items-center">
        {visibleMaterials.map((material) => (
          <MaterialSwatch
            key={material.id}
            material={material}
            selected={material.id === selectedId}
            size={size}
            onClick={onSelect}
          />
        ))}
        {!showAll && hiddenCount > 0 && (
          <button
            type="button"
            onClick={() => setShowAll(true)}
            className="text-sm text-primary hover:text-primary-700 font-medium"
          >
            +{hiddenCount} more
          </button>
        )}
        {showAll && hiddenCount > 0 && (
          <button
            type="button"
            onClick={() => setShowAll(false)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Show less
          </button>
        )}
      </div>
    </div>
  );
};

interface MaterialCategoryPickerProps {
  categories: {
    name: string;
    materials: Material[];
  }[];
  selectedIds: Record<string, string>;
  onSelect?: (category: string, material: Material) => void;
  size?: 'sm' | 'md' | 'lg';
}

const MaterialCategoryPicker = ({
  categories,
  selectedIds,
  onSelect,
  size = 'md',
}: MaterialCategoryPickerProps) => {
  return (
    <div className="space-y-4">
      {categories.map((category) => (
        <MaterialSwatchGroup
          key={category.name}
          label={category.name}
          materials={category.materials}
          selectedId={selectedIds[category.name]}
          onSelect={(material) => onSelect?.(category.name, material)}
          size={size}
        />
      ))}
    </div>
  );
};

export { MaterialSwatch, MaterialSwatchGroup, MaterialCategoryPicker };
export type { Material, MaterialSwatchProps, MaterialSwatchGroupProps, MaterialCategoryPickerProps };
