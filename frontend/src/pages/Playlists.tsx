import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Plus, ListMusic, RefreshCcw, Edit, Trash2, Download, FileText, FolderPlus, ArrowUpDown, ArrowUp, ArrowDown, Upload, Save } from 'lucide-react';
import PlaylistEditDialog from '@/components/PlaylistEditDialog';
import TaskStatusDialog from '@/components/TaskStatusDialog';
import { api } from '@/lib/api';
import { useGenerateAllM3U } from '@/hooks/useGenerateAllM3U';

interface SmartPlaylist {
  id: number;
  name: string;
  base_folder: string;
  filter_tags: string[];
  exclude_tags: string[];
  filter_language: string | null;
  filter_favorites: boolean | null;
  sort_method: string;
  is_system_level: boolean;
  filter_tags_display: string[];
  exclude_tags_display: string[];
  filter_language_display: string;
  filter_favorites_display: string;
  sort_method_display: string;
}

interface PlaylistsResponse {
  success: boolean;
  message: string;
  data: SmartPlaylist[];
  total_count: number;
}

export default function PlaylistsPage() {
  const navigate = useNavigate();
  const [playlists, setPlaylists] = useState<SmartPlaylist[]>([]);
  const [loading, setLoading] = useState(true);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingPlaylist, setEditingPlaylist] = useState<SmartPlaylist | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deletingPlaylist, setDeletingPlaylist] = useState<SmartPlaylist | null>(null);
  const [taskDialogOpen, setTaskDialogOpen] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [sortField, setSortField] = useState<'name' | null>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [exportingConfig, setExportingConfig] = useState(false);
  const [importingConfig, setImportingConfig] = useState(false);
  const [importConfirmOpen, setImportConfirmOpen] = useState(false);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // 使用批量生成 M3U 的 hook
  const { generatingAll, successMessage, error, handleGenerateAllM3U, setSuccessMessage, setError } = useGenerateAllM3U();

  useEffect(() => {
    fetchPlaylists();
  }, []);

  const fetchPlaylists = async () => {
    try {
      setLoading(true);
      const data: PlaylistsResponse = await api.get('playlists/');

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

  const handleEditPlaylist = (playlist: SmartPlaylist) => {
    setEditingPlaylist(playlist);
    setEditingId(playlist.id);
    setIsCreating(false);
    setEditDialogOpen(true);
  };

  const handleSavePlaylist = async (id: number | null, updatedPlaylist: Partial<SmartPlaylist>) => {
    try {
      setLoading(true);

      if (id === null) {
        // 新增播放清單
        const data = await api.post('playlists/', updatedPlaylist);

        if (data.success) {
          // 重新載入播放清單
          await fetchPlaylists();
          setEditDialogOpen(false);
          setEditingPlaylist(null);
          setEditingId(null);
          setIsCreating(false);
          setSuccessMessage(data.message || '成功建立播放清單');
          // 清除成功訊息 after 3 seconds
          setTimeout(() => setSuccessMessage(null), 3000);
        } else {
          setError(data.message || '建立播放清單失敗');
        }
      } else {
        // 更新播放清單
        const data = await api.put(`playlists/${id}`, updatedPlaylist);

        if (data.success) {
          // 重新載入播放清單
          await fetchPlaylists();
          setEditDialogOpen(false);
          setEditingPlaylist(null);
          setEditingId(null);
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
    setEditingId(null);
    setIsCreating(true);
    setEditDialogOpen(true);
  };

  const handleSort = (field: 'name') => {
    if (sortField === field) {
      // 如果點擊同一個欄位，切換排序方向
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // 如果點擊不同欄位，設定新欄位並重設為升序
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getSortedPlaylists = () => {
    if (!sortField) return playlists;

    const sorted = [...playlists].sort((a, b) => {
      let aValue = '';
      let bValue = '';

      if (sortField === 'name') {
        aValue = a.name.toLowerCase();
        bValue = b.name.toLowerCase();
      }

      if (sortDirection === 'asc') {
        return aValue.localeCompare(bValue);
      } else {
        return bValue.localeCompare(aValue);
      }
    });

    return sorted;
  };

  const getSortIcon = (field: 'name') => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-4 h-4 text-gray-400" />;
    }

    if (sortDirection === 'asc') {
      return <ArrowUp className="w-4 h-4 text-gray-600" />;
    } else {
      return <ArrowDown className="w-4 h-4 text-gray-600" />;
    }
  };


  const handleDeletePlaylist = (playlist: SmartPlaylist) => {
    setDeletingPlaylist(playlist);
    setDeletingId(playlist.id);
    setDeleteConfirmOpen(true);
  };

  const confirmDeletePlaylist = async () => {
    if (deletingId === null) return;

    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);

      const data = await api.delete(`playlists/${deletingId}`);

      if (data.success) {
        // 重新載入播放清單
        await fetchPlaylists();
        setDeleteConfirmOpen(false);
        setDeletingPlaylist(null);
        setDeletingId(null);
        setSuccessMessage(data.message || '成功刪除播放清單');
        // 清除成功訊息 after 3 seconds
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        setError(data.message || '刪除播放清單失敗');
      }
    } catch (err) {
      setError('網路錯誤，請稍後再試');
      console.error('Error deleting playlist:', err);
    } finally {
      setLoading(false);
    }
  };

  const cancelDeletePlaylist = () => {
    setDeleteConfirmOpen(false);
    setDeletingPlaylist(null);
    setDeletingId(null);
  };

  const handleDownloadM3U = (playlist: SmartPlaylist) => {
    try {
      // 創建下載連結
      const downloadUrl = api.url(`playlists/${playlist.id}/download-m3u`);

      // 創建隐藏的 a 標籤來觸發下載
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${playlist.name}.m3u`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setSuccessMessage(`開始下載播放清單 "${playlist.name}" 的 M3U 檔案`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      console.error('Download error:', error);
      setError('下載失敗，請稍後再試');
    }
  };

  const handleGenerateM3U = async (playlist: SmartPlaylist) => {
    try {
      setError(null);
      setSuccessMessage(null);

      const data = await api.post(`playlists/${playlist.id}/generate-m3u`);

      if (data.success) {
        setSuccessMessage(`成功生成 M3U 檔案到 ${data.file_path}`);
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        setError(data.message || '生成 M3U 檔案失敗');
      }
    } catch (err) {
      setError('網路錯誤，請稍後再試');
      console.error('Error generating M3U file:', err);
    }
  };

  const handleExportConfig = () => {
    try {
      setExportingConfig(true);
      setError(null);
      setSuccessMessage(null);

      // 創建下載連結
      const downloadUrl = api.url('playlists/export-config');

      // 創建隐藏的 a 標籤來觸發下載
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `playlist_config_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setSuccessMessage('開始下載播放清單配置檔案');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError('下載失敗，請稍後再試');
      console.error('Error exporting config:', err);
    } finally {
      setExportingConfig(false);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type === 'application/json' || file.name.endsWith('.json')) {
        setUploadedFile(file);
        setImportConfirmOpen(true);
      } else {
        setError('請選擇 JSON 檔案');
      }
    }
  };

  const handleImportConfigConfirm = () => {
    // 觸發檔案選擇
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';
    input.onchange = (e) => {
      const event = e as unknown as React.ChangeEvent<HTMLInputElement>;
      handleFileUpload(event);
    };
    input.click();
  };

  const confirmImportConfig = async () => {
    if (!uploadedFile) {
      setError('請先選擇要匯入的檔案');
      return;
    }

    try {
      setImportingConfig(true);
      setError(null);
      setSuccessMessage(null);
      setImportConfirmOpen(false);

      // 讀取檔案內容
      const fileContent = await uploadedFile.text();
      const configData = JSON.parse(fileContent);

      // 先將檔案上傳到伺服器（儲存為 playlist_config.json）
      const formData = new FormData();
      formData.append('file', uploadedFile);

      // 使用 fetch 上傳檔案
      const uploadResponse = await fetch(api.url('playlists/upload-config'), {
        method: 'POST',
        body: formData
      });

      if (!uploadResponse.ok) {
        throw new Error('上傳檔案失敗');
      }

      // 然後執行匯入
      const data = await api.post(`playlists/import-config?replace_existing=${replaceExisting}`);

      if (data.success) {
        setSuccessMessage(data.message);
        setTimeout(() => setSuccessMessage(null), 5000);
        // 重新載入播放清單
        await fetchPlaylists();
      } else {
        setError(data.message || '匯入配置失敗');
      }
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError('JSON 檔案格式錯誤');
      } else {
        setError('匯入失敗，請稍後再試');
      }
      console.error('Error importing config:', err);
    } finally {
      setImportingConfig(false);
      setUploadedFile(null);
    }
  };

  const cancelImportConfig = () => {
    setImportConfirmOpen(false);
    setReplaceExisting(false);
    setUploadedFile(null);
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
        <div className="flex gap-3">
          <Button
            onClick={handleExportConfig}
            disabled={exportingConfig}
            variant="outline"
          >
            {exportingConfig ? (
              <RefreshCcw className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {exportingConfig ? '匯出中...' : '匯出配置'}
          </Button>
          <Button
            onClick={handleImportConfigConfirm}
            disabled={importingConfig}
            variant="outline"
          >
            {importingConfig ? (
              <RefreshCcw className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {importingConfig ? '匯入中...' : '匯入配置'}
          </Button>
          <Button
            onClick={handleGenerateAllM3U}
            disabled={generatingAll}
            variant="outline"
          >
            {generatingAll ? (
              <RefreshCcw className="w-4 h-4 animate-spin" />
            ) : (
              <FolderPlus className="w-4 h-4" />
            )}
            {generatingAll ? '生成中...' : '批量生成 M3U'}
          </Button>
          <Button
            onClick={handleAddPlaylist}
            variant="default"
          >
            <Plus className="w-4 h-4" />
            新增播放清單
          </Button>
        </div>
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
                      <button
                        onClick={() => handleSort('name')}
                        className="flex items-center gap-2 hover:text-gray-700 transition-colors"
                      >
                        Title
                        {getSortIcon('name')}
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      FilterTags (篩選)
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      ExcludeTags (排除)
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
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900 max-w-[150px] min-w-[120px]">
                      Sort Method
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900 max-w-[200px] min-w-[100px]">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {getSortedPlaylists().map((playlist) => {
                    return (
                      <tr key={playlist.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-900 font-medium max-w-[240px] min-w-[100px]">
                          {playlist.name}
                        </td>
                        <td className="space-x-2 space-y-2 px-4 py-3 text-gray-900 max-w-[200px] min-w-[120px]">
                          {playlist.filter_tags_display.length > 0 ? (
                            <span className="space-x-2 space-y-2">
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
                        <td className="space-x-2 space-y-2 px-4 py-3 text-gray-900 max-w-[200px] min-w-[120px]">
                          {playlist.exclude_tags_display.length > 0 ? (
                            <span className="space-x-2 space-y-2">
                              {playlist.exclude_tags_display.map((tag, tagIndex) => (
                                <span
                                  key={tagIndex}
                                  className="inline-block px-2 py-1 text-xs bg-red-100 text-red-800 rounded"
                                >
                                  {tag}
                                </span>
                              ))}
                            </span>
                          ) : (
                            <span className="text-gray-500">不排除</span>
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
                        <td className="px-4 py-3 text-center text-gray-900 max-w-[150px] min-w-[120px]">
                          <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                            {playlist.sort_method_display}
                          </span>
                        </td>
                        <td className="px-4 py-3 max-w-[280px] min-w-[100px] text-center">
                          <button
                            onClick={() => navigate(`/playlist/${playlist.id}`)}
                            className="m-1 inline-flex items-center p-2 text-xs text-gray-800 rounded border hover:bg-gray-100"
                            title="查看播放清單"
                          >
                            <ListMusic className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleEditPlaylist(playlist)}
                            className="m-1 inline-flex items-center p-2 text-xs text-gray-800 rounded border hover:bg-gray-100"
                            title="編輯播放清單"
                          >
                            <Edit className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleDownloadM3U(playlist)}
                            className="m-1 inline-flex items-center p-2 text-xs text-gray-800 rounded border hover:bg-gray-100"
                            title="下載 M3U 檔案"
                          >
                            <Download className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleGenerateM3U(playlist)}
                            className="m-1 inline-flex items-center p-2 text-xs text-gray-800 rounded border hover:bg-gray-100"
                            title="生成 M3U 檔案到檔案系統"
                          >
                            <FileText className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleDeletePlaylist(playlist)}
                            className="m-1 inline-flex items-center p-2 text-xs text-red-800 rounded border border-red-200 hover:bg-red-100"
                            title="刪除播放清單"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
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
        playlistId={editingId}
        open={editDialogOpen}
        onOpenChange={(open) => {
          setEditDialogOpen(open);
          if (!open) {
            // 對話框關閉時清理狀態
            setEditingPlaylist(null);
            setEditingId(null);
            setIsCreating(false);
          }
        }}
        onSave={handleSavePlaylist}
        isCreate={isCreating}
      />

      {/* 刪除確認對話框 */}
      {deleteConfirmOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              確認刪除播放清單
            </h3>
            <p className="text-gray-600 mb-6">
              您確定要刪除播放清單「{deletingPlaylist?.name}」嗎？
              <br />
              <span className="text-red-600 font-medium">此操作無法復原。</span>
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={cancelDeletePlaylist}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={confirmDeletePlaylist}
                disabled={loading}
                className={`px-4 py-2 text-white rounded ${loading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-700'
                  }`}
              >
                {loading ? '刪除中...' : '確認刪除'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 匯入確認對話框 */}
      {importConfirmOpen && uploadedFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              確認匯入播放清單配置
            </h3>
            <div className="mb-4 p-3 bg-gray-50 rounded border border-gray-200">
              <p className="text-sm text-gray-600 mb-1">檔案名稱：</p>
              <p className="text-sm font-medium text-gray-900">{uploadedFile.name}</p>
            </div>
            <div className="mb-6">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={replaceExisting}
                  onChange={(e) => setReplaceExisting(e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  替換模式：刪除所有現有播放清單後再匯入
                </span>
              </label>
              <p className="text-xs text-gray-500 mt-2 ml-7">
                {replaceExisting ? (
                  <span className="text-red-600 font-medium">
                    警告：這將刪除所有現有的播放清單，並替換為配置檔中的播放清單。此操作無法復原。
                  </span>
                ) : (
                  <span className="text-blue-600">
                    僅會新增配置檔中不存在的播放清單，已存在的播放清單將被跳過。
                  </span>
                )}
              </p>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={cancelImportConfig}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={confirmImportConfig}
                disabled={importingConfig}
                className={`px-4 py-2 text-white rounded ${importingConfig
                  ? 'bg-gray-400 cursor-not-allowed'
                  : replaceExisting
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                  }`}
              >
                {importingConfig ? '匯入中...' : '確認匯入'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 任務狀態對話框 */}
      <TaskStatusDialog
        taskId={currentTaskId}
        isOpen={taskDialogOpen}
        onClose={() => {
          setTaskDialogOpen(false);
          setCurrentTaskId(null);
        }}
        onComplete={(result) => {
          // 任務完成時刷新播放清單
          fetchPlaylists();
          setSuccessMessage(String((result as { message?: string })?.message || '同步完成'));
          setTimeout(() => setSuccessMessage(null), 5000);
        }}
      />
    </div>
  );
}
