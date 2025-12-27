import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCcw, Edit, Trash2, Download, FileText, FolderPlus, ArrowUpDown, ArrowUp, ArrowDown, Upload, Save, Folder, FolderX, ListMusic, Languages, Heart, SortDesc, Tags, CircleOff, Settings } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
  const { generatingAll, handleGenerateAllM3U } = useGenerateAllM3U();

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
        toast.error(data.message || '獲取播放清單失敗');
      }
    } catch (err) {
      toast.error('網路錯誤，請稍後再試');
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
          toast.success(data.message || '成功建立播放清單');
        } else {
          toast.error(data.message || '建立播放清單失敗');
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
          toast.success(data.message || '成功更新播放清單');
        } else {
          toast.error(data.message || '更新播放清單失敗');
        }
      }
    } catch (err) {
      toast.error('網路錯誤，請稍後再試');
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

      const data = await api.delete(`playlists/${deletingId}`);

      if (data.success) {
        // 重新載入播放清單
        await fetchPlaylists();
        setDeleteConfirmOpen(false);
        setDeletingPlaylist(null);
        setDeletingId(null);
        toast.success(data.message || '成功刪除播放清單');
      } else {
        toast.error(data.message || '刪除播放清單失敗');
      }
    } catch (err) {
      toast.error('網路錯誤，請稍後再試');
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

      toast.success(`開始下載播放清單 "${playlist.name}" 的 M3U 檔案`);
    } catch (error) {
      console.error('Download error:', error);
      toast.error('下載失敗，請稍後再試');
    }
  };

  const handleGenerateM3U = async (playlist: SmartPlaylist) => {
    try {
      const data = await api.post(`playlists/${playlist.id}/generate-m3u`);

      if (data.success) {
        toast.success(`成功生成 M3U 檔案到 ${data.file_path}`, { duration: 5000 });
      } else {
        toast.error(data.message || '生成 M3U 檔案失敗');
      }
    } catch (err) {
      toast.error('網路錯誤，請稍後再試');
      console.error('Error generating M3U file:', err);
    }
  };

  const handleExportConfig = () => {
    try {
      setExportingConfig(true);

      // 創建下載連結
      const downloadUrl = api.url('playlists/export-config');

      // 創建隐藏的 a 標籤來觸發下載
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `playlist_config_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success('開始下載播放清單配置檔案');
    } catch (err) {
      toast.error('下載失敗，請稍後再試');
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
        toast.error('請選擇 JSON 檔案');
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
      toast.error('請先選擇要匯入的檔案');
      return;
    }

    try {
      setImportingConfig(true);
      setImportConfirmOpen(false);

      // 讀取檔案內容驗證格式
      const fileContent = await uploadedFile.text();
      JSON.parse(fileContent); // 驗證 JSON 格式

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
        toast.success(data.message, { duration: 5000 });
        // 重新載入播放清單
        await fetchPlaylists();
      } else {
        toast.error(data.message || '匯入配置失敗');
      }
    } catch (err) {
      if (err instanceof SyntaxError) {
        toast.error('JSON 檔案格式錯誤');
      } else {
        toast.error('匯入失敗，請稍後再試');
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

  return (
    <div className="mx-auto px-8 py-4">
      <div className="flex flex-col md:flex-row items-start gap-4 mt-4 mb-6 ">
        <h1 className="text-2xl font-bold text-gray-900">播放清單管理</h1>
        <div className="flex-1 flex gap-2 flex-wrap items-start justify-start md:justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                disabled={exportingConfig || importingConfig}
              >
                {exportingConfig || importingConfig ? (
                  <RefreshCcw className="w-4 h-4 animate-spin" />
                ) : (
                  <Settings className="w-4 h-4" />
                )}
                配置管理
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={handleExportConfig}
                disabled={exportingConfig}
              >
                <Download className="w-4 h-4" />
                {exportingConfig ? '匯出中...' : '匯出配置'}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={handleImportConfigConfirm}
                disabled={importingConfig}
              >
                <Upload className="w-4 h-4" />
                {importingConfig ? '匯入中...' : '匯入配置'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            onClick={handleGenerateAllM3U}
            disabled={generatingAll}
            variant="outline"
          >
            {generatingAll ? (
              <RefreshCcw className="w-4 h-4 animate-spin" />
            ) : (
              <ListMusic className="w-4 h-4" />
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

      {playlists.length === 0 ? (
        <div className="bg-white border rounded-2xl p-8">
          <p className="text-gray-600 text-center">尚無播放清單</p>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => handleSort('name')}
              className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
            >
              排序：Title
              {getSortIcon('name')}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {getSortedPlaylists().map((playlist) => (
              <div
                key={playlist.id}
                className="bg-white border rounded-xl shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <h3
                      className="text-lg font-semibold text-gray-900 cursor-pointer hover:text-blue-600"
                      onClick={() => navigate(`/playlist/${playlist.id}`)}
                    >
                      {playlist.name}
                    </h3>
                    {playlist.is_system_level && (
                      <FolderX className="size-5 text-muted-foreground flex-shrink-0 ml-2" />
                    )}
                  </div>

                  <div className="space-y-3 text-sm">
                    <div className='flex content-start gap-2'>
                      <span className="text-gray-600 font-medium mt-0.5">
                        <Tags className="size-4" />
                      </span>
                      {playlist.filter_tags_display.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {playlist.filter_tags_display.map((tag, tagIndex) => (
                            <span
                              key={tagIndex}
                              className="inline-block px-2 py-0.5 text-xs bg-gray-100 text-gray-900 rounded-full"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-gray-500">不篩選</span>
                      )}
                    </div>

                    <div className='flex content-start gap-2'>
                      <span className="text-gray-600 font-medium mt-0.5">
                        <CircleOff className="size-4" />
                      </span>
                      {playlist.exclude_tags_display.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {playlist.exclude_tags_display.map((tag, tagIndex) => (
                            <span
                              key={tagIndex}
                              className="inline-block px-2 py-0.5 text-xs bg-red-100 text-red-800 rounded-full"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="mt-1 text-gray-500"> 不排除</span>
                      )}
                    </div>

                    <hr className='my-4' />

                    <div className='grid grid-cols-2 gap-3'>
                      <div className='flex items-center'>
                        <span className="text-gray-600 font-medium"><Folder className="size-4" /></span>
                        <span className="ml-2 inline-flex items-center gap-1.5 py-0.5 px-2 text-xs rounded-full bg-gray-100">
                          {playlist.base_folder}
                        </span>
                      </div>

                      <div className='flex items-center'>
                        <span className="text-gray-600 font-medium"><Languages className="size-4" /></span>
                        <span className="ml-2 inline-block px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded-full">
                          {playlist.filter_language_display}
                        </span>
                      </div>

                      <div className='flex items-center'>
                        <span className="text-gray-600 font-medium"><Heart className="size-4" /></span>
                        <span className="ml-2 inline-block px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded-full">
                          {playlist.filter_favorites_display}
                        </span>
                      </div>

                      <div className='flex items-center'>
                        <span className="text-gray-600 font-medium"><SortDesc className="size-4" /></span>
                        <span className="ml-2 inline-block px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded-full">
                          {playlist.sort_method_display}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="border-t bg-gray-50 px-5 py-3 flex items-center justify-end gap-2 rounded-b-xl">
                  <Button
                    onClick={() => handleEditPlaylist(playlist)}
                    variant="ghost"
                    className="inline-flex items-center p-2 text-xs"
                    title="編輯播放清單"
                  >
                    <Edit className="w-5 h-5" />
                  </Button>
                  <Button
                    onClick={() => handleDownloadM3U(playlist)}
                    variant="ghost"
                    className="inline-flex items-center p-2 text-xs"
                    title="下載 M3U 檔案"
                  >
                    <Download className="w-5 h-5" />
                  </Button>
                  <Button
                    onClick={() => handleGenerateM3U(playlist)}
                    variant="ghost"
                    className="inline-flex items-center p-2 text-xs"
                    title="生成 M3U 檔案到檔案系統"
                  >
                    <FileText className="w-5 h-5" />
                  </Button>
                  <Button
                    onClick={() => handleDeletePlaylist(playlist)}
                    variant="outlineDestructive"
                    className="inline-flex items-center p-2 text-xs border-0"
                    title="刪除播放清單"
                  >
                    <Trash2 className="w-5 h-5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

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
          toast.success(String((result as { message?: string })?.message || '同步完成'), { duration: 5000 });
        }}
      />
    </div>
  );
}
