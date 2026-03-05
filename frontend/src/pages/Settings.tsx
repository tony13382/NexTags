import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { FolderInput, Languages, Tag, Trash2, Download, Upload, Settings as SettingsIcon, GripVertical } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

function SortableTagItem({
  id,
  tag,
  index,
  onChange,
  onDelete,
}: {
  id: string;
  tag: string;
  index: number;
  onChange: (index: number, value: string) => void;
  onDelete: (index: number) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="flex items-center gap-2">
      <button type="button" className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 touch-none" {...attributes} {...listeners}>
        <GripVertical className="size-4" />
      </button>
      <input
        type="text"
        value={tag}
        onChange={(e) => onChange(index, e.target.value)}
        className="flex-1 px-3 py-2 border rounded"
      />
      <button
        onClick={() => onDelete(index)}
        className="px-3 py-2 text-gray-500 hover:text-red-500 rounded"
      >
        <Trash2 className="size-4" />
      </button>
    </div>
  );
}

interface Config {
  supported_tags: string[];
  supported_languages: { [key: string]: string };
  allow_folders: string[];
}

export default function Settings() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // 編輯狀態
  const [editingTags, setEditingTags] = useState<string[]>([]);
  const [editingLanguages, setEditingLanguages] = useState<{ [key: string]: string }>({});
  const [editingFolders, setEditingFolders] = useState<string[]>([]);

  // 新增項目的輸入框
  const [newTag, setNewTag] = useState('');
  const [newLangCode, setNewLangCode] = useState('');
  const [newLangName, setNewLangName] = useState('');
  const [newFolder, setNewFolder] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const tagIds = editingTags.map((_, i) => `tag-${i}`);

  const handleTagDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = tagIds.indexOf(active.id as string);
      const newIndex = tagIds.indexOf(over.id as string);
      setEditingTags(arrayMove(editingTags, oldIndex, newIndex));
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const result = await api.get('config/');
      if (result.success) {
        // 提供默認值，處理空配置的情況
        const configData = {
          supported_tags: result.data.supported_tags || [],
          supported_languages: result.data.supported_languages || {},
          allow_folders: result.data.allow_folders || []
        };
        setConfig(configData);
        setEditingTags(configData.supported_tags);
        setEditingLanguages(configData.supported_languages);
        setEditingFolders(configData.allow_folders);
      }
    } catch (error) {
      console.error('Failed to fetch config:', error);
      toast.error('載入設定失敗');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);

    try {
      // 更新 supported_tags
      await api.post('config/', {
        config_key: 'supported_tags',
        config_value: editingTags,
        description: '支援的標籤列表'
      });

      // 更新 supported_languages
      await api.post('config/', {
        config_key: 'supported_languages',
        config_value: editingLanguages,
        description: '支援的語言代碼對應'
      });

      // 更新 allow_folders
      await api.post('config/', {
        config_key: 'allow_folders',
        config_value: editingFolders,
        description: '允許的音樂資料夾'
      });

      toast.success('設定已儲存');
      await fetchConfig();
    } catch (error) {
      console.error('Failed to save config:', error);
      toast.error('儲存設定失敗');
    } finally {
      setSaving(false);
    }
  };

  const handleExportConfig = () => {
    try {
      const exportData = {
        supported_tags: editingTags,
        supported_languages: editingLanguages,
        allow_folders: editingFolders,
        export_date: new Date().toISOString(),
        version: '1.0'
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `config_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success('設定已匯出');
    } catch (error) {
      console.error('Failed to export config:', error);
      toast.error('匯出設定失敗');
    }
  };

  const handleImportConfig = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const importedConfig = JSON.parse(content);

        // 驗證必要的欄位
        if (!importedConfig.supported_tags || !importedConfig.supported_languages || !importedConfig.allow_folders) {
          toast.error('配置檔案格式不正確');
          return;
        }

        // 應用匯入的設定
        setEditingTags(importedConfig.supported_tags);
        setEditingLanguages(importedConfig.supported_languages);
        setEditingFolders(importedConfig.allow_folders);

        toast.success('設定已匯入，請點擊「儲存設定」以套用');
      } catch (error) {
        console.error('Failed to import config:', error);
        toast.error('匯入設定失敗，請確認檔案格式正確');
      }
    };

    reader.readAsText(file);
    // 清空 input，讓同一個檔案可以再次選擇
    event.target.value = '';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <p className="text-gray-600">載入中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col md:flex-row items-start gap-4 mt-4 mb-6 ">
          <h1 className="text-2xl font-bold text-gray-900">系統設定</h1>
          <div className="flex-1 flex gap-2 flex-wrap items-start justify-start md:justify-end">
            <input
              type="file"
              accept=".json"
              onChange={handleImportConfig}
              className="hidden"
              id="import-config"
            />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <SettingsIcon className="w-4 h-4" />
                  配置管理
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleExportConfig}>
                  <Download className="w-4 h-4" />
                  匯出設定
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => document.getElementById('import-config')?.click()}>
                  <Upload className="w-4 h-4" />
                  匯入設定
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <Tabs defaultValue="tags">
          <TabsList className='grid grid-cols-3 mb-4'>
            <TabsTrigger value="tags"><Tag className='size-4 me-2' />支援的標籤</TabsTrigger>
            <TabsTrigger value="languages"><Languages className='size-4 me-2' />支援的語言</TabsTrigger>
            <TabsTrigger value="folders"><FolderInput className='size-4 me-2' />允許的資料夾</TabsTrigger>
          </TabsList>
          <TabsContent value="tags">
            {/* 支援的標籤 */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="flex gap-2 items-center text-xl font-semibold mb-4">
                <Tag className='size-6' />
                支援的標籤
              </h2>
              <div className="space-y-2 mb-4">
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleTagDragEnd}
                >
                  <SortableContext items={tagIds} strategy={verticalListSortingStrategy}>
                    {editingTags.map((tag, index) => (
                      <SortableTagItem
                        key={tagIds[index]}
                        id={tagIds[index]}
                        tag={tag}
                        index={index}
                        onChange={(i, value) => {
                          const newTags = [...editingTags];
                          newTags[i] = value;
                          setEditingTags(newTags);
                        }}
                        onDelete={(i) => {
                          setEditingTags(editingTags.filter((_, idx) => idx !== i));
                        }}
                      />
                    ))}
                  </SortableContext>
                </DndContext>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  placeholder="新增標籤"
                  className="flex-1 px-3 py-2 border rounded"
                />
                <button
                  onClick={() => {
                    if (newTag.trim()) {
                      setEditingTags([...editingTags, newTag.trim()]);
                      setNewTag('');
                    }
                  }}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
                >
                  新增
                </button>
              </div>
            </div>
          </TabsContent>
          <TabsContent value="languages">
            {/* 支援的語言 */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="flex gap-2 items-center text-xl font-semibold mb-4">
                <Languages className='size-6' />
                支援的語言
              </h2>
              <div className="space-y-2 mb-4">
                {Object.entries(editingLanguages).map(([code, name]) => (
                  <div key={code} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={code}
                      disabled
                      className="w-24 px-3 py-2 border rounded bg-gray-100"
                    />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => {
                        setEditingLanguages({
                          ...editingLanguages,
                          [code]: e.target.value
                        });
                      }}
                      className="flex-1 px-3 py-2 border rounded"
                    />
                    <button
                      onClick={() => {
                        const newLangs = { ...editingLanguages };
                        delete newLangs[code];
                        setEditingLanguages(newLangs);
                      }}
                      className="px-3 py-2 text-gray-500 hover:text-red-500 rounded"
                    >
                      <Trash2 className='size-4' />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newLangCode}
                  onChange={(e) => setNewLangCode(e.target.value)}
                  placeholder="語言代碼"
                  className="w-24 px-3 py-2 border rounded"
                />
                <input
                  type="text"
                  value={newLangName}
                  onChange={(e) => setNewLangName(e.target.value)}
                  placeholder="語言名稱"
                  className="flex-1 px-3 py-2 border rounded"
                />
                <button
                  onClick={() => {
                    if (newLangCode.trim() && newLangName.trim()) {
                      setEditingLanguages({
                        ...editingLanguages,
                        [newLangCode.trim()]: newLangName.trim()
                      });
                      setNewLangCode('');
                      setNewLangName('');
                    }
                  }}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
                >
                  新增
                </button>
              </div>
            </div>
          </TabsContent>
          <TabsContent value="folders">
            {/* 允許的資料夾 */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="flex gap-2 items-center text-xl font-semibold mb-4">
                <FolderInput className='size-6' />
                允許的音樂資料夾
              </h2>
              <div className="space-y-2 mb-4">
                {editingFolders.map((folder, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={folder}
                      onChange={(e) => {
                        const newFolders = [...editingFolders];
                        newFolders[index] = e.target.value;
                        setEditingFolders(newFolders);
                      }}
                      className="flex-1 px-3 py-2 border rounded"
                    />
                    <button
                      onClick={() => {
                        setEditingFolders(editingFolders.filter((_, i) => i !== index));
                      }}
                      className="px-3 py-2 text-gray-500 hover:text-red-500 rounded"
                    >
                      <Trash2 className='size-4' />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newFolder}
                  onChange={(e) => setNewFolder(e.target.value)}
                  placeholder="新增資料夾"
                  className="flex-1 px-3 py-2 border rounded"
                />
                <button
                  onClick={() => {
                    if (newFolder.trim()) {
                      setEditingFolders([...editingFolders, newFolder.trim()]);
                      setNewFolder('');
                    }
                  }}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
                >
                  新增
                </button>
              </div>
            </div>
          </TabsContent>
        </Tabs>







        {/* 儲存按鈕 */}
        <div className="flex justify-end gap-4">
          <Button
            variant="outline"
            onClick={() => {
              setEditingTags(config?.supported_tags || []);
              setEditingLanguages(config?.supported_languages || {});
              setEditingFolders(config?.allow_folders || []);
              toast.info('設定已重置');
            }}
            className="flex-1 px-6 py-2"
          >
            重置
          </Button>
          <Button
            variant='success'
            onClick={saveConfig}
            disabled={saving}
            className="flex-2 px-6 py-2"
          >
            {saving ? '儲存中...' : '儲存設定'}
          </Button>
        </div>
      </div>
    </div>
  );
}
