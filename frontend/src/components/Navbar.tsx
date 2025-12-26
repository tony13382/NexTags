import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();
  const pathname = location.pathname;

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex-shrink-0 flex items-center">
            <h1 className="text-xl font-bold text-gray-900">音樂管理系統</h1>
          </div>
          <div className="hidden sm:flex sm:space-x-4 items-center">
            <Link
              to="/"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === '/'
                ? 'bg-gray-600 text-white'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              歌曲管理
            </Link>
            <Link
              to="/playlists"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === '/playlists'
                ? 'bg-gray-600 text-white'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              播放清單管理
            </Link>
            <Link
              to="/cache"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === '/cache'
                ? 'bg-gray-600 text-white'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              快取管理
            </Link>
            <Link
              to="/settings"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === '/settings'
                ? 'bg-gray-600 text-white'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              系統設定
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}