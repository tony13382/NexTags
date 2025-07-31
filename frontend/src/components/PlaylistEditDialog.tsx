'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose, DialogFooter } from '@/components/ui/dialog';
import { Save } from 'lucide-react';

interface SmartPlaylist {
    name: string;
    base_folder: string;
    filter_tags: string[];
    filter_language: string | null;
    filter_favorites: boolean | null;
    jellyfin_playlist_id: string;
    filter_tags_display: string[];
    filter_language_display: string;
    filter_favorites_display: string;
}

interface PlaylistEditDialogProps {
    playlist: SmartPlaylist | null;
    playlistIndex: number | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSave: (index: number | null, updatedPlaylist: Partial<SmartPlaylist>) => void;
    isCreate?: boolean;
}

export default function PlaylistEditDialog({
    playlist,
    playlistIndex,
    open,
    onOpenChange,
    onSave,
    isCreate = false
}: PlaylistEditDialogProps) {
    const [editedPlaylist, setEditedPlaylist] = useState<Partial<SmartPlaylist>>({});
    const [loading, setLoading] = useState(false);
    const [languages, setLanguages] = useState<Record<string, string>>({});
    const [availableTags, setAvailableTags] = useState<string[]>([]);
    const [baseFolders, setBaseFolders] = useState<string[]>([]);

    useEffect(() => {
        if (open) {
            if (playlist) {
                // 編輯模式
                setEditedPlaylist({
                    name: playlist.name,
                    base_folder: playlist.base_folder,
                    filter_tags: [...(playlist.filter_tags || [])],
                    filter_language: playlist.filter_language,
                    filter_favorites: playlist.filter_favorites,
                    jellyfin_playlist_id: playlist.jellyfin_playlist_id || ''
                });
            } else {
                // 新增模式
                setEditedPlaylist({
                    name: '',
                    base_folder: '',
                    filter_tags: [],
                    filter_language: null,
                    filter_favorites: null,
                    jellyfin_playlist_id: ''
                });
            }
        }
    }, [playlist, open, isCreate]);

    useEffect(() => {
        if (open) {
            // 載入語言清單和標籤清單
            const fetchData = async () => {
                try {
                    // 載入語言清單
                    const languagesResponse = await fetch('/api/tags/languages');
                    if (languagesResponse.ok) {
                        const languagesData = await languagesResponse.json();
                        setLanguages(languagesData);
                    }

                    // 載入標籤清單
                    const tagsResponse = await fetch('/api/tags/tags');
                    if (tagsResponse.ok) {
                        const tagsData = await tagsResponse.json();
                        setAvailableTags(tagsData);
                    }

                    // 載入基礎資料夾清單
                    const baseFoldersResponse = await fetch('/api/tags/baseFolders');
                    if (baseFoldersResponse.ok) {
                        const baseFoldersData = await baseFoldersResponse.json();
                        setBaseFolders(baseFoldersData);
                    }

                } catch (error) {
                    console.error('Failed to load data:', error);
                }
            };

            fetchData();
        }
    }, [open]);

    const handleInputChange = (field: keyof SmartPlaylist, value: string | string[] | boolean | null) => {
        setEditedPlaylist(prev => ({ ...prev, [field]: value }));
    };

    const handleTagToggle = (tag: string) => {
        const currentTags = editedPlaylist.filter_tags || [];
        const isSelected = currentTags.includes(tag);

        let newTags: string[];
        if (isSelected) {
            newTags = currentTags.filter(t => t !== tag);
        } else {
            newTags = [...currentTags, tag];
        }

        handleInputChange('filter_tags', newTags);
    };

    const handleSave = async () => {
        // 驗證必填欄位
        if (!editedPlaylist.name || !editedPlaylist.base_folder) {
            return;
        }

        setLoading(true);
        try {
            onSave(playlistIndex, editedPlaylist);
            onOpenChange(false);
        } catch (error) {
            console.error('Failed to save playlist:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        onOpenChange(false);
        setEditedPlaylist({});
    };

    // 移除這個限制，因為新增模式時 playlist 是 null

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>{isCreate ? '新增播放清單' : '播放清單編輯'}</DialogTitle>
                    <DialogClose onClose={handleClose} />
                </DialogHeader>

                <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                    {/* 播放清單名稱 */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">Title</label>
                        <Input
                            value={editedPlaylist.name || ''}
                            onChange={(e) => handleInputChange('name', e.target.value)}
                            placeholder="播放清單名稱"
                        />
                    </div>

                    {/* Jellyfin Playlist ID */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">Jellyfin Playlist Id</label>
                        <Input
                            value={editedPlaylist.jellyfin_playlist_id || ''}
                            onChange={(e) => handleInputChange('jellyfin_playlist_id', e.target.value)}
                            placeholder="Jellyfin 播放清單 ID"
                            className="font-mono text-sm"
                        />
                    </div>

                    {/* BaseFolder */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">BaseFolder</label>
                        <select
                            value={editedPlaylist.base_folder || ''}
                            onChange={(e) => handleInputChange('base_folder', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">選擇基礎資料夾</option>
                            {baseFolders.map((folder) => (
                                <option key={folder} value={folder}>
                                    {folder}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Tags / Genre (標籤) */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-3">Tags / Genre (標籤)</label>
                        <div className="flex flex-wrap gap-2">
                            {availableTags.map((tag) => {
                                const isSelected = editedPlaylist.filter_tags?.includes(tag) || false;
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

                    {/* Language */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">Language</label>
                        <select
                            value={editedPlaylist.filter_language || ''}
                            onChange={(e) => handleInputChange('filter_language', e.target.value || null)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">不設定</option>
                            {Object.entries(languages).map(([code, name]) => (
                                <option key={code} value={code}>
                                    {name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Favorites */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">Favorites</label>
                        <select
                            value={editedPlaylist.filter_favorites === null || editedPlaylist.filter_favorites === undefined ? '' : editedPlaylist.filter_favorites.toString()}
                            onChange={(e) => {
                                const value = e.target.value;
                                if (value === '') {
                                    handleInputChange('filter_favorites', null);
                                } else {
                                    handleInputChange('filter_favorites', value === 'true');
                                }
                            }}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">不設定</option>
                            <option value="true">是</option>
                            <option value="false">否</option>
                        </select>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleClose} disabled={loading}>
                        取消
                    </Button>
                    <Button onClick={handleSave} disabled={loading} className="flex items-center gap-2">
                        <Save className="w-4 h-4" />
                        {loading ? '儲存中...' : 'Save'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}