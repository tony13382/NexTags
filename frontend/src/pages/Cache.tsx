import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/lib/api';

interface CacheStatistics {
    actual_files: {
        total: number;
        by_folder: Record<string, number>;
    };
    cached_files: {
        total: number;
        by_folder?: Record<string, number>;
    };
    cache_info: {
        cache_type: string;
        cache_file_exists?: boolean;
        cache_file_path?: string;
        cache_file_size_bytes?: number;
        memory_used_bytes?: number;
        memory_used_human?: string;
        redis_version?: string;
    };
    folders: string[];
}

interface WaitImportFile {
    file_id: string;
    original_filename: string;
    status: string;
    created_at: string;
    updated_at: string;
    base_folder: string;
    errors: string[];
}

export default function Cache() {
    const [statistics, setStatistics] = useState<CacheStatistics | null>(null);
    const [loading, setLoading] = useState(true);
    const [rebuilding, setRebuilding] = useState(false);
    const [waitImportFiles, setWaitImportFiles] = useState<WaitImportFile[]>([]);
    const [loadingWaitImport, setLoadingWaitImport] = useState(false);

    // Dialog states
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [fileToDelete, setFileToDelete] = useState<{ id: string; name: string } | null>(null);

    const fetchStatistics = async () => {
        try {
            const data = await api.get('cache/statistics');
            setStatistics(data);
        } catch (error) {
            console.error('獲取快取統計失敗:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRebuildCache = async () => {
        setRebuilding(true);
        try {
            await api.post('cache/rebuild');
            await fetchStatistics();
            toast.success('快取重建完成');
        } catch (error) {
            console.error('重建快取失敗:', error);
            toast.error('重建快取失敗');
        } finally {
            setRebuilding(false);
        }
    };

    const fetchWaitImportFiles = async () => {
        setLoadingWaitImport(true);
        try {
            const data = await api.get('music-import/pending');
            if (data.success) {
                setWaitImportFiles(data.pending_imports);
            }
        } catch (error) {
            console.error('獲取 WaitImport 檔案失敗:', error);
        } finally {
            setLoadingWaitImport(false);
        }
    };

    const handleDeleteClick = (fileId: string, filename: string) => {
        setFileToDelete({ id: fileId, name: filename });
        setShowDeleteConfirm(true);
    };

    const handleConfirmDelete = async () => {
        if (!fileToDelete) return;

        try {
            const response = await fetch(api.url('music-import/delete'), {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_id: fileToDelete.id })
            });

            if (response.ok) {
                toast.success('檔案已刪除');
                await fetchWaitImportFiles();
            } else {
                toast.error('刪除檔案失敗');
            }
        } catch (error) {
            console.error('刪除檔案失敗:', error);
            toast.error('刪除檔案失敗');
        } finally {
            setShowDeleteConfirm(false);
            setFileToDelete(null);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    useEffect(() => {
        fetchStatistics();
        fetchWaitImportFiles();
    }, []);

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="text-center">載入中...</div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            {/* 標題和重新快取按鈕 */}
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-2xl font-bold">快取管理</h1>
            </div>

            {/* WaitImport 檔案管理 */}
            <div className="mb-8">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold">WaitImport 暫存檔案</h2>
                    <Button
                        onClick={fetchWaitImportFiles}
                        disabled={loadingWaitImport}
                        variant="outline"
                        className="flex items-center gap-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        {loadingWaitImport ? '載入中...' : '重新整理'}
                    </Button>
                </div>

                {loadingWaitImport ? (
                    <div className="text-center py-8 text-gray-600">載入中...</div>
                ) : waitImportFiles.length === 0 ? (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
                        <p className="text-gray-600">目前沒有暫存檔案</p>
                    </div>
                ) : (
                    <div className="bg-white rounded-lg border overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 border-b">
                                    <tr>
                                        <th className="px-4 py-3 text-left font-medium text-gray-500">檔案名稱</th>
                                        <th className="px-4 py-3 text-left font-medium text-gray-500">狀態</th>
                                        <th className="px-4 py-3 text-left font-medium text-gray-500">目標資料夾</th>
                                        <th className="px-4 py-3 text-left font-medium text-gray-500">建立時間</th>
                                        <th className="px-4 py-3 text-center font-medium text-gray-500">操作</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {waitImportFiles.map((file) => (
                                        <tr key={file.file_id} className="hover:bg-gray-50">
                                            <td className="px-4 py-3">
                                                <div className="font-medium text-gray-900">{file.original_filename}</div>
                                                {file.errors.length > 0 && (
                                                    <div className="text-xs text-red-600 mt-1">
                                                        錯誤: {file.errors.join(', ')}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="inline-block px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                    {file.status}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-gray-600">{file.base_folder}</td>
                                            <td className="px-4 py-3 text-gray-600 text-sm">
                                                {formatDate(file.created_at)}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleDeleteClick(file.file_id, file.original_filename)}
                                                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>

            <hr className="my-8" />

            {statistics && statistics.folders.length === 0 ? (
                <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-8 text-center">
                    <div className="text-6xl mb-4">⚠️</div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-4">尚未設定音樂資料夾</h2>
                    <p className="text-gray-600 mb-6">
                        系統目前沒有設定任何音樂資料夾。請先到系統設定頁面新增允許的音樂資料夾，才能使用快取功能。
                    </p>
                    <a
                        href="/settings"
                        className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        前往系統設定
                    </a>
                </div>
            ) : statistics && (
                <div className="space-y-8">

                    {/* 快取數據 */}
                    <div>
                        <div className='flex mb-4 items-center'>
                            <h2 className="flex-1 text-xl font-semibold mb-4">快取數據</h2>
                            <Button
                                variant="outline"
                                onClick={handleRebuildCache}
                                disabled={rebuilding || !statistics?.folders.length}
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                {rebuilding ? '重新快取中...' : '重新快取'}
                            </Button>
                        </div>
                        <div className="space-y-4">
                            {/* 快取類型和資訊 */}
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="font-semibold">快取類型：</span>
                                    <span className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded-full text-sm">
                                        {statistics.cache_info.cache_type || 'Unknown'}
                                    </span>
                                </div>
                                {statistics.cache_info.cache_type === 'Redis' && (
                                    <div className="grid grid-cols-3 gap-4 mt-3">
                                        <div>
                                            <div className="text-sm text-gray-600">Redis 版本</div>
                                            <div className="font-semibold">{statistics.cache_info.redis_version}</div>
                                        </div>
                                        <div>
                                            <div className="text-sm text-gray-600">記憶體使用</div>
                                            <div className="font-semibold">{statistics.cache_info.memory_used_human}</div>
                                        </div>
                                        <div>
                                            <div className="text-sm text-gray-600">快取檔案數</div>
                                            <div className="font-semibold">{statistics.cached_files.total}</div>
                                        </div>
                                    </div>
                                )}
                                {statistics.cache_info.cache_file_exists && (
                                    <div className="mt-3 text-sm text-gray-600">
                                        <div>快取檔案: {statistics.cache_info.cache_file_path}</div>
                                        <div>檔案大小: {(statistics.cache_info.cache_file_size_bytes! / 1024 / 1024).toFixed(2)} MB</div>
                                    </div>
                                )}
                            </div>

                            {/* 各資料夾快取數據 */}
                            {statistics.cached_files.by_folder && (
                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
                                    {statistics.folders.map((folder) => (
                                        <div key={folder} className="bg-white border rounded-lg p-6 text-left">
                                            <div className="text-gray-600 mb-2">{folder}</div>
                                            <div className="flex items-end text-3xl font-bold text-gray-900">
                                                <span className="flex-1">
                                                    {statistics.cached_files.by_folder![folder] || 0}
                                                </span>
                                                <span className="text-base">首</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <hr />
                    {/* 實際檔案數據 */}
                    <div>
                        <h2 className="text-xl font-semibold mb-4">實際檔案數據</h2>
                        <div>
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
                                {statistics.folders.map((folder) => (
                                    <div key={folder} className="bg-white border rounded-lg p-6 text-left">
                                        <div className="text-gray-600 mb-2">{folder}</div>
                                        <div className="flex items-end text-3xl font-bold text-gray-900">
                                            <span className="flex-1">
                                                {statistics.actual_files.by_folder[folder] || 0}
                                            </span>
                                            <span className="text-base">首</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 刪除確認 Dialog */}
            <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <DialogContent>
                    <DialogHeader className='flex flex-col gap-2'>
                        <DialogTitle>確認刪除</DialogTitle>
                        <DialogDescription>
                            確定要刪除檔案 &quot;{fileToDelete?.name}&quot; 嗎？此操作無法復原。
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            className="flex-1"
                            onClick={() => {
                                setShowDeleteConfirm(false);
                                setFileToDelete(null);
                            }}
                        >
                            取消
                        </Button>
                        <Button
                            variant="destructive"
                            className="flex-1"
                            onClick={handleConfirmDelete}
                        >
                            確定刪除
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
