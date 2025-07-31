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
        by_folder: Record<string, number>;
    };
    cache_info: {
        cache_file_exists: boolean;
        cache_file_path: string;
        cache_file_size_bytes: number;
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
                        <div>
                            <div className="grid grid-cols-4 gap-8">
                                {statistics.folders.map((folder) => (
                                    <div key={folder} className="bg-white border rounded-lg p-6 text-left">
                                        <div className="text-gray-600 mb-2">{folder}</div>
                                        <div className="flex items-end text-3xl font-bold text-gray-900">
                                            <span className="flex-1">
                                                {statistics.cached_files.by_folder[folder] || 0}
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
        </div>
    );
}