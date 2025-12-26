// API 配置
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

export const api = {
  // 構建完整的 API URL
  url: (endpoint: string) => {
    // 移除開頭的 / 以避免雙斜線
    const path = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
    return `${API_BASE_URL}/${path}`
  },

  // GET 請求
  get: async (endpoint: string, params?: Record<string, string>) => {
    const url = new URL(api.url(endpoint))
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value)
      })
    }
    return fetch(url.toString())
  },

  // POST 請求
  post: async (endpoint: string, data?: unknown) => {
    return fetch(api.url(endpoint), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: data ? JSON.stringify(data) : undefined,
    })
  },

  // PUT 請求
  put: async (endpoint: string, data?: unknown) => {
    return fetch(api.url(endpoint), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: data ? JSON.stringify(data) : undefined,
    })
  },

  // DELETE 請求
  delete: async (endpoint: string) => {
    return fetch(api.url(endpoint), {
      method: 'DELETE',
    })
  },

  // FormData POST 請求
  postFormData: async (endpoint: string, formData: FormData) => {
    return fetch(api.url(endpoint), {
      method: 'POST',
      body: formData,
    })
  },
}
