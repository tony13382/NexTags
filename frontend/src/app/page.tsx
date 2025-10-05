'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Heart, Edit, Plus, Volume2 } from 'lucide-react';
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
  SortAlbumArtist?: string;
  SortComposer?: string;
  AlbumArtist?: string;
  Composer?: string;
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
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [showFavorites, setShowFavorites] = useState(false);
  const [allowFolders, setAllowFolders] = useState<string[]>([]);
  const [availableLanguages, setAvailableLanguages] = useState<string[]>([]);
  const [pagination, setPagination] = useState({
    current_page: 1,
    total_pages: 1,
    total_count: 0
  });
  const [editingSong, setEditingSong] = useState<Song | null>(null);
  const [generatingBatchReplayGain, setGeneratingBatchReplayGain] = useState(false);
  const [batchReplayGainStatus, setBatchReplayGainStatus] = useState<{
    is_running: boolean;
    total_files: number;
    processed_files: number;
    failed_files: number;
    current_file: string;
  } | null>(null);

  const fetchSongs = async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        p: page.toString(),
        details: 'true'
      });

      if (searchTitle) params.append('filterTitle', searchTitle);
      if (selectedFolder) params.append('filterFolder', selectedFolder);
      if (selectedLanguage) params.append('filterLanguage', selectedLanguage);
      if (showFavorites) params.append('filterFavorite', 'true');

      const response = await fetch(`/api/audios/?${params}`);
      const data: ApiResponse = await response.json();

      setSongs(data.audio_files);
      setAllowFolders(data.allow_folders);

      // Extract unique languages from all songs
      const languages = new Set<string>();
      data.audio_files.forEach((song: Song) => {
        if (song.Language && song.Language.trim()) {
          languages.add(song.Language.trim());
        }
      });
      setAvailableLanguages(Array.from(languages).sort());

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
            albumartist: song.AlbumArtist || '',
            composer: song.Composer || '',
            titlesort: song.SortTitle,
            artistsort: song.SortArtist,
            albumsort: song.SortAlbum,
            albumartistsort: song.SortAlbumArtist || '',
            composersort: song.SortComposer || '',
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

  const pollBatchReplayGainStatus = async () => {
    try {
      const response = await fetch('/api/audios/replaygain/batch/status');
      const data = await response.json();

      if (data.success && data.status) {
        setBatchReplayGainStatus(data.status);

        if (data.status.is_running) {
          // 繼續輪詢
          setTimeout(pollBatchReplayGainStatus, 2000); // 每 2 秒查詢一次
        } else {
          // 完成
          setGeneratingBatchReplayGain(false);
          if (data.status.total_files > 0) {
            alert(`批量生成完成！\n總計: ${data.status.total_files} 個檔案\n成功: ${data.status.processed_files} 個\n失敗: ${data.status.failed_files} 個`);
          }
        }
      }
    } catch (error) {
      console.error('Error polling status:', error);
    }
  };

  const handleBatchGenerateReplayGain = async () => {
    if (!confirm('確定要為所有歌曲生成 ReplayGain 嗎？這可能需要數小時。\n\n處理過程將在後台進行，您可以關閉此頁面，稍後再回來查看進度。')) {
      return;
    }

    try {
      setGeneratingBatchReplayGain(true);

      const response = await fetch('/api/audios/replaygain/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await response.json();

      if (data.success) {
        // 開始輪詢狀態
        pollBatchReplayGainStatus();
      } else {
        alert(`批量生成失敗: ${data.message}`);
        setGeneratingBatchReplayGain(false);
      }
    } catch (error) {
      console.error('Error generating batch ReplayGain:', error);
      alert('批量生成 ReplayGain 時發生錯誤');
      setGeneratingBatchReplayGain(false);
    }
  };

  return (
    <div className="mx-auto px-8 py-4">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 mt-4 mb-6 flex items-center gap-2">
            歌曲管理
          </h1>
          <div className="flex gap-2 mt-4 mb-6">
            <Button
              className="flex items-center gap-2"
              onClick={handleBatchGenerateReplayGain}
              disabled={generatingBatchReplayGain}
              variant="outline"
            >
              <Volume2 className="h-4 w-4" />
              {generatingBatchReplayGain ? '生成中...' : '生成 ReplayGain'}
            </Button>
            <Button
              className="flex items-center gap-2"
              onClick={() => window.location.href = '/new'}
            >
              <Plus className="h-4 w-4" />
              新增歌曲
            </Button>
          </div>

          {/* ReplayGain 進度顯示 */}
          {batchReplayGainStatus && batchReplayGainStatus.is_running && (
            <Card className="mb-6 bg-blue-50 border-blue-200">
              <CardContent className="pt-6">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">ReplayGain 生成進度</span>
                    <span>{batchReplayGainStatus.processed_files + batchReplayGainStatus.failed_files} / {batchReplayGainStatus.total_files}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                      style={{
                        width: `${((batchReplayGainStatus.processed_files + batchReplayGainStatus.failed_files) / batchReplayGainStatus.total_files) * 100}%`
                      }}
                    ></div>
                  </div>
                  <div className="text-xs text-gray-600">
                    <div>成功: {batchReplayGainStatus.processed_files} 個</div>
                    <div>失敗: {batchReplayGainStatus.failed_files} 個</div>
                    {batchReplayGainStatus.current_file && (
                      <div className="mt-1 truncate">目前處理: {batchReplayGainStatus.current_file.split('/').pop()}</div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* 搜尋和篩選區域 */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              搜尋和篩選
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
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
              <select
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
              >
                <option value="">所有語言</option>
                {availableLanguages.map(language => (
                  <option key={language} value={language}>{language}</option>
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
