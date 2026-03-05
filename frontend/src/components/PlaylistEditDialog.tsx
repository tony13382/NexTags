'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Info, Save } from 'lucide-react';

interface SmartPlaylist {
    name: string;
    base_folder: string;
    filter_tags: string[];
    exclude_tags: string[];
    filter_language: string[];
    exclude_language: string[];
    filter_favorites: boolean | null;
    sort_method: string;
    is_system_level: boolean;
    filter_tags_display: string[];
    exclude_tags_display: string[];
    filter_language_display: string[];
    exclude_language_display: string[];
    filter_favorites_display: string;
    sort_method_display: string;
}

interface PlaylistEditDialogProps {
    playlist: SmartPlaylist | null;
    playlistId: number | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSave: (id: number | null, updatedPlaylist: Partial<SmartPlaylist>) => void;
    isCreate?: boolean;
}

export default function PlaylistEditDialog({
    playlist,
    playlistId,
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
                    exclude_tags: [...(playlist.exclude_tags || [])],
                    filter_language: [...(playlist.filter_language || [])],
                    exclude_language: [...(playlist.exclude_language || [])],
                    filter_favorites: playlist.filter_favorites,
                    sort_method: playlist.sort_method || 'creation_time',
                    is_system_level: playlist.is_system_level ?? false
                });
            } else {
                // 新增模式
                setEditedPlaylist({
                    name: '',
                    base_folder: '',
                    filter_tags: [],
                    exclude_tags: [],
                    filter_language: [],
                    exclude_language: [],
                    filter_favorites: null,
                    sort_method: 'creation_time',
                    is_system_level: false
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
                        setBaseFolders(baseFoldersData.base_folders || []);
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

    const handleLanguageToggle = (code: string) => {
        const current = editedPlaylist.filter_language || [];
        const isSelected = current.includes(code);
        const updated = isSelected ? current.filter(c => c !== code) : [...current, code];
        handleInputChange('filter_language', updated);
    };

    const handleExcludeLanguageToggle = (code: string) => {
        const current = editedPlaylist.exclude_language || [];
        const isSelected = current.includes(code);
        const updated = isSelected ? current.filter(c => c !== code) : [...current, code];
        handleInputChange('exclude_language', updated);
    };

    const handleExcludeTagToggle = (tag: string) => {
        const currentTags = editedPlaylist.exclude_tags || [];
        const isSelected = currentTags.includes(tag);

        let newTags: string[];
        if (isSelected) {
            newTags = currentTags.filter(t => t !== tag);
        } else {
            newTags = [...currentTags, tag];
        }

        handleInputChange('exclude_tags', newTags);
    };

    const handleSave = async () => {
        // 驗證必填欄位
        if (!editedPlaylist.name || !editedPlaylist.base_folder) {
            return;
        }

        setLoading(true);
        try {
            onSave(playlistId, editedPlaylist);
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
                <DialogHeader className='p-2 pb-0'>
                    <DialogTitle>{isCreate ? '新增播放清單' : '播放清單編輯'}</DialogTitle>
                    <DialogClose onClose={handleClose} />
                </DialogHeader>

                <div className="space-y-4 max-h-[60vh] overflow-y-auto px-2">
                    {/* 播放清單名稱 */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">Title</label>
                        <Input
                            value={editedPlaylist.name || ''}
                            onChange={(e) => handleInputChange('name', e.target.value)}
                            placeholder="播放清單名稱"
                        />
                    </div>


                    {/* BaseFolder */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">BaseFolder</label>
                        <Select
                            value={editedPlaylist.base_folder || ''}
                            onValueChange={(value) => handleInputChange('base_folder', value)}
                        >
                            <SelectTrigger className="w-full">
                                <SelectValue placeholder="選擇基礎資料夾" />
                            </SelectTrigger>
                            <SelectContent>
                                {baseFolders.map((folder) => (
                                    <SelectItem key={folder} value={folder}>
                                        {folder}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Tags / Genre (標籤) */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-3">Tags / Genre (標籤)</label>
                        <div className="flex flex-wrap gap-2">
                            {availableTags
                                .filter(tag => !editedPlaylist.exclude_tags?.includes(tag))
                                .map((tag) => {
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
                        {availableTags.filter(tag => !editedPlaylist.exclude_tags?.includes(tag)).length === 0 && (
                            <p className="text-sm text-gray-500 mt-2">所有標籤都已在「Exclude Tags」中被選擇</p>
                        )}
                    </div>

                    {/* Exclude Tags (排除標籤) */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-3">Exclude Tags (排除標籤)</label>
                        <div className="flex flex-wrap gap-2">
                            {availableTags
                                .filter(tag => !editedPlaylist.filter_tags?.includes(tag))
                                .map((tag) => {
                                    const isSelected = editedPlaylist.exclude_tags?.includes(tag) || false;
                                    return (
                                        <button
                                            key={tag}
                                            type="button"
                                            onClick={() => handleExcludeTagToggle(tag)}
                                            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${isSelected
                                                ? 'bg-red-600 text-white'
                                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                }`}
                                        >
                                            {tag}
                                        </button>
                                    );
                                })}
                        </div>
                        {availableTags.filter(tag => !editedPlaylist.filter_tags?.includes(tag)).length === 0 && (
                            <p className="text-sm text-gray-500 mt-2">所有標籤都已在「Tags / Genre」中被選擇</p>
                        )}
                    </div>

                    {/* Language (語言) */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-3">Language (語言)</label>
                        <div className="flex flex-wrap gap-2">
                            {Object.entries(languages)
                                .filter(([code]) => !editedPlaylist.exclude_language?.includes(code))
                                .map(([code, name]) => {
                                    const isSelected = editedPlaylist.filter_language?.includes(code) || false;
                                    return (
                                        <button
                                            key={code}
                                            type="button"
                                            onClick={() => handleLanguageToggle(code)}
                                            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${isSelected
                                                ? 'bg-green-700 text-white'
                                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                }`}
                                        >
                                            {name}
                                        </button>
                                    );
                                })}
                        </div>
                        {Object.keys(languages).filter(code => !editedPlaylist.exclude_language?.includes(code)).length === 0 && (
                            <p className="text-sm text-gray-500 mt-2">所有語言都已在「Exclude Language」中被選擇</p>
                        )}
                    </div>

                    {/* Exclude Language (排除語言) */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-3">Exclude Language (排除語言)</label>
                        <div className="flex flex-wrap gap-2">
                            {Object.entries(languages)
                                .filter(([code]) => !editedPlaylist.filter_language?.includes(code))
                                .map(([code, name]) => {
                                    const isSelected = editedPlaylist.exclude_language?.includes(code) || false;
                                    return (
                                        <button
                                            key={code}
                                            type="button"
                                            onClick={() => handleExcludeLanguageToggle(code)}
                                            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${isSelected
                                                ? 'bg-red-600 text-white'
                                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                }`}
                                        >
                                            {name}
                                        </button>
                                    );
                                })}
                        </div>
                        {Object.keys(languages).filter(code => !editedPlaylist.filter_language?.includes(code)).length === 0 && (
                            <p className="text-sm text-gray-500 mt-2">所有語言都已在「Language」中被選擇</p>
                        )}
                    </div>

                    {/* Favorites */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">Favorites</label>
                        <Select
                            value={editedPlaylist.filter_favorites === null || editedPlaylist.filter_favorites === undefined ? 'NONE' : editedPlaylist.filter_favorites.toString()}
                            onValueChange={(value) => {
                                if (value === 'NONE') {
                                    handleInputChange('filter_favorites', null);
                                } else {
                                    handleInputChange('filter_favorites', value === 'true');
                                }
                            }}
                        >
                            <SelectTrigger className="w-full">
                                <SelectValue placeholder="不設定" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="NONE">不設定</SelectItem>
                                <SelectItem value="true">是</SelectItem>
                                <SelectItem value="false">否</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Sort Method */}
                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">Sort Method (排序方式)</label>
                        <Select
                            value={editedPlaylist.sort_method || 'creation_time'}
                            onValueChange={(value) => handleInputChange('sort_method', value)}
                        >
                            <SelectTrigger className="w-full">
                                <SelectValue placeholder="選擇排序方式" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="creation_time">檔案建立時間 (File Creation Time)</SelectItem>
                                <SelectItem value="title">標題 (TitleSort)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* System Level Playlist */}
                    <div className="flex flex-col gap-2 pb-4">
                        <div className="flex items-center gap-2">
                            <label className="text-sm font-medium text-gray-700">系統等級播放清單</label>
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Info className="h-4 w-4 text-gray-400 cursor-help" />
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        <div className="text-sm">
                                            <p><strong>開啟：</strong>存入 /Music/Playlist</p>
                                            <p><strong>關閉：</strong>存入 /Music/{editedPlaylist.base_folder || '音樂資料夾'}/Playlist</p>
                                        </div>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        </div>
                        <Switch
                            checked={editedPlaylist.is_system_level ?? false}
                            onCheckedChange={(checked) => handleInputChange('is_system_level', checked)}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleClose} disabled={loading} className='flex-1'>
                        取消
                    </Button>
                    <Button onClick={handleSave} disabled={loading} className="flex-1 flex items-center gap-2">
                        <Save className="w-4 h-4" />
                        {loading ? '儲存中...' : 'Save'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}