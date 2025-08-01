'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, CloudUpload, Download } from 'lucide-react';

interface SongWithDate {
    file_path: string | null;
    jellyfin_date_created: string | null;
    formatted_date: string;
    jellyfin_id: string;
    song_name: string;
}

interface PlaylistSongsResponse {
    success: boolean;
    message: string;
    playlist_name: string;
    playlist_index: number;
    filter_summary: {
        base_folder: string;
        filter_tags: string[];
        filter_language: string | null;
        filter_favorites: boolean | null;
        total_files_found: number;
        files_after_filtering: number;
        sort_method?: string;
    };
    songs: SongWithDate[];
    total_count: number;
}

export default function PlaylistDetailPage() {
    const params = useParams();
    const router = useRouter();
    const playlistId = params.id as string;

    const [playlistData, setPlaylistData] = useState<PlaylistSongsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [syncLoading, setSyncLoading] = useState(false);
    const [downloadLoading, setDownloadLoading] = useState(false);

    useEffect(() => {
        if (playlistId) {
            fetchPlaylistSongs();
        }
    }, [playlistId]); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchPlaylistSongs = async () => {
        try {
            setLoading(true);
            const response = await fetch(`/api/playlists/${playlistId}/songs`);
            const data: PlaylistSongsResponse = await response.json();

            if (data.success) {
                setPlaylistData(data);
            } else {
                setError(data.message || '獲取播放清單歌曲失敗');
            }
        } catch (err) {
            setError('網路錯誤，請稍後再試');
            console.error('Error fetching playlist songs:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSyncToJellyfin = async () => {
        try {
            setSyncLoading(true);
            const response = await fetch(`/api/playlists/${playlistId}/sync-to-jellyfin`, {
                method: 'POST',
            });

            const data = await response.json();

            if (data.success) {
                alert('成功同步到 Jellyfin！');
            } else {
                alert(`同步失敗：${data.message}`);
            }
        } catch (error) {
            console.error('同步錯誤:', error);
            alert('同步過程中發生錯誤');
        } finally {
            setSyncLoading(false);
        }
    };

    const handleDownloadM3U = async () => {
        try {
            setDownloadLoading(true);
            const response = await fetch(`/api/playlists/${playlistId}/download-m3u`);

            if (response.ok) {
                // 取得檔案內容並觸發下載
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${playlistData?.playlist_name || 'playlist'}.m3u`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                const errorData = await response.json();
                alert(`下載失敗：${errorData.message}`);
            }
        } catch (error) {
            console.error('下載錯誤:', error);
            alert('下載過程中發生錯誤');
        } finally {
            setDownloadLoading(false);
        }
    };

    const getFileName = (filePath: string | null | undefined) => {
        if (!filePath || typeof filePath !== 'string') {
            return '';
        }
        return filePath.split('/').pop() || filePath;
    };

    const getFileExtension = (fileName: string | null | undefined) => {
        if (!fileName || typeof fileName !== 'string') {
            return '';
        }
        return fileName.split('.').pop()?.toUpperCase() || '';
    };

    if (loading) {
        return (
            <div className="mx-auto px-8 py-4">
                <div className="flex items-center gap-4 mb-6">
                    <Button
                        onClick={() => router.back()}
                        variant="outline"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        返回
                    </Button>
                    <h1 className="text-2xl font-bold text-gray-900">載入中...</h1>
                </div>
                <div className="bg-white shadow rounded-lg p-6">
                    <p className="text-gray-600">載入播放清單歌曲中...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="mx-auto px-8 py-4">
                <div className="flex items-center gap-4 mb-6">
                    <Button
                        onClick={() => router.back()}
                        variant="outline"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        返回
                    </Button>
                    <h1 className="text-2xl font-bold text-gray-900">錯誤</h1>
                </div>
                <div className="bg-white shadow rounded-lg p-6">
                    <p className="text-red-600">錯誤：{error}</p>
                    <Button onClick={fetchPlaylistSongs} className="mt-4">
                        重新載入
                    </Button>
                </div>
            </div>
        );
    }

    if (!playlistData) {
        return (
            <div className="mx-auto px-8 py-4">
                <div className="flex items-center gap-4 mb-6">
                    <Button
                        onClick={() => router.back()}
                        variant="outline"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        返回
                    </Button>
                    <h1 className="text-2xl font-bold text-gray-900">無資料</h1>
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto px-8 py-4">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <Button
                        onClick={() => router.back()}
                        variant="outline"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        返回
                    </Button>
                    <h1 className="text-2xl font-bold text-gray-900">
                        {playlistData.playlist_name}
                    </h1>
                </div>
                <div className="flex items-center gap-3">
                    <Button
                        onClick={handleDownloadM3U}
                        disabled={downloadLoading}
                        variant="outline"
                        className="border-none bg-gray-50 text-gray-600 hover:bg-gray-200"
                    >
                        <Download className="w-4 h-4" />
                        {downloadLoading ? '下載中...' : '下載 .m3u'}
                    </Button>
                    <Button
                        onClick={handleSyncToJellyfin}
                        disabled={syncLoading}
                        variant="default"
                        className="bg-gray-600 hover:bg-gray-700"
                    >
                        <CloudUpload className="w-4 h-4" />
                        {syncLoading ? '同步中...' : '同步到 Jellyfin'}
                    </Button>
                </div>
            </div>

            {/* 篩選條件摘要 */}
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle>篩選條件摘要</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                        <div>
                            <span className="font-medium text-gray-700">基礎資料夾：</span>
                            <span className="text-gray-900">{playlistData.filter_summary.base_folder}</span>
                        </div>
                        <div>
                            <span className="font-medium text-gray-700">標籤篩選：</span>
                            {playlistData.filter_summary.filter_tags.length > 0 ? (
                                <span className="space-x-1">
                                    {playlistData.filter_summary.filter_tags.map((tag, index) => (
                                        <span
                                            key={index}
                                            className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded"
                                        >
                                            {tag}
                                        </span>
                                    ))}
                                </span>
                            ) : (
                                <span className="text-gray-500">無</span>
                            )}
                        </div>
                        <div>
                            <span className="font-medium text-gray-700">語言篩選：</span>
                            <span className="text-gray-900">
                                {playlistData.filter_summary.filter_language || '無'}
                            </span>
                        </div>
                        <div>
                            <span className="font-medium text-gray-700">我的最愛：</span>
                            <span className="text-gray-900">
                                {playlistData.filter_summary.filter_favorites === null ? '無' :
                                    playlistData.filter_summary.filter_favorites ? '是' : '否'}
                            </span>
                        </div>
                    </div>
                    <div className="mt-4 pt-4 border-t">
                        <div className="flex gap-6 text-sm">
                            <div>
                                <span className="font-medium text-gray-700">總檔案數：</span>
                                <span className="text-gray-900">{playlistData.filter_summary.total_files_found}</span>
                            </div>
                            <div>
                                <span className="font-medium text-gray-700">篩選後檔案數：</span>
                                <span className="text-gray-900">{playlistData.filter_summary.files_after_filtering}</span>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 歌曲列表 */}
            <div className="bg-white border rounded-2xl p-0 overflow-hidden">
                <div className="p-4 font-bold">
                    <p>歌曲列表 ({playlistData.total_count} 首)
                        {playlistData.filter_summary.sort_method === 'local_jellyfin_add_time' &&
                            <span className="text-sm text-green-600 font-normal ml-2">
                                ✓ 按本地 jellyfin_add_time 標籤排序 (新→舊)
                            </span>
                        }
                        {playlistData.filter_summary.sort_method === 'jellyfin_date_created' &&
                            <span className="text-sm text-blue-600 font-normal ml-2">
                                ✓ 按 Jellyfin 加入時間排序 (新→舊)
                            </span>
                        }
                    </p>
                </div>
                <div>
                    {playlistData.songs.length === 0 ? (
                        <p className="text-gray-600 text-center py-8">此播放清單暫無歌曲</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="min-w-full table-auto border-collapse">
                                <thead>
                                    <tr className="border-b bg-gray-50">
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">
                                            #
                                        </th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">
                                            歌曲名稱
                                        </th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">
                                            加入時間
                                        </th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">
                                            格式
                                        </th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">
                                            檔案路徑
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {playlistData.songs.map((song, index) => {
                                        const fileName = getFileName(song.file_path);
                                        const fileExtension = getFileExtension(fileName);

                                        return (
                                            <tr key={index} className="border-b hover:bg-gray-50">
                                                <td className="px-4 py-3 text-sm text-gray-500">
                                                    {index + 1}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-900 font-medium truncate max-w-[300px] min-w-[150px]">
                                                    {song.song_name || fileName}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-700 min-w-[150px]">
                                                    {song.formatted_date ? (
                                                        <div className="flex flex-col">
                                                            <span className="text-xs text-gray-900">{song.formatted_date.split(' ')[0]}</span>
                                                            <span className="text-xs text-gray-500">{song.formatted_date.split(' ')[1]}</span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-gray-400 text-xs">無日期資訊</span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-3 text-sm">
                                                    <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">
                                                        {fileExtension}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-600 font-mono text-xs truncate max-w-[400px]">
                                                    {song.file_path}
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
        </div>
    );
}