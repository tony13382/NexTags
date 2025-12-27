'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ArrowRight, Save, Sparkles, X } from 'lucide-react'

interface TagEditorProps {
    filePath: string
    initialTags: Record<string, unknown>
    onSave: (tags: Record<string, unknown>) => void
    onCancel: () => void
}

export default function MusicImportTagEditor({ filePath, initialTags, onSave, onCancel }: TagEditorProps) {
    const [tags, setTags] = useState<Record<string, unknown>>(initialTags || {})
    const [loading, setLoading] = useState(false)
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
                                field.toLowerCase().includes('composer') ? 'composersort' :
                                    field.toLowerCase().includes('performer') ? 'performersort' : ''
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

                {/* 演奏者 */}
                <div className="flex items-end gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">演奏者</label>
                        <Input
                            value={String(tags.performer || '')}
                            onChange={(e) => handleInputChange('performer', e.target.value)}
                            placeholder="演奏者名稱"
                        />
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => convertToPinyin('performer')}
                        disabled={loading}
                        className="w-8 h-8 p-0"
                    >
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">排序演奏者</label>
                        <Input
                            value={String(tags.performersort || '')}
                            onChange={(e) => handleInputChange('performersort', e.target.value)}
                            placeholder="排序演奏者"
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

                {/* 碟片編號 */}
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">碟片編號</label>
                        <Input
                            value={String(tags.discnumber || '')}
                            onChange={(e) => handleInputChange('discnumber', e.target.value)}
                            placeholder="1"
                            type="number"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">碟片總數</label>
                        <Input
                            value={String(tags.disctotal || '')}
                            onChange={(e) => handleInputChange('disctotal', e.target.value)}
                            placeholder="2"
                            type="number"
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
                <Select
                    value={String(tags.language || '')}
                    onValueChange={(value) => handleInputChange('language', value)}
                >
                    <SelectTrigger className="w-full">
                        <SelectValue placeholder="請選擇語言" />
                    </SelectTrigger>
                    <SelectContent>
                        {Object.entries(languages).map(([code, name]) => (
                            <SelectItem key={code} value={code}>
                                {name}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
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

            {/* ReplayGain (自動生成，僅顯示) */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                    ReplayGain <span className="text-xs text-gray-500">(已在上傳時自動生成)</span>
                </label>
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
                        <Sparkles className='size-4' />
                        {loading ? '處理中...' : ''}
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