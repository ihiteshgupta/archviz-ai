'use client';

import NotificationBell from './NotificationBell';

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg
            className="w-8 h-8 text-primary-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
          <a href="/" className="text-xl font-bold text-gray-900">
            ArchViz AI
          </a>
        </div>
        <nav className="flex items-center gap-6">
          <a href="/" className="text-gray-600 hover:text-gray-900">
            Projects
          </a>
          <a href="/materials" className="text-gray-600 hover:text-gray-900">
            Materials
          </a>
          <a href="/settings" className="text-gray-600 hover:text-gray-900">
            Settings
          </a>
          <NotificationBell />
        </nav>
      </div>
    </header>
  );
}
