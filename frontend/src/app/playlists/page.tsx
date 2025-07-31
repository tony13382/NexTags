'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Plus, ListMusic, RefreshCcw, Edit } from 'lucide-react';
import PlaylistEditDialog from '@/components/PlaylistEditDialog';

interface SmartPlaylist {
  name: string;
  base_folder: string;
  filter_tags: string[];
  filter_language: string | null;
  filter_favorites: boolean | null;
  jellyfin_playlist_id: string;
  filter_tags_display: string[];
  filter_language_display: string;
  filter_favorites_display: string;
}

interface PlaylistsResponse {
  success: boolean;
  message: string;
  data: SmartPlaylist[];
  total_count: number;
}

export default function PlaylistsPage() {
  const [playlists, setPlaylists] = useState<SmartPlaylist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingPlaylist, setEditingPlaylist] = useState<SmartPlaylist | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [syncingIndex, setSyncingIndex] = useState<number | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchPlaylists();
  }, []);

  const fetchPlaylists = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/playlists/');
      const data: PlaylistsResponse = await response.json();

      if (data.success) {
        setPlaylists(data.data || []);
      } else {
        setError(data.message || '獲取播放清單失敗');
      }
    } catch (err) {
      setError('網路錯誤，請稍後再試');
      console.error('Error fetching playlists:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditPlaylist = (playlist: SmartPlaylist, index: number) => {
    setEditingPlaylist(playlist);
    setEditingIndex(index);
    setEditDialogOpen(true);
  };

  const handleSavePlaylist = async (index: number | null, updatedPlaylist: Partial<SmartPlaylist>) => {
    try {
      setLoading(true);

      if (index === null) {
        // 新增播放清單
        const response = await fetch('/api/playlists/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updatedPlaylist),
        });

        const data = await response.json();

        if (data.success) {
          // 重新載入播放清單
          await fetchPlaylists();
          setEditDialogOpen(false);
          setEditingPlaylist(null);
          setEditingIndex(null);
          setIsCreating(false);
          setSuccessMessage(data.message || '成功建立播放清單');
          // 清除成功訊息 after 3 seconds
          setTimeout(() => setSuccessMessage(null), 3000);
        } else {
          setError(data.message || '建立播放清單失敗');
        }
      } else {
        // 更新播放清單
        const response = await fetch(`/api/playlists/${index}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updatedPlaylist),
        });

        const data = await response.json();

        if (data.success) {
          // 重新載入播放清單
          await fetchPlaylists();
          setEditDialogOpen(false);
          setEditingPlaylist(null);
          setEditingIndex(null);
          setSuccessMessage(data.message || '成功更新播放清單');
          // 清除成功訊息 after 3 seconds
          setTimeout(() => setSuccessMessage(null), 3000);
        } else {
          setError(data.message || '更新播放清單失敗');
        }
      }
    } catch (err) {
      setError('網路錯誤，請稍後再試');
      console.error('Error saving playlist:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPlaylist = () => {
    setEditingPlaylist(null);
    setEditingIndex(null);
    setIsCreating(true);
    setEditDialogOpen(true);
  };

  const handleSyncToJellyfin = async (index: number, playlist: SmartPlaylist) => {
    if (!playlist.jellyfin_playlist_id) {
      setError('此播放清單沒有設定 Jellyfin Playlist ID');
      return;
    }

    try {
      setSyncingIndex(index);
      setError(null);
      setSuccessMessage(null);

      const response = await fetch(`/api/playlists/${index}/sync-to-jellyfin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        setSuccessMessage(data.message || '同步成功');
        // 清除成功訊息 after 3 seconds
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        setError(data.message || '同步到 Jellyfin 失敗');
      }
    } catch (err) {
      setError('網路錯誤，請稍後再試');
      console.error('Error syncing to Jellyfin:', err);
    } finally {
      setSyncingIndex(null);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto px-8 py-4">
        <h1 className="text-2xl mt-4 mb-6 font-bold text-gray-900">播放清單管理</h1>
        <div className="bg-white shadow rounded-lg p-6">
          <p className="text-gray-600">載入中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto px-8 py-4">
        <h1 className="text-2xl mt-4 mb-6 font-bold text-gray-900">播放清單管理</h1>
        <div className="bg-white shadow rounded-lg p-6">
          <p className="text-red-600">錯誤：{error}</p>
          <Button onClick={fetchPlaylists} className="mt-4">
            重新載入
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto px-8 py-4">
      <div className="flex justify-between items-center mt-4 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">播放清單管理</h1>
        <Button
          onClick={handleAddPlaylist}
          className="bg-gray-600 hover:bg-gray-700 text-white"
        >
          <Plus className="w-4 h-4" />
          Add Playlist
        </Button>
      </div>

      {/* 成功訊息 */}
      {successMessage && (
        <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
          {successMessage}
        </div>
      )}

      {/* 錯誤訊息 */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-900 hover:text-red-700"
          >
            ✕
          </button>
        </div>
      )}

      <div className="bg-white border rounded-2xl overflow-hidden">
        <div>
          {playlists.length === 0 ? (
            <p className="text-gray-600 text-center py-8">尚無播放清單</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full table-auto border-collapse">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      Jellyfin Playlist Id
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      Title
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      FilterTags (篩選)
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      BaseFolder
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      FilterLanguages
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      FilterFavorites
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {playlists.map((playlist, index) => (
                    <tr key={index} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-900 font-mono truncate max-w-[200px] min-w-[100px]">
                        {playlist.jellyfin_playlist_id || '未設定'}
                      </td>
                      <td className="px-4 py-3 text-gray-900 font-medium max-w-[240px] min-w-[100px]">
                        {playlist.name}
                      </td>
                      <td className="px-4 py-3 text-gray-900 max-w-[200px] min-w-[100px]">
                        {playlist.filter_tags_display.length > 0 ? (
                          <span className="space-x-1 gap-2">
                            {playlist.filter_tags_display.map((tag, tagIndex) => (
                              <span
                                key={tagIndex}
                                className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-900 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </span>
                        ) : (
                          <span className="text-gray-500">不篩選</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-900 max-w-[200px] min-w-[100px]">
                        {playlist.base_folder}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-90 max-w-[200px] min-w-[100px]0">
                        <span className="inline-block px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                          {playlist.filter_language_display}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center text-gray-900 max-w-[200px] min-w-[100px]">
                        <span className="inline-block px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                          {playlist.filter_favorites_display}
                        </span>
                      </td>
                      <td className="px-4 py-3 space-x-2 max-w-[200px] min-w-[100px] text-center">
                        <Link
                          href={`/playlist/${index}`}
                          className="inline-flex items-center p-3 text-xs bg-gray-100 text-gray-800 rounded hover:bg-gray-300"
                          title="查看播放清單"
                        >
                          <ListMusic className="w-6 h-6" />
                        </Link>
                        <button
                          onClick={() => handleEditPlaylist(playlist, index)}
                          className="inline-flex items-center p-3 text-xs bg-gray-100 text-gray-800 rounded hover:bg-gray-300"
                          title="編輯播放清單"
                        >
                          <Edit className="w-6 h-6" />
                        </button>
                        <button
                          onClick={() => handleSyncToJellyfin(index, playlist)}
                          disabled={syncingIndex === index}
                          className={`inline-flex items-center p-3 text-xs rounded ${syncingIndex === index
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-gray-100 text-gray-800 hover:bg-gray-300'
                            }`}
                          title={playlist.jellyfin_playlist_id ? "同步到 Jellyfin" : "需要設定 Jellyfin Playlist ID"}
                        >
                          <RefreshCcw className={`w-6 h-6 ${syncingIndex === index ? 'animate-spin' : ''}`} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        共 {playlists.length} 個播放清單
      </div>

      <PlaylistEditDialog
        playlist={editingPlaylist}
        playlistIndex={editingIndex}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        onSave={handleSavePlaylist}
        isCreate={isCreating}
      />
    </div>
  );
}