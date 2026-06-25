import type {
  FamilyMember,
  Item,
  ItemCategory,
  InventoryItem,
  Alert,
  ChatRequest,
  ChatResponse,
} from '../types'

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

// Family
export const getFamily = () => request<FamilyMember[]>('/family/')
export const addMember = (data: Partial<FamilyMember>) =>
  request<FamilyMember>('/family/', { method: 'POST', body: JSON.stringify(data) })
export const updateMember = (id: number, data: Partial<FamilyMember>) =>
  request<FamilyMember>(`/family/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteMember = (id: number) =>
  request<{ ok: boolean }>(`/family/${id}`, { method: 'DELETE' })

// Items
export const getItems = () => request<Item[]>('/items/')
export const getCategories = () => request<ItemCategory[]>('/items/categories')
export const addItem = (data: Partial<Item>) =>
  request<Item>('/items/', { method: 'POST', body: JSON.stringify(data) })
export const updateItem = (id: number, data: Partial<Item>) =>
  request<Item>(`/items/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteItem = (id: number) =>
  request<{ ok: boolean }>(`/items/${id}`, { method: 'DELETE' })

// Inventory
export const getInventory = () => request<InventoryItem[]>('/inventory/')

// Alerts
export const getAlerts = (status?: string) =>
  request<Alert[]>(`/alerts/${status ? `?status=${status}` : ''}`)
export const updateAlert = (id: number, data: { status: string }) =>
  request<Alert>(`/alerts/${id}`, { method: 'PUT', body: JSON.stringify(data) })

// Chat
export const sendMessage = (message: string) =>
  request<ChatResponse>('/chat/', { method: 'POST', body: JSON.stringify({ message }) })
