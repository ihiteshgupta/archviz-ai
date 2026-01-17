import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Header from '@/components/Header';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'ArchViz AI - AI-Powered Architectural Visualization',
  description: 'Transform DWG files into stunning photorealistic renders with AI',
  manifest: '/manifest.json',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen flex flex-col">
          <Header />
          <main className="flex-1">{children}</main>
          <footer className="bg-white border-t border-gray-200 py-4">
            <div className="max-w-7xl mx-auto px-4 text-center text-gray-500 text-sm">
              ArchViz AI - AI-Powered Architectural Visualization
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
