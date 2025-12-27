import { Disc2, ListMinus, ListMusic, Music, ServerCrash, Settings2 } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();
  const pathname = location.pathname;

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="mx-auto px-4 py-3">
        <div className="flex gap-2 justify-between">
          <div className="flex-shrink-0 flex items-center">
            <Link to="/" className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-gray-900">音樂管理系統</h1>
            </Link>
          </div>
          <div className="flex items-center">
            <Link
              to="/"
              className={`flex px-4 py-2 gap-2 rounded-full text-sm font-medium transition-colors ${pathname === '/'
                ? 'bg-foreground text-background'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              <Disc2 className="w-5 h-5" />
              {pathname === '/' && '歌曲管理'}
            </Link>
            <Link
              to="/playlists"
              className={`flex px-4 py-2 gap-2 rounded-full text-sm font-medium transition-colors ${pathname === '/playlists'
                ? 'bg-foreground text-background'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              <ListMusic className="w-5 h-5" />
              {pathname === '/playlists' && '播放清單'}
            </Link>
            <Link
              to="/cache"
              className={`flex px-4 py-2 gap-2 rounded-full text-sm font-medium transition-colors ${pathname === '/cache'
                ? 'bg-foreground text-background'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              <ServerCrash className="w-5 h-5" />
              {pathname === '/cache' && '快取管理'}
            </Link>
            <Link
              to="/settings"
              className={`flex px-4 py-2 gap-2 rounded-full text-sm font-medium transition-colors ${pathname === '/settings'
                ? 'bg-foreground text-background'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                }`}
            >
              <Settings2 className="w-5 h-5" />
              {pathname === '/settings' && '系統設定'}
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}