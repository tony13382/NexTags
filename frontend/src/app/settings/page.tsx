'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Config {
  supported_tags: string[];
  supported_languages: { [key: string]: string };
  allow_folders: string[];
}

export default function SettingsPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 編輯狀態
  const [editingTags, setEditingTags] = useState<string[]>([]);
  const [editingLanguages, setEditingLanguages] = useState<{ [key: string]: string }>({});
  const [editingFolders, setEditingFolders] = useState<string[]>([]);

  // 新增項目的輸入框
  const [newTag, setNewTag] = useState('');
  const [newLangCode, setNewLangCode] = useState('');
  const [newLangName, setNewLangName] = useState('');
  const [newFolder, setNewFolder] = useState('');

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/config');
      const result = await response.json();
      if (result.success) {
        setConfig(result.data);
        setEditingTags(result.data.supported_tags);
        setEditingLanguages(result.data.supported_languages);
        setEditingFolders(result.data.allow_folders);
      }
    } catch (error) {
      console.error('Failed to fetch config:', error);
      setMessage({ type: 'error', text: '載入設定失敗' });
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    setMessage(null);

    try {
      // 更新 supported_tags
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config_key: 'supported_tags',
          config_value: editingTags,
          description: '支援的標籤列表'
        })
      });

      // 更新 supported_languages
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config_key: 'supported_languages',
          config_value: editingLanguages,
          description: '支援的語言代碼對應'
        })
      });

      // 更新 allow_folders
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config_key: 'allow_folders',
          config_value: editingFolders,
          description: '允許的音樂資料夾'
        })
      });

      setMessage({ type: 'success', text: '設定已儲存' });
      await fetchConfig();
    } catch (error) {
      console.error('Failed to save config:', error);
      setMessage({ type: 'error', text: '儲存設定失敗' });
    } finally {
      setSaving(false);
    }
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
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">系統設定</h1>
          <Link
            href="/"
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            返回首頁
          </Link>
        </div>

        {message && (
          <div
            className={`mb-4 p-4 rounded ${
              message.type === 'success'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* 支援的標籤 */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">支援的標籤</h2>
          <div className="space-y-2 mb-4">
            {editingTags.map((tag, index) => (
              <div key={index} className="flex items-center gap-2">
                <input
                  type="text"
                  value={tag}
                  onChange={(e) => {
                    const newTags = [...editingTags];
                    newTags[index] = e.target.value;
                    setEditingTags(newTags);
                  }}
                  className="flex-1 px-3 py-2 border rounded"
                />
                <button
                  onClick={() => {
                    setEditingTags(editingTags.filter((_, i) => i !== index));
                  }}
                  className="px-3 py-2 text-gray-500 hover:text-red-500 rounded"
                >
                  ✕
                </button>
              </div>
            ))}
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

        {/* 支援的語言 */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">支援的語言</h2>
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
                  ✕
                </button>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newLangCode}
              onChange={(e) => setNewLangCode(e.target.value)}
              placeholder="語言代碼 (如: eng)"
              className="w-40 px-3 py-2 border rounded"
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

        {/* 允許的資料夾 */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">允許的音樂資料夾</h2>
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
                  ✕
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

        {/* 儲存按鈕 */}
        <div className="flex justify-end gap-4">
          <button
            onClick={() => {
              setEditingTags(config?.supported_tags || []);
              setEditingLanguages(config?.supported_languages || {});
              setEditingFolders(config?.allow_folders || []);
              setMessage(null);
            }}
            className="px-6 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            重置
          </button>
          <button
            onClick={saveConfig}
            disabled={saving}
            className="px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-400"
          >
            {saving ? '儲存中...' : '儲存設定'}
          </button>
        </div>
      </div>
    </div>
  );
}
