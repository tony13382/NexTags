'use client'

import React, { useEffect, useState } from 'react'

interface TaskInfo {
  task_id: string
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  data: any
  result: any
  error: string | null
  progress: number
}

interface TaskStatusDialogProps {
  taskId: string | null
  isOpen: boolean
  onClose: () => void
  onComplete?: (result: any) => void
}

export default function TaskStatusDialog({ 
  taskId, 
  isOpen, 
  onClose, 
  onComplete 
}: TaskStatusDialogProps) {
  const [task, setTask] = useState<TaskInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchTaskStatus = async () => {
    if (!taskId) return

    try {
      setLoading(true)
      const response = await fetch(`/api/tasks/${taskId}`)
      const data = await response.json()

      if (data.success) {
        setTask(data.task)
        setError(null)

        // 如果任務完成，調用完成回調
        if (data.task.status === 'completed' && onComplete) {
          onComplete(data.task.result)
        }
      } else {
        setError(data.message || '獲取任務狀態失敗')
      }
    } catch (err) {
      setError('網路錯誤，請稍後再試')
      console.error('Error fetching task status:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isOpen || !taskId) {
      setTask(null)
      setError(null)
      return
    }

    // 立即獲取一次狀態
    fetchTaskStatus()

    // 如果任務還在進行中，定期輪詢狀態
    const pollInterval = setInterval(() => {
      if (task?.status === 'pending' || task?.status === 'running') {
        fetchTaskStatus()
      } else {
        clearInterval(pollInterval)
      }
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [isOpen, taskId, task?.status])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'text-yellow-600'
      case 'running': return 'text-blue-600'
      case 'completed': return 'text-green-600'
      case 'failed': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending': return '等待中'
      case 'running': return '執行中'
      case 'completed': return '已完成'
      case 'failed': return '失敗'
      default: return '未知'
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">任務狀態</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <span className="sr-only">關閉</span>
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {loading && !task && (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-600">載入中...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {task && (
            <div className="space-y-4">
              {/* 任務基本信息 */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">狀態</span>
                  <span className={`text-sm font-medium ${getStatusColor(task.status)}`}>
                    {getStatusText(task.status)}
                  </span>
                </div>

                {/* 進度條 */}
                {task.status === 'running' && (
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-gray-600 mb-1">
                      <span>進度</span>
                      <span>{task.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${task.progress}%` }}
                      ></div>
                    </div>
                  </div>
                )}
              </div>

              {/* 任務詳情 */}
              <div className="text-sm text-gray-600">
                <p><strong>任務類型:</strong> {task.task_type}</p>
                <p><strong>任務 ID:</strong> {task.task_id}</p>
                <p><strong>創建時間:</strong> {new Date(task.created_at).toLocaleString('zh-TW')}</p>
                
                {task.data?.playlist_name && (
                  <p><strong>播放清單:</strong> {task.data.playlist_name}</p>
                )}
              </div>

              {/* 結果或錯誤信息 */}
              {task.status === 'completed' && task.result && (
                <div className="bg-green-50 border border-green-200 rounded-md p-4">
                  <p className="text-sm text-green-800 font-medium">✅ {task.result.message}</p>
                  {task.result.songs_added && (
                    <p className="text-sm text-green-700 mt-1">
                      成功同步 {task.result.songs_added} 首歌曲
                    </p>
                  )}
                </div>
              )}

              {task.status === 'failed' && task.error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <p className="text-sm text-red-800 font-medium">❌ 任務失敗</p>
                  <p className="text-sm text-red-700 mt-1">{task.error}</p>
                </div>
              )}

              {/* 關閉按鈕 */}
              <div className="flex justify-end pt-4">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  {task.status === 'running' ? '後台執行' : '關閉'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}