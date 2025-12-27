import axios from 'axios'

// API 配置
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

// 創建 axios 實例
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 回應攔截器：自動處理錯誤
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const api = {
  // 構建完整的 API URL（保留此方法以維持向後相容）
  url: (endpoint: string) => {
    const path = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
    return `${API_BASE_URL}/${path}`
  },

  // GET 請求
  get: async (endpoint: string, params?: Record<string, string>) => {
    console.log("Calling api.get from api.ts for endpoint:", endpoint);
    const response = await axiosInstance.get(endpoint, { params })
    return response.data
  },

  // POST 請求
  post: async (endpoint: string, data?: unknown) => {
    const response = await axiosInstance.post(endpoint, data)
    return response.data
  },

  // PUT 請求
  put: async (endpoint: string, data?: unknown) => {
    const response = await axiosInstance.put(endpoint, data)
    return response.data
  },

  // DELETE 請求
  delete: async (endpoint: string) => {
    const response = await axiosInstance.delete(endpoint)
    return response.data
  },

  // FormData POST 請求
  postFormData: async (endpoint: string, formData: FormData) => {
    const response = await axiosInstance.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}
