'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import MusicImportTagEditor from '@/components/MusicImportTagEditor'

// 匯入狀態枚舉
enum ImportStatus {
    UPLOADED = 'uploaded',
    CONVERTED = 'converted',
    TAGS_EXTRACTED = 'tags_extracted',
    TAGS_EDITED = 'tags_edited',
    ARTIST_READY = 'artist_ready',
    ALBUM_READY = 'album_ready',
    READY_TO_MOVE = 'ready_to_move',
    COMPLETED = 'completed',
    FAILED = 'failed'
}

// 類型定義
interface ImportSession {
    file_id: string
    original_filename: string
    status: ImportStatus
    temp_path: string
    base_folder: string
    needs_conversion: boolean
    format: string
    extracted_tags?: Record<string, unknown>
    suggested_filename?: string
    artist_name?: string
    album_name?: string
    final_filename?: string
    preview_final_path?: string
    errors?: string[]
}

interface BaseFolderOption {
    value: string
    label: string
}

export default function NewMusicPage() {
    // 狀態管理
    const [currentSession, setCurrentSession] = useState<ImportSession | null>(null)
    const [baseFolders, setBaseFolders] = useState<BaseFolderOption[]>([])
    const [selectedBaseFolder, setSelectedBaseFolder] = useState<string>('')
    const [isLoading, setIsLoading] = useState(false)
    const [showTagEditor, setShowTagEditor] = useState(false)
    const [showArtistImageDialog, setShowArtistImageDialog] = useState(false)
    const [artistName, setArtistName] = useState('')
    const [albumName, setAlbumName] = useState('')
    const [finalFilename, setFinalFilename] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [progress, setProgress] = useState<number>(0)

    // 載入基礎資料夾選項
    useEffect(() => {
        fetchBaseFolders()
    }, [])

    const fetchBaseFolders = async () => {
        try {
            const response = await fetch('/api/tags/baseFolders')
            const data = await response.json()
            if (data.success) {
                const folders = data.base_folders.map((folder: string) => ({
                    value: folder,
                    label: folder
                }))
                setBaseFolders(folders)
                if (folders.length > 0) {
                    setSelectedBaseFolder(folders[0].value)
                }
            }
        } catch (error) {
            console.error('載入基礎資料夾失敗:', error)
            setError('載入基礎資料夾失敗')
        }
    }

    // 檔案上傳處理
    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (!file || !selectedBaseFolder) return

        setIsLoading(true)
        setError(null)
        setProgress(10)

        try {
            const formData = new FormData()
            formData.append('file', file)
            formData.append('base_folder', selectedBaseFolder)

            const response = await fetch('/api/music-import/upload', {
                method: 'POST',
                body: formData
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '檔案上傳失敗')
            }

            setCurrentSession(data)
            setProgress(20)

            // 如果需要轉換，自動執行轉換
            if (data.needs_conversion) {
                await convertFile(data.file_id)
            } else {
                await extractTags(data.file_id)
            }

        } catch (error) {
            console.error('檔案上傳失敗:', error)
            setError(error instanceof Error ? error.message : '檔案上傳失敗')
        } finally {
            setIsLoading(false)
        }
    }

    // 轉換檔案
    const convertFile = async (fileId: string) => {
        try {
            setProgress(30)
            const response = await fetch('/api/music-import/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_id: fileId })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '檔案轉換失敗')
            }

            // 更新當前會話狀態
            await refreshSessionStatus(fileId)
            setProgress(40)

            // 繼續提取標籤
            await extractTags(fileId)

        } catch (error) {
            console.error('檔案轉換失敗:', error)
            setError(error instanceof Error ? error.message : '檔案轉換失敗')
        }
    }

    // 提取標籤
    const extractTags = async (fileId: string) => {
        try {
            setProgress(50)
            const response = await fetch('/api/music-import/extract-tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_id: fileId })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '標籤提取失敗')
            }

            // 更新當前會話狀態
            await refreshSessionStatus(fileId)
            setProgress(60)

            // 顯示標籤編輯器
            setShowTagEditor(true)

        } catch (error) {
            console.error('標籤提取失敗:', error)
            setError(error instanceof Error ? error.message : '標籤提取失敗')
        }
    }

    // 更新標籤
    const handleUpdateTags = async (tags: Record<string, unknown>) => {
        if (!currentSession) return

        try {
            const response = await fetch('/api/music-import/update-tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: currentSession.file_id,
                    tags: tags
                })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '標籤更新失敗')
            }

            // 更新當前會話狀態
            await refreshSessionStatus(currentSession.file_id)
            setProgress(70)
            setShowTagEditor(false)

            // 從標籤中提取歌手和專輯名稱
            const artistName = String(tags.artist || '')
            const albumName = String(tags.album || '')
            setArtistName(artistName)
            setAlbumName(albumName)

            // 檢查歌手資料夾 - 直接使用從標籤提取的值
            await checkArtist(currentSession.file_id, artistName, albumName)

        } catch (error) {
            console.error('標籤更新失敗:', error)
            setError(error instanceof Error ? error.message : '標籤更新失敗')
        }
    }

    // 檢查歌手資料夾
    const checkArtist = async (fileId: string, artistName: string, albumName: string) => {
        try {
            const response = await fetch('/api/music-import/check-artist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: fileId,
                    artist_name: artistName
                })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '檢查歌手資料夾失敗')
            }

            // 更新當前會話狀態
            await refreshSessionStatus(fileId)

            // 如果需要上傳歌手圖片，顯示對話框
            if (data.needs_artist_image) {
                setShowArtistImageDialog(true)
            } else {
                // 直接處理專輯 - 使用傳入的albumName參數
                await processAlbum(fileId, artistName, albumName)
            }

        } catch (error) {
            console.error('檢查歌手資料夾失敗:', error)
            setError(error instanceof Error ? error.message : '檢查歌手資料夾失敗')
        }
    }

    // 上傳歌手圖片
    const handleArtistImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (!file || !currentSession || !artistName) return

        try {
            const formData = new FormData()
            formData.append('file_id', currentSession.file_id)
            formData.append('artist_name', artistName)
            formData.append('image', file)

            const response = await fetch('/api/music-import/upload-artist-image', {
                method: 'POST',
                body: formData
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '歌手圖片上傳失敗')
            }

            setShowArtistImageDialog(false)

            // 繼續處理專輯 - 使用當前狀態的值
            await processAlbum(currentSession.file_id, artistName, albumName)

        } catch (error) {
            console.error('歌手圖片上傳失敗:', error)
            setError(error instanceof Error ? error.message : '歌手圖片上傳失敗')
        }
    }

    // 處理專輯
    const processAlbum = async (fileId: string, artistName: string, albumName: string) => {
        try {
            setProgress(80)
            const response = await fetch('/api/music-import/process-album', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: fileId,
                    artist_name: artistName,
                    album_name: albumName
                })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '專輯處理失敗')
            }

            // 更新當前會話狀態
            await refreshSessionStatus(fileId)

            // 設定建議的最終檔案名稱
            const suggestedFilename = currentSession?.suggested_filename || `01 - ${currentSession?.original_filename}`
            setFinalFilename(suggestedFilename)

            // 準備檔案
            await finalizeFile(fileId, suggestedFilename)

        } catch (error) {
            console.error('專輯處理失敗:', error)
            setError(error instanceof Error ? error.message : '專輯處理失敗')
        }
    }

    // 準備檔案
    const finalizeFile = async (fileId: string, filename: string) => {
        try {
            setProgress(90)
            const response = await fetch('/api/music-import/finalize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: fileId,
                    final_filename: filename
                })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '檔案準備失敗')
            }

            // 更新當前會話狀態
            await refreshSessionStatus(fileId)
            setProgress(95)

        } catch (error) {
            console.error('檔案準備失敗:', error)
            setError(error instanceof Error ? error.message : '檔案準備失敗')
        }
    }

    // 確認移動檔案
    const confirmMove = async () => {
        if (!currentSession) return

        try {
            setIsLoading(true)
            const response = await fetch('/api/music-import/confirm-move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: currentSession.file_id
                })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || '檔案移動失敗')
            }

            // 更新當前會話狀態
            await refreshSessionStatus(currentSession.file_id)
            setProgress(100)

            // 重置狀態
            setTimeout(() => {
                setCurrentSession(null)
                setProgress(0)
                setArtistName('')
                setAlbumName('')
                setFinalFilename('')
                setError(null)
            }, 2000)

        } catch (error) {
            console.error('檔案移動失敗:', error)
            setError(error instanceof Error ? error.message : '檔案移動失敗')
        } finally {
            setIsLoading(false)
        }
    }

    // 刷新會話狀態
    const refreshSessionStatus = async (fileId: string) => {
        try {
            const response = await fetch(`/api/music-import/status?file_id=${fileId}`)
            const data = await response.json()

            if (response.ok && data.success) {
                setCurrentSession(prev => ({
                    ...prev,
                    ...data.file_info,
                    file_id: fileId
                }))
            }
        } catch (error) {
            console.error('刷新會話狀態失敗:', error)
        }
    }

    // 取消匯入
    const cancelImport = async () => {
        if (!currentSession) return

        try {
            const response = await fetch('/api/music-import/delete', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: currentSession.file_id
                })
            })

            if (response.ok) {
                setCurrentSession(null)
                setProgress(0)
                setError(null)
            }
        } catch (error) {
            console.error('取消匯入失敗:', error)
        }
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
            <div className="mb-6">
                <h1 className="text-3xl font-bold">新增音樂</h1>
                <p className="text-gray-600 mt-2">上傳音樂檔案並組織到音樂庫中</p>
            </div>

            {/* 進度條 */}
            {progress > 0 && (
                <div className="mb-6">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                            className="bg-gray-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${progress}%` }}
                        ></div>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">進度: {progress}%</p>
                </div>
            )}

            {/* 錯誤訊息 */}
            {error && (
                <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
                    {error}
                </div>
            )}

            {/* 檔案上傳區域 */}
            {!currentSession && (
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle>上傳音樂檔案</CardTitle>
                        <CardDescription>
                            支援格式: MP3, FLAC, OGG, M4A (.m4a 檔案會自動轉換為 .flac)
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">目標資料夾</label>
                                <select
                                    value={selectedBaseFolder}
                                    onChange={(e) => setSelectedBaseFolder(e.target.value)}
                                    className="w-full p-2 border border-gray-300 rounded-md"
                                >
                                    {baseFolders.map((folder) => (
                                        <option key={folder.value} value={folder.value}>
                                            {folder.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">選擇音樂檔案</label>
                                <input
                                    type="file"
                                    accept=".mp3,.flac,.ogg,.m4a"
                                    onChange={handleFileUpload}
                                    disabled={isLoading}
                                    className="w-full p-2 border border-gray-300 rounded-md"
                                />
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* 當前處理狀態 */}
            {currentSession && (
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle>處理中: {currentSession.original_filename}</CardTitle>
                        <CardDescription>
                            狀態: {currentSession.status} | 格式: {currentSession.format}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {/* 最終確認區域 */}
                            {currentSession.status === ImportStatus.READY_TO_MOVE && (
                                <div className="space-y-4">
                                    <h3 className="text-lg font-semibold">確認資訊</h3>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <label className="block text-sm font-medium">歌手</label>
                                            <p className="text-gray-800">{artistName}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <label className="block text-sm font-medium">專輯</label>
                                            <p className="text-gray-800">{albumName}</p>
                                        </div>
                                        <div className="col-span-2 space-y-2">
                                            <label className="block text-sm font-medium">最終檔案名稱</label>
                                            <Input
                                                value={finalFilename}
                                                onChange={(e) => setFinalFilename(e.target.value)}
                                                className="mt-1"
                                            />
                                        </div>
                                        <div className="col-span-2 space-y-2">
                                            <label className="block text-sm font-medium">最終路徑</label>
                                            <p className="text-gray-600 text-sm">{currentSession.preview_final_path}</p>
                                        </div>
                                    </div>

                                    <div className="flex space-x-4 justify-end">
                                        <Button
                                            onClick={confirmMove}
                                            disabled={isLoading}
                                            className="bg-gray-600 hover:bg-gray-700"
                                        >
                                            確認移動檔案
                                        </Button>
                                        <Button
                                            onClick={cancelImport}
                                            variant="outline"
                                            disabled={isLoading}
                                        >
                                            取消
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {/* 完成狀態 */}
                            {currentSession.status === ImportStatus.COMPLETED && (
                                <div className="text-center">
                                    <div className="text-green-600 text-lg font-semibold">✅ 檔案匯入完成!</div>
                                    <p className="text-gray-600 mt-2">檔案已成功移動到: {currentSession.preview_final_path}</p>
                                </div>
                            )}

                            {/* 錯誤列表 */}
                            {currentSession.errors && currentSession.errors.length > 0 && (
                                <div className="bg-red-50 p-4 rounded border border-red-200">
                                    <h4 className="text-red-800 font-medium">錯誤訊息:</h4>
                                    <ul className="text-red-700 text-sm mt-2">
                                        {currentSession.errors.map((error, index) => (
                                            <li key={index}>• {error}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* 標籤編輯對話框 */}
            <Dialog open={showTagEditor} onOpenChange={setShowTagEditor}>
                <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
                    <DialogHeader>
                        <DialogTitle>編輯音樂標籤</DialogTitle>
                        <DialogDescription>
                            請編輯音樂標籤資訊，完成後點擊儲存繼續
                        </DialogDescription>
                    </DialogHeader>
                    {currentSession?.extracted_tags && (
                        <MusicImportTagEditor
                            filePath={currentSession.temp_path}
                            onSave={handleUpdateTags}
                            onCancel={() => setShowTagEditor(false)}
                            initialTags={currentSession.extracted_tags}
                        />
                    )}
                </DialogContent>
            </Dialog>

            {/* 歌手圖片上傳對話框 */}
            <Dialog open={showArtistImageDialog} onOpenChange={setShowArtistImageDialog}>
                <DialogContent>
                    <DialogHeader className="grid">
                        <DialogTitle>上傳歌手圖片</DialogTitle>
                        <DialogDescription>
                            歌手 &quot;{artistName}&quot; 的資料夾需要封面圖片，請上傳歌手圖片 (JPG/PNG 格式)，檔案將保存為 artist.jpg
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <input
                            type="file"
                            accept=".jpg,.jpeg,.png"
                            onChange={handleArtistImageUpload}
                            className="w-full p-2 border border-gray-300 rounded-md"
                        />
                        <div className="flex space-x-4 justify-end">
                            <Button
                                onClick={() => {
                                    setShowArtistImageDialog(false)
                                    // 跳過歌手圖片，直接處理專輯 - 使用當前狀態的值
                                    if (currentSession) {
                                        processAlbum(currentSession.file_id, artistName, albumName)
                                    }
                                }}
                                variant="outline"
                            >
                                跳過
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    )
}