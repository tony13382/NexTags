'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { X, ArrowRight, Save, Upload, Image as ImageIcon, Search } from 'lucide-react';

interface Song {
  Title: string;
  Artist: string;
  Album: string;
  MainFolder: string;
  FilePath: string;
  Genre: string[];
  Language: string;
  Favorite: string;
  Cover: string;
  SortTitle?: string;
  SortArtist?: string;
  SortAlbum?: string;
  Lyrics?: string;
  Comment?: string;
  JfId?: string;
}

interface TagEditorProps {
  song: Song | null;
  onClose: () => void;
  onSave: (song: Song) => void;
}

export default function TagEditor({ song, onClose, onSave }: TagEditorProps) {
  const [editedSong, setEditedSong] = useState<Song | null>(null);
  const [loading, setLoading] = useState(false);
  const [languages, setLanguages] = useState<Record<string, string>>({});
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [coverImage, setCoverImage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (song) {
      setEditedSong({
        ...song,
        SortTitle: song.SortTitle || '',
        SortArtist: song.SortArtist || '',
        SortAlbum: song.SortAlbum || '',
        Lyrics: song.Lyrics || '',
        Comment: song.Comment || '',
        JfId: song.JfId || ''
      });
      // 設置封面圖片 - 使用 API 端點
      if (song.Cover) {
        const imageUrl = `/api/images/cover?path=${encodeURIComponent(song.Cover)}`;
        setCoverImage(imageUrl);
      } else {
        setCoverImage(null);
      }
    }
  }, [song]);

  useEffect(() => {
    // 載入語言清單和標籤清單
    const fetchLanguages = async () => {
      try {
        const response = await fetch('/api/tags/languages');
        if (response.ok) {
          const data = await response.json();
          setLanguages(data);
        }
      } catch (error) {
        console.error('Failed to load languages:', error);
      }
    };

    const fetchTags = async () => {
      try {
        const response = await fetch('/api/tags/tags');
        if (response.ok) {
          const data = await response.json();
          setAvailableTags(data);
        }
      } catch (error) {
        console.error('Failed to load tags:', error);
      }
    };

    fetchLanguages();
    fetchTags();
  }, []);

  if (!song || !editedSong) return null;

  const handleInputChange = (field: keyof Song, value: string | string[]) => {
    setEditedSong(prev => prev ? { ...prev, [field]: value } : null);
  };

  const handleImageClick = () => {
    fileInputRef.current?.click();
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        setCoverImage(result);
        // 更新編輯的歌曲資料中的封面路徑
        // 注意：這裡應該將圖片上傳到伺服器並獲得路徑，目前僅作為本地預覽
        handleInputChange('Cover', result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragOver(false);

    const files = event.dataTransfer.files;
    const file = files[0];

    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        setCoverImage(result);
        handleInputChange('Cover', result);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeCoverImage = () => {
    setCoverImage(null);
    handleInputChange('Cover', '');
  };

  const convertToPinyin = async (field: 'Title' | 'Artist' | 'Album') => {
    const sourceValue = editedSong[field];
    if (!sourceValue) return;

    setLoading(true);
    try {
      const response = await fetch('/api/tools/pinyin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: sourceValue })
      });

      const data = await response.json();

      if (response.ok && data.result) {
        const sortField = `Sort${field}` as keyof Song;
        handleInputChange(sortField, data.result);
      }
    } catch (error) {
      console.error('Pinyin conversion failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const autoMatchJellyfinId = async () => {
    if (!editedSong?.Title || !editedSong?.Artist || !editedSong?.Album) {
      console.warn('需要標題、藝術家和專輯資訊才能進行自動匹配');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`/api/jellyfin/songs?title=${encodeURIComponent(editedSong.Title)}&artist=${encodeURIComponent(editedSong.Artist)}&album=${encodeURIComponent(editedSong.Album)}&limit=1`);

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.songs && data.songs.length > 0) {
          const jellyfinId = data.songs[0].Id;
          handleInputChange('JfId', jellyfinId);
          console.log('自動匹配成功，Jellyfin ID:', jellyfinId);
        } else {
          console.warn('未找到匹配的 Jellyfin 歌曲');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('Jellyfin 搜尋失敗:', response.status, response.statusText, errorData);
      }
    } catch (error) {
      console.error('自動匹配 Jellyfin ID 失敗:', error);
    } finally {
      setLoading(false);
    }
  };

  const processLyrics = async () => {
    if (!editedSong?.Lyrics) return;

    setLoading(true);
    try {
      const response = await fetch('/api/tools/lyric', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lyric: editedSong.Lyrics })
      });

      const data = await response.json();

      if (response.ok && data.result) {
        handleInputChange('Lyrics', data.result);
      }
    } catch (error) {
      console.error('Lyric processing failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTagToggle = (tag: string) => {
    if (!editedSong) return;

    const currentGenres = editedSong.Genre || [];
    const isSelected = currentGenres.includes(tag);

    let newGenres: string[];
    if (isSelected) {
      // 移除標籤
      newGenres = currentGenres.filter(genre => genre !== tag);
    } else {
      // 添加標籤
      newGenres = [...currentGenres, tag];
    }

    handleInputChange('Genre', newGenres);
  };

  const handleSave = () => {
    if (editedSong) {
      onSave(editedSong);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end backdrop-blur-md"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }}
    >
      <div className="bg-white w-128 h-full shadow-xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b bg-white">
          <h2 className="text-lg font-semibold">編輯標籤</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          <div className="border p-4 rounded-xl bg-white">
            <h3 className="font-medium text-gray-900 mb-3">Path</h3>
            <label className="text-sm text-gray-500 block mb-1">{editedSong.FilePath}</label>
          </div>
          <div className="border p-4 rounded-xl bg-white gap-2">
            <div
              className={`aspect-square max-w-[240px] shadow-lg mx-auto rounded-2xl cursor-pointer transition-all duration-200 ${isDragOver
                ? 'border-2 border-dashed border-blue-400 bg-blue-50'
                : 'bg-gray-500 hover:bg-gray-400'
                }`}
              onClick={handleImageClick}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {coverImage ? (
                <div className="relative w-full h-full">
                  <img
                    src={coverImage}
                    alt="Album Cover"
                    className="w-full h-full object-cover rounded-2xl"
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeCoverImage();
                    }}
                    className="absolute top-2 right-2 bg-gray-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-white">
                  {isDragOver ? (
                    <>
                      <Upload className="h-12 w-12 mb-2" />
                      <span className="text-sm font-medium text-blue-600">拖放圖片到此處</span>
                    </>
                  ) : (
                    <>
                      <ImageIcon className="h-12 w-12 mb-2" />
                      <span className="text-sm font-medium">點擊上傳封面</span>
                    </>
                  )}
                </div>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              className="hidden"
            />
            <label className="text-xs text-center text-gray-500 block mt-2">
              {coverImage ? '點擊更換圖片或拖放新圖片' : '點擊圖片上傳或拖放圖片'}
            </label>
          </div>
          <div className="border p-4 rounded-xl bg-white grid gap-4">
            <div className="flex items-end bg-white rounded-lg gap-4">
              <div>
                <label className="text-gray-500 block mb-1">Title</label>
                <Input
                  value={editedSong.Title}
                  onChange={(e) => handleInputChange('Title', e.target.value)}
                  placeholder="歌曲標題"
                />
              </div>
              <div className="col-auto flex justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => convertToPinyin('Title')}
                  disabled={loading}
                  className="w-8 h-8 p-0"
                >
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
              <div>
                <label className="text-gray-500 block mb-1">SortTitle</label>
                <Input
                  value={editedSong.SortTitle || ''}
                  onChange={(e) => handleInputChange('SortTitle', e.target.value)}
                  placeholder="排序標題"
                />
              </div>
            </div>
            <div className="flex items-end bg-white rounded-lg gap-4">
              <div>
                <label className="text-gray-500 block mb-1">Artist</label>
                <Input
                  value={editedSong.Artist}
                  onChange={(e) => handleInputChange('Artist', e.target.value)}
                  placeholder="藝術家"
                />
              </div>
              <div className="flex justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => convertToPinyin('Artist')}
                  disabled={loading}
                  className="w-8 h-8 p-0"
                >
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
              <div>
                <label className="text-gray-500 block mb-1">SortArtist</label>
                <Input
                  value={editedSong.SortArtist || ''}
                  onChange={(e) => handleInputChange('SortArtist', e.target.value)}
                  placeholder="排序藝術家"
                />
              </div>
            </div>
            <div className="flex items-end bg-white rounded-lg gap-4">
              <div>
                <label className="text-gray-500 block mb-1">Album</label>
                <Input
                  value={editedSong.Album}
                  onChange={(e) => handleInputChange('Album', e.target.value)}
                  placeholder="專輯名稱"
                />
              </div>
              <div className="flex justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => convertToPinyin('Album')}
                  disabled={loading}
                  className="w-8 h-8 p-0"
                >
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
              <div>
                <label className="text-gray-500 block mb-1">SortAlbum</label>
                <Input
                  value={editedSong.SortAlbum || ''}
                  onChange={(e) => handleInputChange('SortAlbum', e.target.value)}
                  placeholder="排序專輯"
                />
              </div>
            </div>
            <div>
              <label className="text-gray-500 block mb-3">Genre</label>
              <div className="flex flex-wrap gap-2">
                {availableTags.map((tag) => {
                  const isSelected = editedSong.Genre?.includes(tag) || false;
                  return (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => handleTagToggle(tag)}
                      className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${isSelected
                        ? 'bg-gray-800 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <label className="text-gray-500 block mb-1">Language</label>
              <select
                value={editedSong.Language}
                onChange={(e) => handleInputChange('Language', e.target.value)}
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
            <div>
              <label className="text-gray-500 block mb-1">Favorite</label>
              <select
                value={editedSong.Favorite}
                onChange={(e) => handleInputChange('Favorite', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="False">否</option>
                <option value="True">是</option>
              </select>
            </div>
            <div>
              <label className="text-gray-500 block mb-1">備註 (Comment)</label>
              <textarea
                value={editedSong.Comment || ''}
                onChange={(e) => handleInputChange('Comment', e.target.value)}
                placeholder="輸入備註或評論..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
              />
            </div>
            <div className="flex items-end bg-white rounded-lg gap-4">
              <div className="flex-1">
                <label className="text-gray-500 block mb-1">Jellyfin ID</label>
                <Input
                  value={editedSong.JfId || ''}
                  onChange={(e) => handleInputChange('JfId', e.target.value)}
                  placeholder="輸入 Jellyfin ID..."
                />
              </div>
              <div className="flex justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={autoMatchJellyfinId}
                  disabled={loading || !editedSong.Title || !editedSong.Artist || !editedSong.Album}
                  className="w-auto h-9 px-3"
                  title="根據標題、藝術家和專輯自動匹配 Jellyfin ID"
                >
                  <Search className="h-4 w-4 mr-1" />
                  自動匹配
                </Button>
              </div>
            </div>
          </div>
          {/* Other Fields */}
          <div className="bg-white rounded-lg border p-4 space-y-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-gray-500">歌詞 (Lyrics)</label>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={processLyrics}
                  disabled={loading || !editedSong.Lyrics}
                  className="text-xs"
                >
                  處理歌詞
                </Button>
              </div>
              <textarea
                value={editedSong.Lyrics || ''}
                onChange={(e) => handleInputChange('Lyrics', e.target.value)}
                placeholder="輸入歌詞..."
                rows={12}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
              />
            </div>
          </div>
        </div>

        <div className="p-4 border-t bg-white">
          <Button onClick={handleSave} className="w-full flex items-center gap-2">
            <Save className="h-4 w-4" />
            保存變更
          </Button>
        </div>
      </div>
    </div>
  );
}