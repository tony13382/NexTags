'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ArrowRight, Save, X } from 'lucide-react'

interface TagEditorProps {
    filePath: string
    initialTags: Record<string, unknown>
    onSave: (tags: Record<string, unknown>) => void
    onCancel: () => void
}

export default function MusicImportTagEditor({ filePath, initialTags, onSave, onCancel }: TagEditorProps) {
    const [tags, setTags] = useState<Record<string, unknown>>(initialTags || {})
    const [loading, setLoading] = useState(false)
    const [generatingReplayGain, setGeneratingReplayGain] = useState(false)
    const [languages, setLanguages] = useState<Record<string, string>>({})
    const [availableTags, setAvailableTags] = useState<string[]>([])

    useEffect(() => {
        setTags(initialTags || {})
    }, [initialTags])

    useEffect(() => {
        // 載入語言清單和標籤清單
        const fetchLanguages = async () => {
            try {
                const response = await fetch('/api/tags/languages')
                if (response.ok) {
                    const data = await response.json()
                    setLanguages(data)
                }
            } catch (error) {
                console.error('Failed to load languages:', error)
            }
        }

        const fetchTags = async () => {
            try {
                const response = await fetch('/api/tags/tags')
                if (response.ok) {
                    const data = await response.json()
                    setAvailableTags(data)
                }
            } catch (error) {
                console.error('Failed to load tags:', error)
            }
        }

        fetchLanguages()
        fetchTags()
    }, [])

    const handleInputChange = (field: string, value: string | string[]) => {
        setTags((prev: Record<string, unknown>) => ({
            ...prev,
            [field]: value
        }))
    }

    const convertToPinyin = async (field: string) => {
        const sourceValue = tags[field]
        if (!sourceValue) return

        setLoading(true)
        try {
            const response = await fetch('/api/tools/pinyin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: sourceValue })
            })

            const data = await response.json()

            if (response.ok && data.result) {
                const sortField = field.toLowerCase().includes('title') ? 'titlesort' :
                    field.toLowerCase().includes('artist') && !field.toLowerCase().includes('album') ? 'artistsort' :
                        field.toLowerCase().includes('album') && !field.toLowerCase().includes('artist') ? 'albumsort' :
                            field.toLowerCase().includes('albumartist') ? 'albumartistsort' :
                                field.toLowerCase().includes('composer') ? 'composersort' : ''
                if (sortField) {
                    handleInputChange(sortField, data.result)
                }
            }
        } catch (error) {
            console.error('Pinyin conversion failed:', error)
        } finally {
            setLoading(false)
        }
    }

    const processLyrics = async () => {
        if (!tags.lyrics) return

        setLoading(true)
        try {
            const response = await fetch('/api/tools/lyric', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lyric: tags.lyrics })
            })

            const data = await response.json()

            if (response.ok && data.result) {
                handleInputChange('lyrics', data.result)
            }
        } catch (error) {
            console.error('Lyric processing failed:', error)
        } finally {
            setLoading(false)
        }
    }

    const generateReplayGain = async () => {
        if (!filePath) return

        setGeneratingReplayGain(true)
        try {
            const response = await fetch('/api/audios/replaygain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            })

            const data = await response.json()

            if (response.ok && data.success) {
                alert('ReplayGain 生成成功！標籤已更新。')
                // 重新讀取檔案標籤以獲取新的 ReplayGain 值
                const tagsResponse = await fetch('/api/audios', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: filePath })
                })

                if (tagsResponse.ok) {
                    const tagsData = await tagsResponse.json()
                    if (tagsData.tags) {
                        handleInputChange('replaygain_track_gain', tagsData.tags.replaygain_track_gain || '')
                        handleInputChange('replaygain_track_peak', tagsData.tags.replaygain_track_peak || '')
                    }
                }
            } else {
                alert(`ReplayGain 生成失敗: ${data.message || '未知錯誤'}`)
            }
        } catch (error) {
            console.error('ReplayGain generation failed:', error)
            alert('生成 ReplayGain 時發生錯誤')
        } finally {
            setGeneratingReplayGain(false)
        }
    }

    const handleGenreToggle = (tag: string) => {
        const currentGenres = Array.isArray(tags.genre) ? tags.genre : []
        const isSelected = currentGenres.includes(tag)

        let newGenres: string[]
        if (isSelected) {
            newGenres = currentGenres.filter((genre: string) => genre !== tag)
        } else {
            newGenres = [...currentGenres, tag]
        }

        handleInputChange('genre', newGenres)
    }

    const handleSave = () => {
        onSave(tags)
    }

    return (
        <div className="space-y-6">
            <div className="text-sm text-gray-600">
                檔案路徑: {filePath}
            </div>

            {/* 基本資訊 */}
            <div className="space-y-4">
                <h3 className="text-lg font-semibold">基本資訊</h3>

                {/* 標題 */}
                <div className="flex items-end gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">標題</label>
                        <Input
                            value={String(tags.title || '')}
                            onChange={(e) => handleInputChange('title', e.target.value)}
                            placeholder="歌曲標題"
                        />
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => convertToPinyin('title')}
                        disabled={loading}
                        className="w-8 h-8 p-0"
                    >
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">排序標題</label>
                        <Input
                            value={String(tags.titlesort || '')}
                            onChange={(e) => handleInputChange('titlesort', e.target.value)}
                            placeholder="排序標題"
                        />
                    </div>
                </div>

                {/* 歌手 */}
                <div className="flex items-end gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">歌手</label>
                        <Input
                            value={String(tags.artist || '')}
                            onChange={(e) => handleInputChange('artist', e.target.value)}
                            placeholder="歌手名稱"
                        />
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => convertToPinyin('artist')}
                        disabled={loading}
                        className="w-8 h-8 p-0"
                    >
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">排序歌手</label>
                        <Input
                            value={String(tags.artistsort || '')}
                            onChange={(e) => handleInputChange('artistsort', e.target.value)}
                            placeholder="排序歌手"
                        />
                    </div>
                </div>

                {/* 專輯 */}
                <div className="flex items-end gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">專輯</label>
                        <Input
                            value={String(tags.album || '')}
                            onChange={(e) => handleInputChange('album', e.target.value)}
                            placeholder="專輯名稱"
                        />
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => convertToPinyin('album')}
                        disabled={loading}
                        className="w-8 h-8 p-0"
                    >
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">排序專輯</label>
                        <Input
                            value={String(tags.albumsort || '')}
                            onChange={(e) => handleInputChange('albumsort', e.target.value)}
                            placeholder="排序專輯"
                        />
                    </div>
                </div>

                {/* 專輯歌手 */}
                <div className="flex items-end gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">專輯歌手</label>
                        <Input
                            value={String(tags.albumartist || '')}
                            onChange={(e) => handleInputChange('albumartist', e.target.value)}
                            placeholder="專輯歌手名稱"
                        />
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => convertToPinyin('albumartist')}
                        disabled={loading}
                        className="w-8 h-8 p-0"
                    >
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">排序專輯歌手</label>
                        <Input
                            value={String(tags.albumartistsort || '')}
                            onChange={(e) => handleInputChange('albumartistsort', e.target.value)}
                            placeholder="排序專輯歌手"
                        />
                    </div>
                </div>

                {/* 作曲家 */}
                <div className="flex items-end gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">作曲家</label>
                        <Input
                            value={String(tags.composer || '')}
                            onChange={(e) => handleInputChange('composer', e.target.value)}
                            placeholder="作曲家名稱"
                        />
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => convertToPinyin('composer')}
                        disabled={loading}
                        className="w-8 h-8 p-0"
                    >
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">排序作曲家</label>
                        <Input
                            value={String(tags.composersort || '')}
                            onChange={(e) => handleInputChange('composersort', e.target.value)}
                            placeholder="排序作曲家"
                        />
                    </div>
                </div>

                {/* 軌道編號 */}
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">軌道編號</label>
                        <Input
                            value={String(tags.tracknumber || '')}
                            onChange={(e) => handleInputChange('tracknumber', e.target.value)}
                            placeholder="01"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">總軌道數</label>
                        <Input
                            value={String(tags.totaltracks || '')}
                            onChange={(e) => handleInputChange('totaltracks', e.target.value)}
                            placeholder="12"
                        />
                    </div>
                </div>
            </div>

            {/* 流派標籤 */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">流派標籤</label>
                <div className="flex flex-wrap gap-2">
                    {availableTags.map((tag) => {
                        const currentGenres = Array.isArray(tags.genre) ? tags.genre : []
                        const isSelected = currentGenres.includes(tag)
                        return (
                            <button
                                key={tag}
                                type="button"
                                onClick={() => handleGenreToggle(tag)}
                                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${isSelected
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                            >
                                {tag}
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* 語言 */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">語言</label>
                <select
                    value={String(tags.language || '')}
                    onChange={(e) => handleInputChange('language', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                    <option value="">請選擇語言</option>
                    {Object.entries(languages).map(([code, name]) => (
                        <option key={code} value={code}>
                            {name}
                        </option>
                    ))}
                </select>
            </div>

            {/* 備註 */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">備註</label>
                <textarea
                    value={String(tags.comment || '')}
                    onChange={(e) => handleInputChange('comment', e.target.value)}
                    placeholder="輸入備註..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
                />
            </div>

            {/* ReplayGain */}
            <div>
                <div className="flex items-center justify-between mb-3">
                    <label className="block text-sm font-medium text-gray-700">ReplayGain</label>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={generateReplayGain}
                        disabled={generatingReplayGain}
                        className="text-xs"
                    >
                        {generatingReplayGain ? '生成中...' : '計算 ReplayGain'}
                    </Button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-500 mb-1">Track Gain</label>
                        <Input
                            value={String(tags.replaygain_track_gain || '')}
                            readOnly
                            placeholder="未設定"
                            className="bg-gray-50"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-500 mb-1">Track Peak</label>
                        <Input
                            value={String(tags.replaygain_track_peak || '')}
                            readOnly
                            placeholder="未設定"
                            className="bg-gray-50"
                        />
                    </div>
                </div>
            </div>

            {/* 歌詞 */}
            <div>
                <div className="flex items-center justify-between mb-1">
                    <label className="block text-sm font-medium text-gray-700">歌詞</label>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={processLyrics}
                        disabled={loading || !tags.lyrics}
                        className="text-xs"
                    >
                        處理歌詞
                    </Button>
                </div>
                <textarea
                    value={String(tags.lyrics || '')}
                    onChange={(e) => handleInputChange('lyrics', e.target.value)}
                    placeholder="輸入歌詞..."
                    rows={8}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
                />
            </div>

            {/* 按鈕 */}
            <div className="flex space-x-4 justify-end">
                <Button onClick={handleSave} className="flex items-center gap-2">
                    <Save className="h-4 w-4" />
                    儲存標籤
                </Button>
                <Button onClick={onCancel} variant="outline" className="flex items-center gap-2">
                    <X className="h-4 w-4" />
                    取消
                </Button>
            </div>
        </div>
    )
}