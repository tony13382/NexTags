'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Music, Heart, Edit } from 'lucide-react';
import TagEditor from '@/components/TagEditor';

interface Song {
  Title: string;
  Artist: string;
  Album: string;
  MainFolder: string;
  FilePath: string;
  Genre: string[];
  Language: string;
  Favorite: string;
  Cover: string;
  SortTitle?: string;
  SortArtist?: string;
  SortAlbum?: string;
  Lyrics?: string;
  Comment?: string;
  JfId?: string;
  JellyfinAddTime?: string;
}

interface ApiResponse {
  audio_files: Song[];
  pagination: {
    current_page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
    has_previous: boolean;
    has_next: boolean;
  };
  allow_folders: string[];
}

export default function Home() {
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTitle, setSearchTitle] = useState('');
  const [selectedFolder, setSelectedFolder] = useState('');
  const [showFavorites, setShowFavorites] = useState(false);
  const [allowFolders, setAllowFolders] = useState<string[]>([]);
  const [pagination, setPagination] = useState({
    current_page: 1,
    total_pages: 1,
    total_count: 0
  });
  const [editingSong, setEditingSong] = useState<Song | null>(null);

  const fetchSongs = async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        p: page.toString(),
        details: 'true'
      });

      if (searchTitle) params.append('filterTitle', searchTitle);
      if (selectedFolder) params.append('filterFolder', selectedFolder);
      if (showFavorites) params.append('filterFavorite', 'true');

      const response = await fetch(`/api/audios/?${params}`);
      const data: ApiResponse = await response.json();

      setSongs(data.audio_files);
      setAllowFolders(data.allow_folders);
      setPagination({
        current_page: data.pagination.current_page,
        total_pages: data.pagination.total_pages,
        total_count: data.pagination.total_count
      });
    } catch (error) {
      console.error('Failed to fetch songs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSongs();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => {
    fetchSongs(1);
  };

  const handlePageChange = (page: number) => {
    fetchSongs(page);
  };

  const handleSaveTags = async (song: Song) => {
    try {
      const response = await fetch('/api/audios/update', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: song.FilePath,
          tags: [{
            title: song.Title,
            artist: song.Artist,
            album: song.Album,
            titlesort: song.SortTitle,
            artistsort: song.SortArtist,
            albumsort: song.SortAlbum,
            genre: song.Genre, // 保持陣列格式
            language: song.Language,
            favorite: song.Favorite,
            lyrics: song.Lyrics || '',
            comment: song.Comment || '',
            jfid: song.JfId || '',
            jellyfin_add_time: song.JellyfinAddTime || ''
          }]
        })
      });

      if (response.ok) {
        // 重新載入歌曲清單
        fetchSongs(pagination.current_page);
        setEditingSong(null);
      } else {
        console.error('Failed to save tags');
      }
    } catch (error) {
      console.error('Error saving tags:', error);
    }
  };

  return (
    <div className="mx-auto px-8 py-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mt-4 mb-6 flex items-center gap-2">
          歌曲管理
        </h1>

        {/* 搜尋和篩選區域 */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              搜尋和篩選
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="md:col-span-2">
                <Input
                  placeholder="搜尋歌曲標題..."
                  value={searchTitle}
                  onChange={(e) => setSearchTitle(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                />
              </div>
              <select
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={selectedFolder}
                onChange={(e) => setSelectedFolder(e.target.value)}
              >
                <option value="">所有資料夾</option>
                {allowFolders.map(folder => (
                  <option key={folder} value={folder}>{folder}</option>
                ))}
              </select>
              <Button
                variant={showFavorites ? 'default' : 'outline'}
                onClick={() => {
                  setShowFavorites(!showFavorites);
                  setTimeout(() => fetchSongs(1), 100);
                }}
                className="flex items-center gap-2"
              >
                <Heart className={`h-4 w-4 ${showFavorites ? 'fill-current' : ''}`} />
                {showFavorites ? '顯示全部' : '只顯示最愛'}
              </Button>
              <Button onClick={handleSearch} className="flex items-center gap-2">
                <Search className="h-4 w-4" />
                搜尋
              </Button>
            </div>
            <div className="mt-4 flex items-center gap-4">
              {/* 統計資訊 */}
              <div className="text-sm text-gray-600">
                共找到 {pagination.total_count} 首歌曲，第 {pagination.current_page} 頁 / 共 {pagination.total_pages} 頁
              </div>
            </div>
          </CardContent>
        </Card>


      </div>

      {/* 歌曲清單 */}
      {loading ? (
        <div className="text-center py-8">載入中...</div>
      ) : (
        <>
          <div className="bg-white rounded-2xl border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-center font-medium text-gray-500 tracking-wider">
                      封面
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      標題
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      藝術家
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      專輯
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      資料夾
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      流派
                    </th>
                    <th className="px-4 py-3 text-center text-nowrap font-medium text-gray-500 tracking-wider max-w-[80px] min-w-[40px]">
                      語言
                    </th>
                    <th className="px-4 py-3 text-center text-nowrap font-medium text-gray-500 tracking-wider max-w-[80px] min-w-[40px]">
                      最愛
                    </th>
                    <th className="px-4 py-3 text-center font-medium text-gray-500 tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {songs.map((song, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="h-12 w-12 mx-auto bg-gray-200 rounded flex items-center justify-center overflow-hidden">
                          {song.Cover ? (
                            <img
                              src={`/api/images/cover?path=${encodeURIComponent(song.Cover)}`}
                              alt={`${song.Title} 封面`}
                              className="h-full w-full object-cover rounded"
                              onError={(e) => {
                                // 當圖片載入失敗時，顯示預設音樂圖標
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                                const parent = target.parentElement;
                                if (parent && !parent.querySelector('.fallback-icon')) {
                                  const musicIcon = document.createElement('div');
                                  musicIcon.className = 'fallback-icon flex items-center justify-center h-full w-full';
                                  musicIcon.innerHTML = '<svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"></path></svg>';
                                  parent.appendChild(musicIcon);
                                }
                              }}
                            />
                          ) : (
                            <Music className="h-4 w-4 text-gray-400" />
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[200px] min-w-[100px]">
                        <div className="font-medium text-gray-900 truncate">
                          {song.Title || '未知標題'}
                        </div>
                        <div className="text-sm text-gray-600 truncate">
                          {song.SortTitle || '未知標題'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[200px] min-w-[100px]">
                        <div className="font-medium text-gray-900 truncate">
                          {song.Artist || '未知藝術家'}
                        </div>
                        <div className="text-sm text-gray-600 truncate">
                          {song.SortArtist || '未知藝術家'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[200px] min-w-[100px]">
                        <div className="font-medium text-gray-900 truncate">
                          {song.Album || '未知專輯'}
                        </div>
                        <div className="text-sm text-gray-600 truncate">
                          {song.SortAlbum || '未知專輯'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[200px] min-w-[100px]">
                        <div className="font-medium text-gray-900 truncate">
                          <span className="inline-block px-2 py-1 mb-2 text-sm bg-gray-500 text-white rounded">
                            {song.MainFolder}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 truncate">
                          {song.FilePath || '未知路徑'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[320px] min-w-[200px]">
                        <div className="text-sm flex flex-wrap gap-2 w-full">
                          {song.Genre.length > 0 ? (
                            song.Genre.map((genre, index) => (
                              <span key={index} className="inline-block px-2 py-1 text-sm bg-gray-100 text-gray-900 rounded">
                                {genre}
                              </span>
                            ))
                          ) : (
                            <span className="text-gray-600">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center max-w-[80px] min-w-[40px]">
                        <div className="text-sm text-gray-900 max-w-[100px] min-w-[40px]">
                          {song.Language || '-'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[80px] min-w-[40px]">
                        {song.Favorite === 'True' ? (
                          <Heart className="h-4 w-4 text-red-500 fill-current mx-auto" />
                        ) : (
                          <div className="h-4 w-4 mx-auto"></div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex items-center gap-1 mx-auto"
                          onClick={() => setEditingSong(song)}
                        >
                          <Edit className="h-3 w-3" />
                          編輯
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 分頁 */}
          {pagination.total_pages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-8">
              <Button
                variant="outline"
                disabled={pagination.current_page === 1}
                onClick={() => handlePageChange(pagination.current_page - 1)}
              >
                上一頁
              </Button>
              <span className="px-4 py-2 text-sm text-gray-600">
                {pagination.current_page} / {pagination.total_pages}
              </span>
              <Button
                variant="outline"
                disabled={pagination.current_page === pagination.total_pages}
                onClick={() => handlePageChange(pagination.current_page + 1)}
              >
                下一頁
              </Button>
            </div>
          )}
        </>
      )}

      <TagEditor
        song={editingSong}
        onClose={() => setEditingSong(null)}
        onSave={handleSaveTags}
      />
    </div>
  );
}
