'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex-shrink-0 flex items-center">
            <h1 className="text-xl font-bold text-gray-900">音樂管理系統</h1>
          </div>
          <div className="hidden sm:flex sm:space-x-4 items-center">
            <Link
              href="/"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === '/'
                ? 'bg-gray-600 text-white'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              歌曲管理
            </Link>
            <Link
              href="/playlists"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === '/playlists'
                ? 'bg-gray-600 text-white'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              播放清單管理
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}