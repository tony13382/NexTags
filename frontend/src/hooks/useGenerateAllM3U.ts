import { useState } from 'react';
import { api } from '@/lib/api';

interface GenerateAllM3UResult {
  generatingAll: boolean;
  successMessage: string | null;
  error: string | null;
  handleGenerateAllM3U: () => Promise<void>;
  setSuccessMessage: (message: string | null) => void;
  setError: (error: string | null) => void;
}

export function useGenerateAllM3U(): GenerateAllM3UResult {
  const [generatingAll, setGeneratingAll] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 輪詢任務狀態
  const pollTaskStatus = async () => {
    try {
      const statusData = await api.get('playlists/generate-all-m3u/status');

      if (statusData.status === 'running') {
        // 更新進度訊息
        const progressText = statusData.total > 0
          ? `${statusData.message} (${statusData.progress}/${statusData.total})`
          : statusData.message;
        setSuccessMessage(`${progressText}`);

        // 繼續輪詢
        setTimeout(pollTaskStatus, 1000);
      } else if (statusData.status === 'completed') {
        setGeneratingAll(false);

        if (statusData.result) {
          const { success_count, error_count, total_count } = statusData.result;
          let message = `批量生成完成！總共 ${total_count} 個播放清單：成功 ${success_count} 個`;
          if (error_count > 0) {
            message += `，失敗 ${error_count} 個`;
          }

          setSuccessMessage(message);
          setTimeout(() => setSuccessMessage(null), 8000);

          // 如果有錯誤，在控制台記錄詳細信息
          if (statusData.result.errors && statusData.result.errors.length > 0) {
            console.error('批量生成錯誤:', statusData.result.errors);
          }
        }
      } else if (statusData.status === 'error') {
        setGeneratingAll(false);
        setError(statusData.message || '批量生成 M3U 檔案失敗');
      } else if (statusData.status === 'idle') {
        // 如果狀態是 idle，可能是任務已經完成很久了
        setGeneratingAll(false);
      }
    } catch (err) {
      console.error('Error polling task status:', err);
      // 繼續輪詢，即使發生錯誤
      setTimeout(pollTaskStatus, 2000);
    }
  };

  // 批量生成 M3U 檔案
  const handleGenerateAllM3U = async () => {
    try {
      setError(null);
      setSuccessMessage(null);
      setGeneratingAll(true);

      const data = await api.post('playlists/generate-all-m3u');

      if (data.success) {
        // 任務已啟動，開始輪詢狀態
        setSuccessMessage('批量生成任務已啟動...');
        setTimeout(pollTaskStatus, 1000);
      } else {
        setGeneratingAll(false);
        setError(data.message || '啟動批量生成任務失敗');
      }
    } catch (err) {
      setGeneratingAll(false);
      setError('網路錯誤，請稍後再試');
      console.error('Error generating all M3U files:', err);
    }
  };

  return {
    generatingAll,
    successMessage,
    error,
    handleGenerateAllM3U,
    setSuccessMessage,
    setError,
  };
}
