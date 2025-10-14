'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

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

export default function CachePage() {
    const [statistics, setStatistics] = useState<CacheStatistics | null>(null);
    const [loading, setLoading] = useState(true);
    const [rebuilding, setRebuilding] = useState(false);

    const fetchStatistics = async () => {
        try {
            const response = await fetch('/api/cache/statistics');
            if (response.ok) {
                const data = await response.json();
                setStatistics(data);
            }
        } catch (error) {
            console.error('獲取快取統計失敗:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRebuildCache = async () => {
        setRebuilding(true);
        try {
            const response = await fetch('/api/cache/rebuild', {
                method: 'POST',
            });
            if (response.ok) {
                await fetchStatistics(); // 重新獲取統計
                alert('快取重建完成');
            } else {
                alert('重建快取失敗');
            }
        } catch (error) {
            console.error('重建快取失敗:', error);
            alert('重建快取失敗');
        } finally {
            setRebuilding(false);
        }
    };

    useEffect(() => {
        fetchStatistics();
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
                <Button
                    onClick={handleRebuildCache}
                    disabled={rebuilding}
                    className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {rebuilding ? '重新快取中...' : '重新快取'}
                </Button>
            </div>

            {statistics && (
                <div className="space-y-8">
                    <hr />
                    {/* 實際檔案數據 */}
                    <div>
                        <h2 className="text-xl font-semibold mb-4">實際檔案數據</h2>
                        <div>
                            <div className="grid grid-cols-4 gap-8">
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

                    <hr />

                    {/* 快取數據 */}
                    <div>
                        <h2 className="text-xl font-semibold mb-4">快取數據</h2>
                        <div className="space-y-4">
                            {/* 快取類型和資訊 */}
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="font-semibold">快取類型:</span>
                                    <span className="px-2 py-1 bg-blue-600 text-white rounded text-sm">
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
                                <div className="grid grid-cols-4 gap-8">
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
                </div>
            )}
        </div>
    );
}